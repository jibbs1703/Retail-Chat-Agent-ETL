ARG AIRFLOW_VERSION=3.0.0
FROM apache/airflow:${AIRFLOW_VERSION}

COPY docker/requirements.txt /requirements.txt

USER airflow
RUN pip install --no-cache-dir -r /requirements.txt

USER root
RUN rm -f /requirements.txt
USER airflow

COPY --chown=airflow:root dags /opt/airflow/dags
COPY --chown=airflow:root config /opt/airflow/config
COPY --chown=airflow:root queries /opt/airflow/queries
COPY --chown=airflow:root utilities /opt/airflow/utilities

USER root
RUN mkdir -p /opt/airflow/plugins && chown -R airflow:root /opt/airflow/plugins
USER airflow
