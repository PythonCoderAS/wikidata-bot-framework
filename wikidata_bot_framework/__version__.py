from importlib.metadata import version as get_version

__version__ = get_version(__package__)
version_info = tuple(__version__.split("."))
