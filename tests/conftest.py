import pywikibot
import pytest


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--simulate",
        action="store_true",
        default=False,
        help="Run tests in simulation mode",
    )

@pytest.fixture(autouse=True)
def block_getpass(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("getpass.getpass", lambda *_, **__: "")
