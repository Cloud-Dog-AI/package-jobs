"""QT regression: cloud_dog_jobs.broker subpackage must be importable.

W28B-330 fix: the broker subpackage was missing from the published wheel
because the .py source files were absent (only __pycache__ existed).
This test ensures the broker module and its key classes are always present.
"""

import importlib
import pathlib


def test_broker_subpackage_importable():
    """cloud_dog_jobs.broker must be importable."""
    mod = importlib.import_module("cloud_dog_jobs.broker")
    assert mod is not None


def test_broker_capacity_importable():
    """cloud_dog_jobs.broker.capacity.CapacityEnforcer must be importable."""
    from cloud_dog_jobs.broker.capacity import CapacityEnforcer
    assert CapacityEnforcer is not None


def test_broker_source_files_exist():
    """broker/ must contain .py source files, not just __pycache__."""
    import cloud_dog_jobs.broker as broker_mod
    broker_dir = pathlib.Path(broker_mod.__file__).parent
    py_files = sorted(p.name for p in broker_dir.glob("*.py"))
    assert "__init__.py" in py_files, "broker/__init__.py missing"
    assert "capacity.py" in py_files, "broker/capacity.py missing"
    assert len(py_files) >= 3, f"Expected >=3 .py files in broker/, got {py_files}"
