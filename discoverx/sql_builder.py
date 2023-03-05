"""
This module contains classes and functions which automatically build
SQL expressions for specified tables and rules
"""
from discoverx.config import TableInfo
from discoverx.common.helper import strip_margin
from discoverx.rules import Rule, RuleTypes
import re
import itertools


class SqlBuilder:
    """
    The SqlBuilder class automatically creates a SQL expression for
    scanning tables and determining the likelihood of its columns to
    match specified rules
    """

    columns_table_name = "system.information_schema.columns"

    def format_regex(self, expression):
        return expression.replace("\\", r"\\")
      
    # pylint: disable=too-few-public-methods
    def rule_matching_sql(self, table_info: TableInfo, rules: list[Rule], sample_size: int = 1000):
        """
        Given a table and a set of rules this method will return a
        SQL expression which matches the table's columns against rules.
        If executed on the table using SQL the output will contain a
        matching frequency (probability) for each column and rule.
        Args:
            table_info (TableInfo): Specifies the table to be scanned
            rules (list[Rule]): A list of Rules based on regular
                expressions
            sample_size (int): The number of records sampled/scanned
                for each table

        Returns:
            string: The SQL expression

        """

        expressions = [r for r in rules if r.type == RuleTypes.REGEX]
        cols = [c for c in table_info.columns if c.data_type.lower() == "string"]
        
        if (not cols):
            raise Exception(f"There are no columns of type string to be scanned in {table_info.table}")
            
        if (not expressions):
            raise Exception(f"There are no rules to scan for.")

        catalog_str = f"{table_info.catalog}." if table_info.catalog else ""
        matching_columns = [f"INT(regexp_like(value, '{self.format_regex(r.definition)}')) AS {r.name}" for r in expressions]
        matching_string = ",\n                    ".join(matching_columns)

        unpivot_expressions = ", ".join([f"'{r.name}', `{r.name}`" for r in expressions])
        unpivot_columns = ", ".join([f"'{c.name}', `{c.name}`" for c in cols])

        sql = f"""
            SELECT 
                '{table_info.catalog}' as catalog,
                '{table_info.database}' as database,
                '{table_info.table}' as table, 
                column,
                rule_name,
                (sum(value) / count(value)) as frequency
            FROM
            (
                SELECT column, stack({len(expressions)}, {unpivot_expressions}) as (rule_name, value)
                FROM 
                (
                    SELECT
                    column,
                    {matching_string}
                    FROM (
                        SELECT
                            stack({len(cols)}, {unpivot_columns}) AS (column, value)
                        FROM {catalog_str}{table_info.database}.{table_info.table}
                        TABLESAMPLE ({sample_size} ROWS)
                    )
                )
            )
            GROUP BY catalog, database, table, column, rule_name
        """

        return strip_margin(sql)

    def get_table_list_sql(self, catalog_filter: str, database_filter: str, table_filter: str):
        """
        Returns a SQL expression which returns a list of columns matching
        the specified filters
        Args:
            catalog_filter (str): A filter expression for catalogs
            database_filter (str): A filter expression for databases
            table_filter (str): A filter expression for tables

        Returns:
            string: The SQL expression
        """

        catalog_sql = f"""AND regexp_like(table_catalog, "^{catalog_filter.replace("*", ".*")}$")"""
        database_sql = f"""AND regexp_like(table_schema, "^{database_filter.replace("*", ".*")}$")"""
        table_sql = f"""AND regexp_like(table_name, "^{table_filter.replace("*", ".*")}$")"""

        sql = f"""
        SELECT 
            table_catalog, 
            table_schema, 
            table_name, 
            collect_list(struct(column_name, data_type, partition_index)) as table_columns
        FROM {self.columns_table_name}
        WHERE 
            table_schema != "information_schema" 
            {catalog_sql if catalog_filter != "*" else ""}
            {database_sql if database_filter != "*" else ""}
            {table_sql if table_filter != "*" else ""}
        GROUP BY table_catalog, table_schema, table_name
        """

        return strip_margin(sql)

    def compile_msql(self, msql, table_info: TableInfo):
        """
        Compiles the specified M-SQL (Multiplex-SQL) expression into regular SQL
        Args:
            msql (str): The M-SQL expression

        Returns:
            string: A SQL expression which multiplexes the MSQL expression
        """
        tag_regex = r"\[([\w_-]+)\]"
        tags = list(set(re.findall(tag_regex, msql)))

        x = []
        for tag in tags:
            tagged_cols = table_info.get_columns_by_tag(tag)
            x.append(tagged_cols)

        combinations = list(itertools.product(*x))
        sql_statements = []

        for c in combinations:
            temp_sql = msql
            for tagged_col in c:
                temp_sql = self._replace_tag(temp_sql, tagged_col.tag, tagged_col.name)
            sql_statements.append(temp_sql)

        final_sql = "\nUNION ALL\n".join(sql_statements)
        return strip_margin(final_sql)
    
    def _replace_tag(self, msql, tag, col_name):
        """
        Replaces a tag in an M-SQL expression with a column name
        Args:
            msql (str): The M-SQL expression
            tag (str): The tag to be replaced
            col_name (str): The column name to be used for replacement

        Returns:
            string: The M-SQL expression with the tag replaced
        """
        # TODO: Assert alias in SELECT statement
        # non_aliased_tags = re.findall(r"SELECT +\[([\w_-]+)\] +", msql)
        # if non_aliased_tags:
        #     raise ValueError(f"""Tags {non_aliased_tags} are not aliased in M-SQL expression.
        #     Please specify an alias for each tag. Eg. [tag] AS 'my_alias'.""")
        return msql.replace(f"[{tag}]", col_name)