# Build Instructions

## Package
`cloud-dog-jobs` - job orchestration, queueing, and backend adapters.

## Prerequisites
- Python 3.10+
- pip

## Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip build twine
pip install -e ".[dev]"
```

If your environment resolves dependencies from an additional package index:
```bash
PYPI_URL=https://packages.example.com/simple/
pip install -e ".[dev]" --extra-index-url "$PYPI_URL"
```

## Local Use
Install the package in editable mode and import it from an interactive shell or another local project:
```bash
python -c "import cloud_dog_jobs; print('package import ok')"
```

## Run Tests
```bash
ruff check cloud_dog_jobs tests
ruff format --check cloud_dog_jobs tests
python -m pytest tests/quality --env ./.env.test -v
python -m pytest tests/unit --env ./.env.test -v
python -m pytest tests/system --env ./.env.test -v
python -m pytest tests/integration --env ./.env.test -v
python -m pytest tests/application --env ./.env.test -v
python -m pytest tests/security --env ./.env.test -v
```

## Build Distribution
```bash
python -m build --no-isolation
```

## Publish
```bash
twine upload --repository-url "$PYPI_URL" dist/*
```

## Docker Packaging
If you consume this package during a container build, pass the package index via environment variables:
```bash
PYPI_URL=https://packages.example.com/simple/ \
PYPI_USERNAME=build-user \
PYPI_PASSWORD=build-password \
docker build -t cloud-dog-jobs:latest .
```

## Dependencies
- runtime dependencies include `httpx`, `redis`, and `sqlalchemy`
- optional extras for Alembic, Redis, and FastAPI are declared in `pyproject.toml`

## Configuration
Tests and sample programs can read configuration from shell variables, a local env file, and package defaults where available.

## Vault Integration
Optional secret-backed test runs can load settings from a standard Vault client configuration:
```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=your-token
export VAULT_MOUNT_POINT=your-mount
export VAULT_CONFIG_PATH=your-path
```
