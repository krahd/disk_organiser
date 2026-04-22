FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# install system deps
RUN apt-get update && apt-get install -y build-essential --no-install-recommends && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

# Create a non-root user for improved container security and set ownership
RUN groupadd -g 1000 appgroup || true \
	&& useradd -r -u 1000 -g appgroup app || true \
	&& chown -R app:appgroup /app

USER app

EXPOSE 8000
CMD ["gunicorn", "backend.app:app", "-b", "0.0.0.0:8000", "--workers", "2"]
