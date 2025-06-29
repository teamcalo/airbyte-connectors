
FROM airbyte/python-connector-base:4.0.0

COPY . ./airbyte/integration_code
RUN pip3 install --no-cache-dir -r ./airbyte/integration_code/requirements.txt

ENV AIRBYTE_ENTRYPOINT "python /airbyte/integration_code/main.py"
ENTRYPOINT ["python", "/airbyte/integration_code/main.py"]