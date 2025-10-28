# ops/airflow_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from pipeline.process_conversations import main as process_main

def run_pipeline(**context):
    process_main()

with DAG(
    dag_id="cxqa_daily",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 * * * *",  # hourly
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
) as dag:
    process = PythonOperator(
        task_id="process_conversations",
        python_callable=run_pipeline,
        provide_context=True,
    )
