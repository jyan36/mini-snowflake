FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY tests /app/tests
COPY examples /app/examples
COPY benchmark.py /app/

ENV PYTHONPATH=/app/src

RUN pip install --no-cache-dir -e .

CMD ["python3", "benchmark.py"]
