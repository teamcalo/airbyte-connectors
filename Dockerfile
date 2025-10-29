
FROM airbyte/python-connector-base:4.1.0

ARG CONNECTOR_PATH
ENV AIRBYTE_ENTRYPOINT="python /airbyte/main.py"

WORKDIR /airbyte
COPY $CONNECTOR_PATH .
RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "/airbyte/main.py"]