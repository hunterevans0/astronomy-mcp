import pytest

from astronomy_mcp import location
from astronomy_mcp.location import Location

MOAB = Location(38.5733, -109.5498, 1227.0, "America/Denver", name="Moab", bortle=2)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.astronomy-mcp."""
    monkeypatch.setenv("ASTRONOMY_MCP_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def moab():
    location.save_default(MOAB)
    return MOAB
