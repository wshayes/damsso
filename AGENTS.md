# Agent Guidelines

This document provides guidelines for AI agents and automated tools working on this project.

## Package Management

**This project uses [uv](https://github.com/astral-sh/uv) exclusively for package management.**

- Always use `uv pip install` instead of `pip install`
- Use `uv pip install -e .` for editable installs
- Use `uv pip install -e ".[test]"` for installing with test dependencies
- Do not use `pip`, `pipenv`, `poetry`, or other package managers
- When creating scripts or documentation, prefer `uv` commands

### Examples

```bash
# Install package in editable mode
uv pip install -e .

# Install with test dependencies
uv pip install -e ".[test]"

# Install a specific package
uv pip install package-name

# Install from requirements (if needed)
uv pip install -r requirements.txt
```

## Project Structure

- Source code is in `src/django_allauth_multitenant_sso/`
- Tests are in `tests/`
- Example project is in `example/`
- Documentation files are in the root directory

## Code Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use isort for import sorting
- Use ruff for linting
- Run `just format` before committing
- Run `just lint` to check code quality

## Testing

- All tests are in the `tests/` directory
- Use pytest for testing
- Run tests with: `just test` or `pytest tests/ -v`
- Run with coverage: `just test-cov`
- Tests should be comprehensive and maintain high coverage

## Development Workflow

- Use `just` commands for common tasks (see `justfile`)
- Always run `just check` before committing
- Pre-commit hooks are configured and should pass
- Update `CHANGELOG.md` for user-facing changes

## Documentation

- Keep README.md up to date
- Update relevant documentation files when making changes
- Add docstrings to new functions and classes
- Follow existing documentation patterns

## Dependencies

- Core dependencies are in `pyproject.toml`
- Test dependencies are in `[project.optional-dependencies.test]`
- Always specify version constraints
- Keep dependencies up to date

## Example Project

- The example project in `example/` demonstrates package usage
- Use `just example-setup` to set up the example
- Keep the example project working and up to date

## Commits and Pull Requests

- Write clear, descriptive commit messages
- Update CHANGELOG.md for significant changes
- Ensure all tests pass before submitting PRs
- Follow the contributing guidelines in CONTRIBUTING.md

## Important Notes

- This is a Django package that extends django-allauth
- Support Python 3.10+
- Support Django 4.2+
- Maintain backward compatibility when possible
- Security is important - follow security best practices

## Quick Reference

```bash
# Setup
just setup

# Test
just test

# Format
just format

# Lint
just lint

# Check everything
just check

# Build
just build

# Example setup
just example-setup
```

## Questions?

Refer to:
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [README.md](README.md) - Project documentation
- [docs/architecture.md](docs/architecture.md) - Technical architecture

