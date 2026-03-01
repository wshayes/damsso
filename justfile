# Justfile for django-allauth-multitenant-sso
# Install just: https://github.com/casey/just
# Usage: just <recipe>

# Default recipe
default:
    @just --list

# Setup and installation
# Note: This project uses uv exclusively for package management
setup:
    #!/usr/bin/env bash
    echo "Setting up development environment..."
    uv pip install -e ".[test]"
    echo "Installing pre-commit hooks..."
    uv pip install pre-commit
    pre-commit install
    echo "✅ Setup complete!"

# Testing
test:
    #!/usr/bin/env bash
    pytest tests/ -v --no-migrations

test-cov:
    #!/usr/bin/env bash
    pytest tests/ --cov=src/django_allauth_multitenant_sso --cov-report=term --cov-report=html --no-migrations
    echo "Coverage report generated in htmlcov/index.html"

test-file file:
    #!/usr/bin/env bash
    pytest tests/{{file}} -v --no-migrations

test-watch:
    #!/usr/bin/env bash
    pytest-watch tests/ --no-migrations

# Code quality
format:
    #!/usr/bin/env bash
    echo "Formatting code with black..."
    black src/ tests/ example/
    echo "Sorting imports with isort..."
    isort src/ tests/ example/
    echo "Formatting with ruff..."
    ruff format src/ tests/ example/
    echo "✅ Formatting complete!"

lint:
    #!/usr/bin/env bash
    echo "Running ruff..."
    ruff check src/ tests/ example/
    echo "Running black check..."
    black --check src/ tests/ example/
    echo "Running isort check..."
    isort --check-only src/ tests/ example/
    echo "✅ Linting complete!"

lint-fix:
    #!/usr/bin/env bash
    echo "Fixing linting issues..."
    ruff check --fix src/ tests/ example/
    black src/ tests/ example/
    isort src/ tests/ example/
    echo "✅ Linting fixes applied!"

type-check:
    #!/usr/bin/env bash
    mypy src/django_allauth_multitenant_sso --ignore-missing-imports

# Pre-commit
pre-commit:
    #!/usr/bin/env bash
    pre-commit run --all-files

pre-commit-install:
    #!/usr/bin/env bash
    pre-commit install

# All checks
check: lint test
    @echo "✅ All checks passed!"

# Building
build:
    #!/usr/bin/env bash
    echo "Building package..."
    python -m build
    echo "✅ Build complete! Check dist/ directory"

build-wheel:
    #!/usr/bin/env bash
    python -m build --wheel

build-sdist:
    #!/usr/bin/env bash
    python -m build --sdist

# Cleaning
clean:
    #!/usr/bin/env bash
    echo "Cleaning build artifacts..."
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info
    rm -rf .pytest_cache/
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf .ruff_cache/
    find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    echo "✅ Clean complete!"

clean-all: clean
    #!/usr/bin/env bash
    echo "Cleaning virtual environment..."
    rm -rf .venv/
    echo "✅ Deep clean complete!"

# Example demo site setup
example-setup:
    #!/usr/bin/env bash
    echo "Setting up example demo site..."
    echo "Installing package in editable mode..."
    uv pip install -e .
    echo "Installing Django and dependencies..."
    uv pip install django django-allauth python3-saml authlib cryptography
    echo "Running migrations..."
    cd example && python manage.py migrate
    echo "✅ Example demo site setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Create a superuser: just example-createsuperuser"
    echo "  2. Start the server: just dev"
    echo "  3. Access admin at: http://localhost:8000/admin/"


example-reset:
    #!/usr/bin/env bash
    echo "Resetting example demo site (removes database)..."
    cd example && rm -f db.sqlite3
    echo "Running migrations..."
    cd example && python manage.py migrate
    echo "✅ Example demo site reset complete!"
    echo "Create a superuser: just example-createsuperuser"

example-createsuperuser:
    #!/usr/bin/env bash
    cd example && echo "from django.contrib.auth import get_user_model; User = get_user_model(); exists = User.objects.filter(username='demo').exists(); User.objects.create_superuser('demo', '', 'demo') if not exists else None; print('Superuser created: demo/demo' if not exists else 'Superuser demo already exists')" | python manage.py shell

# Development server
dev:
    #!/usr/bin/env bash
    cd example && python manage.py runserver

dev-migrate:
    #!/usr/bin/env bash
    cd example && python manage.py migrate

dev-makemigrations:
    #!/usr/bin/env bash
    cd example && python manage.py makemigrations

dev-shell:
    #!/usr/bin/env bash
    cd example && python manage.py shell

dev-createsuperuser:
    #!/usr/bin/env bash
    cd example && python manage.py createsuperuser

# Database
db-reset:
    #!/usr/bin/env bash
    cd example && rm -f db.sqlite3 && python manage.py migrate && python manage.py createsuperuser

# Documentation
docs-dev:
    #!/usr/bin/env bash
    echo "Installing documentation dependencies..."
    uv pip install -e ".[docs]"
    echo "Starting MkDocs development server..."
    echo "Open http://localhost:8088 in your browser"
    mkdocs serve --dev-addr=0.0.0.0:8088

docs-build:
    #!/usr/bin/env bash
    echo "Installing documentation dependencies..."
    uv pip install -e ".[docs]"
    echo "Building documentation..."
    mkdocs build
    echo "✅ Documentation built in site/ directory"

docs-publish:
    #!/usr/bin/env bash
    echo "Installing documentation dependencies..."
    uv pip install -e ".[docs]"
    echo "Building documentation..."
    mkdocs build
    echo "Publishing to GitHub Pages..."
    mkdocs gh-deploy
    echo "✅ Documentation published!"

# Package verification
verify:
    #!/usr/bin/env bash
    echo "Verifying package build..."
    python -m build --wheel
    echo "Checking package contents..."
    python -m zipfile -l dist/*.whl | head -20
    echo "✅ Package verification complete!"

install-local:
    #!/usr/bin/env bash
    echo "Installing local package..."
    uv pip install dist/*.whl
    echo "✅ Package installed!"

# Version management
version:
    #!/usr/bin/env bash
    echo "Current version:"
    grep "^version" pyproject.toml

# Migration management
makemigrations:
    #!/usr/bin/env bash
    cd example && python manage.py makemigrations django_allauth_multitenant_sso

migrate:
    #!/usr/bin/env bash
    cd example && python manage.py migrate

# Coverage report
coverage:
    #!/usr/bin/env bash
    pytest tests/ --cov=src/django_allauth_multitenant_sso --cov-report=term --cov-report=html --no-migrations
    echo "Opening coverage report..."
    open htmlcov/index.html || xdg-open htmlcov/index.html || echo "Please open htmlcov/index.html manually"

# Docker demo environment
docker-up:
    #!/usr/bin/env bash
    echo "Starting Docker demo environment..."
    cd docker && docker compose up --build -d
    echo "Waiting for services to start..."
    cd docker && docker compose logs -f django &
    LOGS_PID=$!
    # Wait for Django to be ready
    until curl -s http://localhost:8000 > /dev/null 2>&1; do sleep 2; done
    kill $LOGS_PID 2>/dev/null || true
    echo ""
    echo "Demo environment is ready! See above for URLs and credentials."

docker-down:
    cd docker && docker compose down

docker-logs *args:
    cd docker && docker compose logs -f {{args}}

docker-logs-django:
    cd docker && docker compose logs -f django

docker-restart:
    cd docker && docker compose restart django

docker-shell:
    cd docker && docker compose exec django python manage.py shell

docker-reset:
    #!/usr/bin/env bash
    echo "Resetting Docker demo environment (removing volumes)..."
    cd docker && docker compose down -v
    echo "Done. Run 'just docker-up' to start fresh."

docker-seed:
    cd docker && docker compose exec django python manage.py seed_demo_data

docker-ps:
    cd docker && docker compose ps

# Help
help:
    @echo "Available commands:"
    @just --list

