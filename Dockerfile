FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    dos2unix \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install poetry
RUN python -m pip install --upgrade pip && \
    pip install poetry

# Copy dependency files
COPY ./poetry.lock ./poetry.lock
COPY ./pyproject.toml ./pyproject.toml

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false
RUN poetry install --no-root --only main

# Copy application code
COPY ./src ./src
COPY ./alembic.ini ./alembic.ini
COPY src/alembic ./alembic

# Set environment variables
ENV PYTHONPATH=/usr/src/app/src
ENV ALEMBIC_CONFIG=/usr/src/app/alembic.ini

# Change to src directory for proper module resolution
WORKDIR /usr/src/app/src

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]