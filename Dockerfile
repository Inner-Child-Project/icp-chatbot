FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

RUN mkdir -p /app/data

ENV PYTHONPATH=/app
ENV CHECKPOINT_DB=/app/data/checkpoints.db

EXPOSE 8100
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8100"]
