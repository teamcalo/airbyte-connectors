
FROM airbyte/python-connector-base:3.0.0

COPY . ./airbyte/integration_code
RUN pip3 install --no-cache-dir -r ./airbyte/integration_code/requirements.txt