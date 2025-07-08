
FROM airbyte/python-connector-base:4.0.0

COPY . /airbyte
RUN pip3 install --no-cache-dir -r /airbyte/requirements.txt

ENV AIRBYTE_ENTRYPOINT="python /airbyte/main.py"
ENTRYPOINT ["python", "/airbyte/main.py"]