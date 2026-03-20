from importlib.metadata import version as get_version, PackageNotFoundError

try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    # This can be hit during tests
    __version__ = "8.0.0"
version_info = tuple(__version__.split("."))
