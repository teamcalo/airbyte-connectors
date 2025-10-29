
FROM --platform=arm64 airbyte/python-connector-base:4.1.0

ARG CONNECTOR_PATH

WORKDIR /airbyte
COPY ${CONNECTOR_PATH} .
RUN pip3 install --no-cache-dir -r requirements.txt

ENV AIRBYTE_ENTRYPOINT "python /airbyte/main.py"
ENTRYPOINT ["python", "/airbyte/main.py"]