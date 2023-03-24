# Databricks notebook source
# MAGIC %md
# MAGIC # DiscoverX interaction

# COMMAND ----------

# MAGIC %pip install pydantic

# COMMAND ----------

# MAGIC %load_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate sample data

# COMMAND ----------

dbutils.notebook.run("./sample_data", timeout_seconds=0, arguments={"discoverx_sample_catalog": "discoverx_sample"} )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Plain functions flow
# MAGIC 
# MAGIC This is a demo interaction with pure functions

# COMMAND ----------

from discoverx import DX
dx = DX()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Scan

# COMMAND ----------

dx.scan(catalogs="discoverx*")

# COMMAND ----------

dx.scanner.scan_result.df[0:10]

# COMMAND ----------

# MAGIC %md
# MAGIC ## M-SQL (Multiplex SQL)
# MAGIC M-SQL lets you run SQL statements across a wide number of table by leveraging the tags

# COMMAND ----------

# MAGIC %md
# MAGIC ### Search for a specific IP across all tables

# COMMAND ----------

dx.msql_experimental("""
SELECT 
  '[ip_v4]' AS ip_v4_column,
  [ip_v4] AS ip_v4, 
  to_json(struct(*)) AS row_content
FROM discoverx*.*.*
WHERE [ip_v4] = '1.2.3.4'
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Distinct IP per table

# COMMAND ----------

dx.msql_experimental("""
SELECT 
  '[ip_v4]' AS ip_v4_column, 
  [ip_v4] AS ip_v4, 
  count([ip_v4]) AS count 
FROM discoverx*.*.*
GROUP BY [ip_v4]
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Delete from all tables - WHAT_IF

# COMMAND ----------

dx.msql_experimental("DELETE FROM discoverx*.*.* WHERE [ip_v4] = '0.0.0.0'", what_if=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Delete from all tables

# COMMAND ----------

dx.msql_experimental("DELETE FROM discoverx*.*.* WHERE [ip_v4] = '0.0.0.0'").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC 
# MAGIC This section is optional, and can be used to customize the behaviour of DiscoverX

# COMMAND ----------

conf = {
  'column_type_classification_threshold': 0.95,
}
dx = DX(**conf)

dx = DX(column_type_classification_threshold=0.95)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Custom rules

# COMMAND ----------

dx.display_rules()

# COMMAND ----------

from discoverx.rules import Rule


resource_request_id_rule = {
  'name': 'resource_request_id',
  'type': 'regex',
  'description': 'Resource request ID',
  'definition': r'^AR-\d{9}$',
  'match_example': ['AR-123456789']
}

resource_request_id_rule = Rule(**resource_request_id_rule)

dx_custm_rules = DX(custom_rules=[resource_request_id_rule])
dx_custm_rules.display_rules()
# # dx.register_rules(custom_rules)

# COMMAND ----------

dx_custm_rules.scan(catalogs="discoverx*", sample_size=1000)

# COMMAND ----------

#  IDEA:
# pipeline = [
#   { 'task_type': 'scan',
#     'task_id': 'pii_dev',
#     'configuration': {
#       'catalogs': '*',
#       'databases': 'dev_*',
#       'tables': '*',
#       'sample_size': 10000,
#       'rules': ['custom_device_id', 'dx_ip_address']
#     }
#   }
# ]

# dx.run(pipeline)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Help

# COMMAND ----------

help(DX)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Search
# MAGIC 
# MAGIC This command can be used to search inside the content of tables.
# MAGIC 
# MAGIC If the tables have ben scanned before, the search will restrict the scope to only the columns that could contain the search term based on the avaialble rules.

# COMMAND ----------

# dx.search("erni@databricks.com", databases="prod_*") # This will only search inside columns tagged with dx_email.
# dx.search("127.0.0.1", databases="prod_*") # This will only search inside columns tagged as dx_ip_address.
# dx.search("127.0.0.1", restrict_to_matched_rules=False) # This not use tags to restrict the columns to search 


# COMMAND ----------

# MAGIC %md
# MAGIC ## Tagging

# COMMAND ----------

# dx.tag_columns(rule_match_frequency_table=None, column_type_classification_threshold=0.95) # This will show the SQL commands to apply tags from the temp view discoverx_temp_rule_match_frequency_table

# dx.tag_columns(rule_match_frequency_table="", yes_i_am_sure=True) # This will apply the tags 

# COMMAND ----------

