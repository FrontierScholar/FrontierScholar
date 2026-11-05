"""FrontierScholar fs: the command-line client for fs-api v1, and the small Python client it uses (Client)."""

__version__ = "0.2.0"
API_MAJOR = "fs-api/1"

from .client import Client, FsError, DEFAULT_BASE  # noqa: E402

__all__ = ["Client", "FsError", "DEFAULT_BASE", "__version__", "API_MAJOR"]
