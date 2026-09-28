import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets an isolated SQLite database and empty in-memory cache."""
    from backend import db
    from backend.cache import store
    db.set_db_path(tmp_path / "test.db")
    db.migrate()
    store._memory.clear()
    yield
    db.set_db_path(None)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("OMNI_NETWORK_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="network test — set OMNI_NETWORK_TESTS=1 to run")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
