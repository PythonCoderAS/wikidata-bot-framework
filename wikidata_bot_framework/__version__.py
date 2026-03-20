from importlib.metadata import version as get_version, PackageNotFoundError

try:
    package = __package__ or "wikidata_bot_framework"
    __version__ = get_version(package)
except PackageNotFoundError:
    # This can be hit during tests
    __version__ = "9.0.0"
version_info = tuple(__version__.split("."))
