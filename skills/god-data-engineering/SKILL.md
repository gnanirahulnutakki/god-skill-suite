---
name: god-data-engineering
description: "God-level data engineering skill covering the modern data stack, batch and streaming pipeline design, Apache Spark (architecture, transformations, optimization), Apache Flink (stateful stream processing, exactly-once), Apache Airflow (DAG design, operators, sensors, XCom, task dependencies), dbt (data modeling, tests, documentation, incremental models), Kafka as a data backbone, data quality frameworks (Great Expectations, dbt tests, Soda), data lake architectures (Delta Lake, Apache Iceberg, Apache Hudi), data warehousing (Snowflake, BigQuery, Redshift), ELT vs ETL, and DataOps. A backend engineer who understands data pipelines builds better APIs. A DevOps engineer who understands data pipelines builds better infrastructure for them."
metadata:
  domain: "\"data-engineering\""
  sources: " - \"Fundamentals of Data Engineering — Reis & Housley (O'Reilly, 2022)\" - \"Apache Kafka Documentation — kafka.apache.org/documentation\" - \"Apache Airflow Documentation — airflow.apache.org/docs\" - \"Apache Spark Documentation — spark.apache.org/docs\" - \"Apache Flink Documentation — flink.apache.org/docs\" - \"dbt Documentation — docs.getdbt.com\" - \"Delta Lake Documentation — docs.delta.io\" - \"Apache Iceberg Documentation — iceberg.apache.org/docs\""
  version: "\"1.0\""
  cross_domain: "''"
---

# God-Level Data Engineering

## Researcher-Warrior Mindset

You do not trust the pipeline because it ran last night. You prove it ran correctly by checking row counts, null rates, referential integrity, and value distributions. You do not assume the schema is stable because it was stable last month. You instrument your pipeline for observability the same way a backend engineer instruments an API. You treat data quality failures as production incidents, because for business decisions, a silent data error is worse than a loud pipeline crash.

---

## Anti-Hallucination Rules

**NEVER fabricate:**
- Spark configuration parameter names — verify in `spark.apache.org/docs/latest/configuration.html` (e.g., `spark.sql.shuffle.partitions` not `spark.shuffle.partitions`)
- Flink operator class names — verify in Flink API docs (e.g., `TumblingEventTimeWindows` vs `TumblingProcessingTimeWindows`)
- Airflow operator names and import paths — these change across versions (e.g., `PythonOperator` moved from `airflow.operators.python_operator` to `airflow.operators.python` in Airflow 2.x)
- dbt model materialization names — `table`, `view`, `incremental`, `ephemeral` are real; `materialized_view` was added later (verify version)
- Great Expectations suite method names — API changed significantly between v2 and v3; verify version
- Delta Lake / Iceberg API methods — `DeltaTable.forPath()` is Java/Scala; Python uses `DeltaTable.forPath(spark, path)`
- Kafka Streams vs Flink API confusion — they are entirely different APIs

**ALWAYS verify:**
- Airflow TaskFlow API availability (Airflow 2.0+, not 1.x)
- dbt adapter support — not all materializations are supported on all data warehouses
- Spark version for features (e.g., Adaptive Query Execution requires Spark 3.0+)
- Flink exactly-once requires checkpoint backend (RocksDB or FsStateBackend) — verify config key names

---

## 1. ELT vs ETL

**ETL (Extract, Transform, Load) — traditional:**
```
Source DB → Extract → Transform (external tool) → Load → Data Warehouse
Transforms happen BEFORE data enters the warehouse.
The transformation compute lives outside the warehouse.
```

**ELT (Extract, Load, Transform) — modern cloud era:**
```
Source DB → Extract → Load (raw) → Transform (inside the warehouse) → Marts
Transforms happen AFTER data lands in the warehouse.
The warehouse compute (Snowflake, BigQuery, Redshift) is the transform engine.
```

**Why ELT won in the cloud data warehouse era:**
1. Cloud DWs have virtually unlimited compute-on-demand — transforming inside them is cheap
2. Raw data is preserved — you can re-transform when requirements change without re-extracting
3. dbt enables SQL-defined transforms with version control, testing, and documentation
4. Separation of concerns: data movement (Fivetran, Airbyte, Stitch) vs transformation (dbt)

**When ETL still applies:**
- PII/sensitive data that must be masked/tokenized BEFORE reaching the warehouse (compliance)
- Very large data requiring pre-aggregation to reduce egress costs
- Real-time streaming where data must be enriched before ingestion (Flink, Kafka Streams)
- Legacy on-premise systems where warehouse compute cannot reach source data

---

## 2. Batch vs Streaming

```
Batch Processing:
  - Process accumulated data on a schedule (hourly, daily)
  - High throughput, high latency (results available after batch completes)
  - Simpler fault tolerance (reprocess the batch)
  - Tools: Spark, dbt, BigQuery scheduled queries, Airflow-orchestrated SQL

Streaming Processing:
  - Process data record-by-record or in micro-batches as it arrives
  - Low latency (results available within seconds/minutes)
  - Complex fault tolerance (state management, exactly-once)
  - Tools: Apache Flink, Kafka Streams, Spark Structured Streaming

Micro-batch (Spark Structured Streaming):
  - Treats stream as rapid sequence of small batches
  - Trigger intervals: every 100ms to minutes
  - Latency: typically seconds, not sub-second
  - Simpler to reason about than true streaming (still uses Spark batch engine underneath)

True Streaming (Flink):
  - Processes each record as it arrives
  - Sub-second latency achievable
  - Event time semantics, watermarks, complex stateful operators
  - Use when: fraud detection, real-time recommendations, alerting
```

**Latency vs Throughput tradeoff:**
```
Batch (daily): 24h latency, maximum throughput (full optimization over full dataset)
Batch (hourly): 1h latency, high throughput
Micro-batch (1 min): 60s latency, moderate throughput (framework overhead)
True streaming: <1s latency, lower throughput per record (stateful overhead)

Choose based on business SLA for data freshness, not engineering preference.
```

---

## 3. Apache Spark

### Architecture
```
Driver Program (SparkContext/SparkSession)
  └── Cluster Manager (YARN, Kubernetes, Mesos, Standalone)
       └── Executor 1 (JVM process on worker node)
            ├── Task 1 (thread)
            ├── Task 2 (thread)
            └── ...
       └── Executor 2
            └── ...

DAG Scheduler: breaks transformations into stages (separated by shuffles)
Task Scheduler: assigns tasks within a stage to executors
```

### RDD vs DataFrame vs Dataset API
```
RDD (Resilient Distributed Dataset):
  - Lowest-level API, full control
  - No schema, no optimizer, Scala/Python/Java objects
  - Use when: fine-grained control, unstructured data
  - Avoid: in new code — no catalyst optimization

DataFrame:
  - Distributed table with named columns and schema
  - Catalyst optimizer applies (predicate pushdown, join reordering)
  - Python/Scala/R/SQL — same execution plan underneath
  - Use: for most ETL/ELT/analytics workloads

Dataset (Scala/Java only):
  - Type-safe DataFrame, compile-time checks
  - Same Catalyst optimization as DataFrame
  - Not available in Python (Python is dynamic — PySparkDataFrame is always DataFrame)
```

### Shuffle: The Most Expensive Spark Operation
```python
# Operations that cause shuffle (data redistributed across executors):
#   groupBy, join (except broadcast join), distinct, repartition, 
#   orderBy, aggregations across partitions

# Tune shuffle partitions:
# Default: spark.sql.shuffle.partitions = 200 (often too many for small data, too few for large)
spark.conf.set("spark.sql.shuffle.partitions", "400")  # tune per job

# Adaptive Query Execution (Spark 3.0+) — automatically tunes at runtime
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

### Broadcast Join
```python
from pyspark.sql.functions import broadcast

# Broadcast small table to all executors — eliminates shuffle for the join
# Rule of thumb: broadcast tables < 100MB (configurable via spark.sql.autoBroadcastJoinThreshold)
result = large_df.join(broadcast(small_lookup_df), "key_column")

# Force disable auto-broadcast for debugging:
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")
```

### Avoiding Data Skew
```python
# Problem: one partition key has 90% of data → one task takes 90% of job time

# Solution 1: Salting — add random prefix to skewed keys
from pyspark.sql.functions import col, concat, lit, rand, floor

num_salt_buckets = 10
skewed_df = skewed_df.withColumn(
    "salted_key", 
    concat(col("key"), lit("_"), (floor(rand() * num_salt_buckets)).cast("string"))
)
# Then join with exploded version of lookup table

# Solution 2: AQE Skew Join Optimization (Spark 3.0+)
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes", "256MB")
```

### Spark UI Interpretation
```
Jobs tab: overall job progress, stages per job
Stages tab: tasks per stage, task duration histogram
  → If some tasks take 10x longer than median: DATA SKEW
  → If many tasks take same short time but there are 2000 of them: TOO MANY SMALL PARTITIONS
Storage tab: cached RDDs/DataFrames — check memory fraction
Environment tab: all Spark config values (debug misconfiguration)
SQL tab: physical plan, Catalyst optimizer decisions, stage boundaries
```

---

## 4. Apache Flink

### Time Semantics
```
Event Time: time embedded in the event itself (when it actually happened)
  → Correct: handles late data, out-of-order events
  → Required for: business reporting, fraud detection
  → Cost: must define watermarks, handle late events

Processing Time: time when the event is processed by Flink
  → Simple, no watermarks needed
  → Wrong for: any use case where event order or timing matters

Ingestion Time: time when event entered Flink (deprecated concept, use event time)
```

### Watermarks
```java
// Watermark: tells Flink "events with timestamp < T-maxLateness will not arrive"
// Allows triggering windows without waiting forever for late data

// Bounded out-of-orderness watermark (verified Flink 1.14+ API)
WatermarkStrategy.<MyEvent>forBoundedOutOfOrderness(Duration.ofSeconds(10))
    .withTimestampAssigner((event, timestamp) -> event.getEventTime())
    .withIdleness(Duration.ofMinutes(1));  // handle idle partitions
```

### Windowing
```java
// Tumbling windows: fixed-size, non-overlapping
// Window [00:00, 01:00), [01:00, 02:00), ...
stream.window(TumblingEventTimeWindows.of(Time.hours(1)))

// Sliding windows: fixed-size, overlapping by slide interval
// A 1-hour window every 15 minutes
stream.window(SlidingEventTimeWindows.of(Time.hours(1), Time.minutes(15)))

// Session windows: gap-based (closes after inactivity gap)
// Useful for user session analysis
stream.window(EventTimeSessionWindows.withGap(Time.minutes(30)))
```

### Checkpointing for Exactly-Once
```yaml
# flink-conf.yaml — verified Flink configuration keys
execution.checkpointing.interval: 60000      # checkpoint every 60 seconds
execution.checkpointing.mode: EXACTLY_ONCE   # or AT_LEAST_ONCE
execution.checkpointing.timeout: 120000      # fail checkpoint if takes > 2 min
execution.checkpointing.min-pause: 30000     # min time between checkpoint starts

state.backend: rocksdb                       # for large state (spills to disk)
# or: hashmap  (in-memory, fast, limited by JVM heap)

state.checkpoints.dir: hdfs://namenode:9000/flink/checkpoints
state.savepoints.dir: hdfs://namenode:9000/flink/savepoints
```

**Savepoints vs Checkpoints:**
- **Checkpoints:** Automatic, for fault recovery — Flink manages lifecycle
- **Savepoints:** Manual, for planned upgrades, scaling, job migration — you trigger them
- `flink savepoint <job-id> [savepoint-dir]`
- Restart from savepoint: `flink run -s <savepoint-path> my-job.jar`

---

## 5. Apache Airflow

### DAG Design Principles

**Idempotency:** Running the same DAG run multiple times produces the same result. Achieved by: using `execution_date` as a partition key, using UPSERT not INSERT, clearing destination before writing.

**Atomicity:** Each task either fully succeeds or fully fails. Partial writes should be rolled back. Write to staging location first, then swap/rename atomically.

```python
# Airflow 2.x DAG — verified syntax with TaskFlow API
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    'owner': 'data-engineering',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'email_on_failure': True,
    'email': ['de-alerts@company.com'],
}

@dag(
    dag_id='daily_revenue_pipeline',
    default_args=default_args,
    schedule_interval='0 6 * * *',     # 6am UTC daily
    start_date=days_ago(1),
    catchup=False,                     # IMPORTANT: don't backfill on first run
    max_active_runs=1,                 # prevent concurrent runs
    tags=['revenue', 'daily'],
)
def revenue_pipeline():

    @task()
    def extract_orders(**context) -> dict:
        execution_date = context['ds']  # YYYY-MM-DD string
        # Extract orders for this specific date (idempotent)
        row_count = run_extraction(execution_date)
        return {'row_count': row_count, 'date': execution_date}

    @task()
    def transform_orders(extract_result: dict) -> dict:
        # XCom: small data only — execution metadata, not the actual records
        # Never pass DataFrames via XCom — use S3/GCS paths instead
        date = extract_result['date']
        output_path = f's3://data-lake/processed/orders/date={date}/'
        run_transform(date, output_path)
        return {'output_path': output_path, 'row_count': extract_result['row_count']}

    @task()
    def load_to_warehouse(transform_result: dict):
        # Load idempotently: DELETE WHERE date=X, then INSERT
        load_partitioned(transform_result['output_path'])

    # Define dependencies via function calls
    extract_result = extract_orders()
    transform_result = transform_orders(extract_result)
    load_to_warehouse(transform_result)

dag = revenue_pipeline()
```

### Operator Types
```python
# PythonOperator — run Python callable
from airflow.operators.python import PythonOperator

# BashOperator — run shell commands
from airflow.operators.bash import BashOperator

# SQLExecuteQueryOperator (Airflow 2.4+) — run SQL
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

# S3ToRedshiftOperator — copy data from S3 to Redshift
from airflow.providers.amazon.aws.transfers.s3_to_redshift import S3ToRedshiftOperator

# BigQueryInsertJobOperator — run BigQuery SQL
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

# SparkSubmitOperator — submit Spark job
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
```

### Sensors
```python
# Sensors block until a condition is met (with poke_interval polling)
from airflow.sensors.s3_key_sensor import S3KeySensor
from airflow.sensors.external_task import ExternalTaskSensor

# Wait for upstream file to appear
wait_for_file = S3KeySensor(
    task_id='wait_for_source_file',
    bucket_name='data-lake',
    bucket_key='incoming/orders/date={{ ds }}/data.parquet',
    poke_interval=300,          # check every 5 minutes
    timeout=3600,               # fail after 1 hour
    mode='reschedule',          # release worker slot while waiting (not 'poke' which holds it)
)

# Wait for another DAG to complete
wait_for_upstream = ExternalTaskSensor(
    task_id='wait_for_orders_dag',
    external_dag_id='orders_pipeline',
    external_task_id='load_to_warehouse',
    execution_delta=timedelta(hours=0),
    mode='reschedule',
    timeout=7200,
)
```

### Common Airflow Pitfalls
```
1. Giant XCom payloads: XCom stores in the Airflow metadata DB (PostgreSQL/MySQL).
   Large DataFrames kill the DB. Rule: XCom only for paths, counts, status strings.

2. Top-level imports in DAG files: Airflow scans all DAG files continuously.
   Heavy imports at the top level slow the scheduler. Move imports inside operators/tasks.

3. Too many tasks in one DAG: scheduling overhead scales with task count.
   Split large DAGs into smaller DAGs with ExternalTaskSensor dependencies.

4. Not setting catchup=False: Airflow will try to backfill every missed interval.
   On first deploy of a DAG with start_date=1 year ago, this creates 365 runs.

5. Using execution_date instead of data_interval_start:
   In Airflow 2.2+, use {{ data_interval_start }} and {{ data_interval_end }} 
   for the actual interval being processed.
```

---

## 6. dbt (data build tool)

### Model Types
```
Staging models (stg_*):
  - One-to-one with source tables
  - Rename columns to consistent naming convention
  - Basic type casting, deduplication
  - Materialized as: view (cheap, always fresh)

Intermediate models (int_*):
  - Business logic, joins across staging models
  - Not exposed to end users
  - Materialized as: view or ephemeral (depends on complexity)

Mart models (fct_*, dim_*):
  - Fact tables: granular events/transactions
  - Dimension tables: entities (customers, products, etc.)
  - Exposed to BI tools and analysts
  - Materialized as: table (for query performance)
```

### Materializations
```yaml
# dbt_project.yml
models:
  my_project:
    staging:
      +materialized: view
    intermediate:
      +materialized: view
    marts:
      +materialized: table
      
# Model-level override in SQL file header:
# {{ config(materialized='incremental', unique_key='order_id') }}
```

**Incremental models:**
```sql
-- Verified dbt incremental model syntax
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge'    -- merge, append, insert_overwrite (varies by adapter)
) }}

SELECT
    order_id,
    user_id,
    total,
    created_at,
    updated_at
FROM {{ source('raw', 'orders') }}

{% if is_incremental() %}
    -- Only process rows updated since last run
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

### dbt Tests
```yaml
# schema.yml — verified dbt test syntax
version: 2

models:
  - name: fct_orders
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: user_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_users')
              field: user_id
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'completed', 'cancelled', 'refunded']
      - name: total
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"  # requires dbt-utils package
```

### dbt Macros
```sql
-- macros/cents_to_dollars.sql
{% macro cents_to_dollars(column_name) %}
    ({{ column_name }} / 100.0)::numeric(10, 2)
{% endmacro %}

-- Usage in model:
SELECT
    order_id,
    {{ cents_to_dollars('amount_cents') }} as amount_dollars
FROM {{ source('raw', 'orders') }}
```

---

## 7. Data Quality

### Great Expectations (v3 API — verified)
```python
import great_expectations as gx

context = gx.get_context()

# Add data source
datasource = context.sources.add_pandas_filesystem(
    name="my_datasource",
    base_directory="./data"
)

# Create expectation suite
suite = context.add_expectation_suite("orders_suite")

# Define expectations
validator = context.get_validator(
    batch_request=...,
    expectation_suite_name="orders_suite"
)
validator.expect_column_to_exist("order_id")
validator.expect_column_values_to_not_be_null("order_id")
validator.expect_column_values_to_be_unique("order_id")
validator.expect_column_values_to_be_between(
    "total", min_value=0, max_value=1_000_000
)
validator.expect_column_values_to_be_in_set(
    "status", ["pending", "completed", "cancelled"]
)

# Run validation checkpoint
checkpoint = context.add_or_update_checkpoint(
    name="orders_checkpoint",
    validations=[{"batch_request": ..., "expectation_suite_name": "orders_suite"}]
)
result = checkpoint.run()
```

### Schema Evolution Handling
```
Strategy 1: Schema-on-read (data lake) — infer schema at query time
  Risk: Type inference errors, downstream breaks when new columns added

Strategy 2: Schema registry (Kafka + Confluent Schema Registry)
  Compatibility modes: BACKWARD (new schema reads old data), FORWARD (old schema reads new data), FULL
  Enforce at produce time — rejects non-compatible schemas

Strategy 3: Versioned schema in Iceberg/Delta Lake
  Schema evolution without rewriting data: ADD COLUMN, RENAME COLUMN
  Schema history tracked in table metadata
```

---

## 8. Delta Lake and Apache Iceberg

### Delta Lake
```python
# PySpark + Delta Lake — verified API
from delta.tables import DeltaTable
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Write (creates Delta table with transaction log)
df.write.format("delta").mode("overwrite").save("/data/orders")

# ACID merge (upsert)
delta_table = DeltaTable.forPath(spark, "/data/orders")
delta_table.alias("target").merge(
    updates_df.alias("source"),
    "target.order_id = source.order_id"
).whenMatchedUpdateAll() \
 .whenNotMatchedInsertAll() \
 .execute()

# Time travel — query as of a previous version
df_v5 = spark.read.format("delta").option("versionAsOf", 5).load("/data/orders")
df_yesterday = spark.read.format("delta").option("timestampAsOf", "2024-01-14").load("/data/orders")

# Z-ordering for query optimization (co-locate related data in same files)
# Improves query performance for filters on z-ordered columns
delta_table.optimize().executeZOrderBy("user_id", "created_at")

# Show transaction history
spark.sql("DESCRIBE HISTORY delta.`/data/orders`").show()
```

### Apache Iceberg
```python
# PySpark + Iceberg — verified catalog configuration
spark = SparkSession.builder \
    .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.0") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.my_catalog", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.my_catalog.type", "hadoop") \
    .config("spark.sql.catalog.my_catalog.warehouse", "s3://my-bucket/warehouse") \
    .getOrCreate()

# Schema evolution — no rewrite needed
spark.sql("ALTER TABLE my_catalog.db.orders ADD COLUMN delivery_date DATE")

# Partition evolution — change partitioning without rewriting
spark.sql("""
    ALTER TABLE my_catalog.db.orders 
    REPLACE PARTITION FIELD months(created_at) WITH days(created_at)
""")

# Time travel
spark.sql("SELECT * FROM my_catalog.db.orders TIMESTAMP AS OF '2024-01-14 00:00:00'")
spark.sql("SELECT * FROM my_catalog.db.orders VERSION AS OF 42")
```

**Iceberg vs Delta Lake vs Hudi:**
- **Delta Lake:** Best Spark integration (same company), widely adopted, MERGE support, Z-ordering
- **Apache Iceberg:** Vendor-neutral, strongest partition evolution, best multi-engine support (Spark, Flink, Trino, Presto, Hive)
- **Apache Hudi:** Strong at CDC/incremental pulls, record-level upserts, Hadoop-native

---

## 9. Data Warehouse Design

### Star Schema vs Snowflake Schema
```
Star Schema:
  Fact table (many rows) → directly connected to Dimension tables (fewer rows)
  Simple JOINs (one hop from fact to dimension)
  Denormalized dimensions (some redundancy, better query performance)
  Best for: BI tools, ad-hoc queries, OLAP cubes

Snowflake Schema:
  Fact table → Dimension tables → Sub-dimension tables (normalized)
  Multiple JOINs to get to fine-grained dimension data
  Better storage efficiency, harder to query
  Best for: complex domain models with shared dimension hierarchies
```

### Slowly Changing Dimensions (SCD)
```sql
-- SCD Type 1: Overwrite — no history kept
UPDATE dim_customers SET email = 'new@email.com' WHERE customer_id = 123;

-- SCD Type 2: Add new row — full history preserved (most common)
-- New columns: is_current (BOOLEAN), valid_from (DATE), valid_to (DATE)
-- When customer changes:
INSERT INTO dim_customers (customer_id, email, is_current, valid_from, valid_to)
VALUES (123, 'new@email.com', TRUE, CURRENT_DATE, '9999-12-31');

UPDATE dim_customers 
SET is_current = FALSE, valid_to = CURRENT_DATE - 1
WHERE customer_id = 123 AND is_current = TRUE AND email != 'new@email.com';

-- SCD Type 3: Add previous value column — only most recent change tracked
ALTER TABLE dim_customers ADD COLUMN previous_email VARCHAR;
UPDATE dim_customers 
SET previous_email = email, email = 'new@email.com'
WHERE customer_id = 123;
```

### Grain Definition
The grain is the most atomic unit of data in a fact table. Define explicitly before building.
```
Wrong grain: "the orders table" (ambiguous)
Correct grain: "one row per order line item" (clear, allows flexibility)
               "one row per order" (aggregated, faster but less flexible)

The grain determines:
  - What foreign keys can be included (matching level of detail)
  - What aggregations are pre-baked vs done at query time
  - Storage requirements
```

---

## 10. Kafka as Data Backbone

### Change Data Capture (CDC) with Debezium
```json
// Debezium PostgreSQL connector config — verified against Debezium 2.x
{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "plugin.name": "pgoutput",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "password",
    "database.dbname": "mydb",
    "database.server.name": "mydb-server",
    "table.include.list": "public.orders,public.customers",
    "publication.autocreate.mode": "filtered",
    "slot.name": "debezium_slot",
    "topic.prefix": "mydb"
  }
}

// Resulting Kafka topics:
//   mydb.public.orders → CDC events for orders table
//   mydb.public.customers → CDC events for customers table

// Event envelope (Debezium format):
{
  "before": { ... },  // row before change (null for INSERT)
  "after": { ... },   // row after change (null for DELETE)
  "op": "c",          // c=create, u=update, d=delete, r=read (snapshot)
  "ts_ms": 1705270000000
}
```

### Log Compaction for State Reconstruction
```
Log compaction: Kafka retains only the latest record per key (not all history)
Configured per topic: cleanup.policy=compact

Use case: materialized views from event sourcing
  Key: entity_id (e.g., product_id)
  Value: current state of the entity

Consumer can rebuild full current state by reading the compacted log from beginning.
New consumers don't need to replay all history — only latest state per key.

Combine: cleanup.policy=compact,delete to compact AND apply time-based retention.
```

---

## 11. DataOps

### CI/CD for Data Pipelines
```yaml
# GitHub Actions workflow for dbt pipeline
name: dbt CI
on: [pull_request]

jobs:
  dbt-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dbt
        run: pip install dbt-snowflake==1.7.0
      
      - name: dbt compile (syntax check)
        run: dbt compile --profiles-dir ./profiles --target ci
      
      - name: dbt test on staging schema
        run: |
          dbt run --target ci --select state:modified+
          dbt test --target ci --select state:modified+
        env:
          SNOWFLAKE_PASSWORD: ${{ secrets.SNOWFLAKE_CI_PASSWORD }}
```

### Data Contract Enforcement
```yaml
# Data contract — defines schema, SLAs, quality guarantees
# Tools: Soda, Great Expectations, custom validation

data_contract:
  name: orders-v2
  version: "2.0.0"
  owner: "data-engineering@company.com"
  
  schema:
    - name: order_id
      type: string
      required: true
      unique: true
    - name: total
      type: decimal(10,2)
      required: true
      minimum: 0
    - name: status
      type: string
      enum: ["pending", "completed", "cancelled"]
  
  sla:
    freshness: "< 2 hours"
    completeness: "> 99.5%"
    uptime: "99.9%"
```

### Environment Promotion (dev → staging → prod)
```
dev: engineer's personal schema (dbt dev target), no production data
staging: shared, production-sized data subset, integration tests run here
prod: production, restricted access, automated deployment only

dbt target configuration:
  profiles.yml defines targets (dev, staging, prod) with different schemas/databases
  
Promotion gate: CI must pass, data quality checks must pass, peer review
Never: deploy directly from laptop to prod (all promotions via CI/CD)
```

---

## Cross-Domain Connections

**Data Engineering ↔ Databases:** The operational database's schema design determines how difficult CDC and incremental extraction are. A table with no `updated_at` column cannot be incrementally extracted without CDC or full scans. SCD Type 2 in the warehouse requires a surrogate key strategy agreed upon with backend engineers.

**Data Engineering ↔ SRE:** Data pipelines need their own SLOs: freshness SLO ("data is no more than 2 hours stale"), completeness SLO ("99.5% of expected rows present"), latency SLO ("pipeline completes within 4 hours of start"). Airflow DAGs should have alerting as rigorous as any production service.

**Data Engineering ↔ Observability:** Instrument data pipelines: emit metrics (rows_processed, rows_failed, processing_lag_seconds), structured logs (same JSON format as application logs, with trace_id when possible), and job-level spans. Airflow integrates with StatsD/OpenTelemetry. Spark has a Prometheus sink (`spark.metrics.conf`).

**Data Engineering ↔ Backend Engineering:** Backend engineers who use `SELECT *` and never delete stale data create downstream data engineering problems. A backend engineer who adds a new non-nullable column without a default breaks the CDC consumer. Data contracts enforce mutual accountability.

---

## Self-Review Checklist

```
Pipeline Design
□ 1. DAGs are idempotent — re-running produces same result (tested, not assumed)
□ 2. DAGs are atomic — each task fully succeeds or fully rolls back
□ 3. XCom is used only for small metadata (paths, counts), not dataframes
□ 4. catchup=False set on Airflow DAGs unless backfill is explicitly intended
□ 5. Sensors use mode='reschedule' not mode='poke' to avoid holding worker slots

Spark
□ 6. spark.sql.shuffle.partitions tuned for data volume (not default 200)
□ 7. Adaptive Query Execution enabled for Spark 3.0+ jobs
□ 8. Data skew investigated via Spark UI stage task duration histogram
□ 9. Broadcast joins used for all small dimension tables
□ 10. Shuffle operations minimized — transformations ordered to filter before joining

dbt
□ 11. All fact and dimension tables have not_null + unique tests on primary keys
□ 12. Referential integrity tests (relationships) defined for foreign keys
□ 13. Incremental models use unique_key to prevent duplicate rows
□ 14. Sources defined in schema.yml with freshness checks

Data Quality
□ 15. Data quality checks fail the pipeline — not just emit warnings
□ 16. Schema evolution is handled explicitly (not silently ignored)
□ 17. Dead letter queue exists for records that fail quality checks

Reliability
□ 18. Data SLOs defined (freshness, completeness) with alerting
□ 19. Checkpointing configured for Flink streaming jobs
□ 20. CI/CD pipeline runs dbt compile + dbt test on every PR before merge
```
