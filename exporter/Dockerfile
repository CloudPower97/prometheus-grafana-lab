FROM python:3.9-slim
RUN pip install prometheus_client
COPY fake_exporter.py /app/
WORKDIR /app
CMD ["python", "fake_exporter.py"]
