# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared fixtures and --env enforcement for cloud_dog_jobs tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TEMP_DB_NAME = "cloud_dog_ai_jobs_it_tmp"
REDIS_KEY_PREFIX = "cloud_dog_ai_jobs_it_tmp"
REQUIRED_VAULT_VARS = ("VAULT_ADDR", "VAULT_TOKEN", "VAULT_MOUNT_POINT", "VAULT_CONFIG_PATH")
VAULT_PRECONDITION_HINT = "Source env-vault first: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"
ENV_TIER_TOKENS = {"UT", "ST", "IT", "AT", "QT", "PT", "CT"}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add mandatory --env option for environment file path(s)."""
    parser.addoption(
        "--env",
        action="append",
        default=None,
        help="Required env file path(s). Can be repeated or comma-separated.",
    )


def _normalise_env_files(raw: list[str] | None) -> list[str]:
    """Normalise raw --env inputs into an ordered list of env file paths."""
    out: list[str] = []
    tests_dir = Path(__file__).resolve().parent
    for value in raw or []:
        for part in value.split(","):
            candidate = part.strip()
            if candidate:
                token = candidate.upper()
                if token in ENV_TIER_TOKENS:
                    tier_file = tests_dir / f"env-{token}"
                    if tier_file.is_file():
                        out.append(str(tier_file))
                else:
                    out.append(candidate)
    return out


def _load_env_file(path: str) -> dict[str, str]:
    """Load key/value pairs from an env file."""
    env: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise pytest.UsageError(f"Invalid env line in {path}: {line}")
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


@pytest.fixture(scope="session", autouse=True)
def _enforce_and_load_env(request: pytest.FixtureRequest) -> None:
    """Require --env files and inject variables into the process environment."""
    env_files = _normalise_env_files(request.config.getoption("--env"))
    if not env_files:
        raise pytest.UsageError("Missing required --env <file>.")
    locked = set(os.environ.keys())
    merged: dict[str, str] = {}
    for path in env_files:
        if not Path(path).is_file():
            raise pytest.UsageError(f"Env file not found: {path}")
        for key, value in _load_env_file(path).items():
            if key in locked:
                continue
            merged[key] = value
    os.environ.update(merged)


@pytest.fixture(scope="session")
def env_tier() -> str:
    """Return the current test environment tier from loaded env files."""
    tier = str(os.environ.get("TEST_ENV_TIER", "")).strip().upper()
    if tier not in {"UT", "ST", "IT", "AT", "QT"}:
        pytest.fail(
            "TEST_ENV_TIER must be set to one of UT/ST/IT/AT/QT via --env file.",
            pytrace=False,
        )
    return tier


@pytest.fixture(scope="session")
def vault_env() -> dict[str, str]:
    """Return Vault variables if present; tests decide whether to hard-fail."""
    return {k: str(os.environ.get(k, "")) for k in REQUIRED_VAULT_VARS}


def missing_vault_vars(vault_env: dict[str, str]) -> list[str]:
    """Return missing Vault variable names for current run."""
    return [k for k in REQUIRED_VAULT_VARS if not vault_env.get(k)]


def _load_vault_dev_config(vault_env: dict[str, str]) -> dict[str, Any]:
    """Read dev config section from Vault."""
    missing = missing_vault_vars(vault_env)
    if missing:
        pytest.fail(f"Vault credentials not in environment (missing: {', '.join(missing)}). {VAULT_PRECONDITION_HINT}")
    url = f"{vault_env['VAULT_ADDR']}/v1/{vault_env['VAULT_MOUNT_POINT']}/data/{vault_env['VAULT_CONFIG_PATH']}"
    cmd = ["curl", "-sS", "-H", f"X-Vault-Token: {vault_env['VAULT_TOKEN']}", url]
    try:
        raw = subprocess.check_output(cmd, text=True)
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"Vault is not reachable in this environment ({exc}). {VAULT_PRECONDITION_HINT}")
    data = json.loads(raw)
    return data["data"]["data"]["json"]["dev"]


@pytest.fixture(scope="session")
def sqlite_database_url() -> str:
    """Return a SQLite URL for integration tests."""
    return "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="session")
def mysql_database_url(vault_env: dict[str, str]) -> str | None:
    """Create/drop a temporary MySQL database and return SQLAlchemy URL."""
    if missing_vault_vars(vault_env):
        yield None
        return
    provider = _load_vault_dev_config(vault_env)["databases"]["providers"]["mysql"]
    cmd = [
        "mysql",
        "--protocol=TCP",
        "-h",
        str(provider["host"]),
        "-P",
        str(provider["port"]),
        "-u",
        str(provider["username"]),
        f"-p{provider['password']}",
        "-e",
        f"DROP DATABASE IF EXISTS {TEMP_DB_NAME}; CREATE DATABASE {TEMP_DB_NAME};",
    ]
    subprocess.check_call(cmd)
    try:
        yield (
            f"mysql+pymysql://{provider['username']}:{provider['password']}"
            f"@{provider['host']}:{provider['port']}/{TEMP_DB_NAME}"
        )
    finally:
        cleanup_cmd = [
            "mysql",
            "--protocol=TCP",
            "-h",
            str(provider["host"]),
            "-P",
            str(provider["port"]),
            "-u",
            str(provider["username"]),
            f"-p{provider['password']}",
            "-e",
            f"DROP DATABASE IF EXISTS {TEMP_DB_NAME};",
        ]
        subprocess.check_call(cleanup_cmd)


@pytest.fixture(scope="session")
def postgres_database_url(vault_env: dict[str, str]) -> str | None:
    """Create/drop a temporary PostgreSQL database and return SQLAlchemy URL."""
    if missing_vault_vars(vault_env):
        yield None
        return
    provider = _load_vault_dev_config(vault_env)["databases"]["providers"]["postgres"]
    env = os.environ.copy()
    env["PGPASSWORD"] = str(provider["password"])
    psql_base = [
        "psql",
        f"host={provider['host']} port={provider['port']} user={provider['username']} dbname=postgres sslmode=disable",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
    ]
    subprocess.check_call(psql_base + [f"DROP DATABASE IF EXISTS {TEMP_DB_NAME};"], env=env)
    subprocess.check_call(psql_base + [f"CREATE DATABASE {TEMP_DB_NAME};"], env=env)
    try:
        yield (
            f"postgresql+psycopg2://{provider['username']}:{provider['password']}"
            f"@{provider['host']}:{provider['port']}/{TEMP_DB_NAME}"
        )
    finally:
        terminate = (
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            f"WHERE datname = '{TEMP_DB_NAME}' AND pid <> pg_backend_pid();"
        )
        subprocess.check_call(psql_base + [terminate], env=env)
        subprocess.check_call(psql_base + [f"DROP DATABASE IF EXISTS {TEMP_DB_NAME};"], env=env)


@pytest.fixture(scope="session")
def redis_url(vault_env: dict[str, str]) -> str | None:
    """Build a Redis URL from Vault redis.valkey0 config."""
    if missing_vault_vars(vault_env):
        return None
    entry = _load_vault_dev_config(vault_env)["redis"]["valkey0"]
    return f"redis://{entry['username']}:{entry['password']}@{entry['host']}:{entry['port']}/{entry['db']}"
