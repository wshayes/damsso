FROM python:3.12-slim

# System deps for python3-saml (xmlsec1) and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    xmlsec1 \
    libxml2-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory to project root for installation
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY example/ ./example/

# Install the package and dependencies
RUN uv pip install --system -e "." && \
    uv pip install --system psycopg2-binary python-dotenv

# Copy entrypoint
COPY docker/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run from example/ directory
WORKDIR /app/example

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
