from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .settings import logger


@dataclass
class _CacheEntry:
    path: Path
    lines: Optional[List[str]] = None
    mtime: Optional[float] = None


class TextCache:
    """Simple file-backed text cache with mtime invalidation."""

    def __init__(self, base_path: Path | str = ".") -> None:
        self.base_path = Path(base_path)
        self._entries: Dict[str, _CacheEntry] = {}

    def register(self, key: str, relative_path: Path | str) -> None:
        self._entries[key] = _CacheEntry(path=self.base_path / relative_path)

    def get_lines(self, key: str) -> Optional[List[str]]:
        entry = self._entries.get(key)
        if not entry:
            return None

        file_path = entry.path
        if not file_path.exists():
            entry.lines = None
            entry.mtime = None
            return None

        try:
            mtime = os.path.getmtime(file_path)
            if entry.lines is None or entry.mtime != mtime:
                with file_path.open("r", encoding="utf-8") as handle:
                    entry.lines = [line.strip() for line in handle if line.strip()]
                entry.mtime = mtime
                logger.info("Loaded %s cache with %d entries", key, len(entry.lines))
        except Exception as error:  # pragma: no cover - logging branch
            logger.error("Error loading %s cache: %s", key, error)
            entry.lines = None
            entry.mtime = None
            return None

        return entry.lines


__all__ = ["TextCache"]
