# Contributing to Django Allauth Multi-Tenant SSO

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - **Required** (this project uses uv exclusively for package management)
- Git

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/yourusername/django-allauth-multitenant-sso.git
   cd django-allauth-multitenant-sso
   ```

2. **Install dependencies:**
   ```bash
   uv pip install -e ".[test]"
   ```
   
   **Note:** This project uses [uv](https://github.com/astral-sh/uv) exclusively for package management. See [AGENTS.md](AGENTS.md) for more details.

3. **Install pre-commit hooks:**
   ```bash
   uv pip install pre-commit
   pre-commit install
   ```

4. **Run tests to verify setup:**
   ```bash
   pytest tests/ -v
   ```

## Development Workflow

### 1. Create a Branch

Create a feature branch from `main`:
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write clean, readable code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

Before committing, ensure all tests pass:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=src/django_allauth_multitenant_sso --cov-report=term
```

### 4. Run Pre-commit Hooks

Pre-commit hooks will run automatically on commit, but you can run them manually:
```bash
pre-commit run --all-files
```

### 5. Commit Your Changes

Write clear, descriptive commit messages:
```bash
git commit -m "Add feature: description of what you added"
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use Black for code formatting (line length: 100)
- Use isort for import sorting
- Use type hints where appropriate
- Maximum line length: 100 characters

### Django Conventions

- Follow Django's coding style guidelines
- Use Django's model conventions
- Write docstrings for classes and functions
- Use Django's translation framework for user-facing strings

### Code Formatting

The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **ruff** for linting

These are configured in `.pre-commit-config.yaml` and will run automatically.

## Testing

### Writing Tests

- Write tests for all new functionality
- Aim for high test coverage (target: 80%+)
- Use descriptive test names
- Follow the existing test structure

### Test Structure

Tests are located in the `tests/` directory:
- `test_models.py` - Model tests
- `test_forms.py` - Form tests
- `test_views.py` - View tests
- `test_adapters.py` - Adapter tests
- `test_providers.py` - SSO provider tests
- `test_decorators.py` - Decorator tests
- `test_emails.py` - Email functionality tests

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run specific test
pytest tests/test_models.py::TestTenant::test_create_tenant -v

# Run with coverage
pytest tests/ --cov=src/django_allauth_multitenant_sso --cov-report=term
```

## Documentation

### Documentation Standards

- Update README.md for user-facing changes
- Update CHANGELOG.md for all changes
- Add docstrings to new functions and classes
- Update architecture docs if needed

### Documentation Files

- `README.md` - Main documentation
- `docs/architecture.md` - Technical architecture
- `docs/quickstart.md` - Quick start guide
- `docs/email-configuration.md` - Email setup guide
- `TEST_COVERAGE.md` - Test coverage report
- `CHANGELOG.md` - Version history

## Pull Request Process

### Before Submitting

1. ✅ All tests pass
2. ✅ Code follows style guidelines
3. ✅ Pre-commit hooks pass
4. ✅ Documentation updated
5. ✅ CHANGELOG.md updated
6. ✅ No merge conflicts

### PR Description

Include in your PR description:
- What changes you made
- Why you made them
- How to test the changes
- Any breaking changes
- Related issues

### Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged

## Reporting Issues

### Bug Reports

When reporting bugs, please include:
- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (Python version, Django version, etc.)
- Error messages or stack traces

### Feature Requests

For feature requests, please include:
- Description of the feature
- Use case or motivation
- Proposed implementation (if you have ideas)

## Development Tools

### Using Just

The project includes a `justfile` with common development tasks:

```bash
# Install just: https://github.com/casey/just

# Run tests
just test

# Run tests with coverage
just test-cov

# Format code
just format

# Lint code
just lint

# Run all checks
just check

# Build package
just build

# Clean build artifacts
just clean
```

## Questions?

If you have questions or need help:
- Open an issue on GitHub
- Check existing issues and discussions
- Review the documentation

Thank you for contributing! 🎉

