"""Simple Test DAG for Airflow Setup Verification."""

from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="jackets_products_dag",
    description="Jackets Product Ingestion DAG",
    schedule="0 * * * *",  # Runs every hour
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["Jackets", "ETL","Products"],
)
def jackets_products_etl():
    """Simple ETL DAG using TaskFlow API."""

    @task
    def relational_database_check() -> str:
        """Relational database check."""
        message = "Hello Relational Database Check"
        print(message)
        return message
    
    @task
    def vector_database_check() -> str:
        """Vector database check."""
        message = "Hello Vector Database Check"
        print(message)
        return message
    
    relational_database_check()
    vector_database_check()


jackets_products_etl()
