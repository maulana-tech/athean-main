"""CLOB backend abstraction — swap Polymarket for Bybit (or others) via env var."""

from strategos.backends.base import ClobClient
from strategos.backends.bybit import BybitClobClient

__all__ = ["ClobClient", "BybitClobClient"]
