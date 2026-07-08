FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY ewa/ ewa/
COPY data/ data/
COPY docs/personal-site-schema.sql docs/

EXPOSE 8000

CMD ["uvicorn", "ewa.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
