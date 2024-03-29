import pywikibot.config
import pytest


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--simulate",
        action="store_true",
        default=False,
        help="Run tests in simulation mode",
    )


def pytest_configure(config: pytest.Config):
    if config.getoption("--simulate"):
        pywikibot.handle_args(["-simulate"])


@pytest.fixture(autouse=True)
def block_getpass(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("getpass.getpass", lambda *_, **__: "")
