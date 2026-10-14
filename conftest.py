import glob
import os
import runpy

import pytest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Builds empty tables in a temporary folder so tests never touch the real tickets.db."""
    scripts = sorted(glob.glob(os.path.join(PROJECT_ROOT, "build_ticket*.py")))
    scripts += sorted(glob.glob(os.path.join(PROJECT_ROOT, "build_traces*.py")))
    monkeypatch.chdir(tmp_path)
    for script in scripts:
        runpy.run_path(script, run_name="__main__")
    return tmp_path / "tickets.db"