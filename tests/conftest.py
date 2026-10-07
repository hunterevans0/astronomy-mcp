import pytest

from astronomy_mcp import jupiter, location, satellites
from astronomy_mcp.location import Location

MOAB = Location(38.5733, -109.5498, 1227.0, "America/Denver", name="Moab", bortle=2)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.astronomy-mcp."""
    monkeypatch.setenv("ASTRONOMY_MCP_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def offline_reference_data(monkeypatch, request):
    """Small downloads that otherwise ride along with offline tools: the Red Spot table and SATCAT."""
    if request.node.get_closest_marker("live"):
        return

    async def built_in_grs():
        return jupiter.BUILT_IN_GRS

    async def no_rcs():
        return {}

    monkeypatch.setattr(jupiter, "current_grs_model", built_in_grs)
    monkeypatch.setattr(satellites, "rcs_table", no_rcs)


@pytest.fixture
def moab():
    location.save_default(MOAB)
    return MOAB
