from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

from jrock.security import PermissionDenied, Permissions


class TextExtensions:
    """Skills and soul are data, never imported Python or executable code."""

    def __init__(self, data_dir: Path, permissions: Permissions):
        self.data_dir, self.permissions = data_dir, permissions
        for kind in ("souls", "skills"):
            (data_dir / kind).mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def name(name: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", name):
            raise ValueError("Use a short name with letters, numbers, dots, hyphens or underscores")
        return name

    def names(self, kind: str) -> list[str]:
        self._kind(kind)
        builtins = files("jrock").joinpath("resources", kind).iterdir()
        return sorted({p.name.removesuffix(".md") for p in builtins if p.name.endswith(".md")} |
                      {p.stem for p in (self.data_dir / kind).glob("*.md")})

    @staticmethod
    def _kind(kind: str) -> None:
        if kind not in {"souls", "skills"}:
            raise ValueError("Unknown extension kind")

    def read(self, kind: str, name: str) -> str:
        self._kind(kind)
        name = self.name(name)
        p = self.data_dir / kind / f"{name}.md"
        if p.exists():
            return p.read_text()
        p = files("jrock").joinpath("resources", kind, f"{name}.md")
        if not p.is_file():
            raise ValueError("Extension does not exist")
        return p.read_text()

    def import_from_workspace(self, owner: int, kind: str, name: str, path: str) -> str:
        self.permissions.authorize(owner)
        self._kind(kind)
        name = self.name(name)
        source = self.permissions.safe_path(path)
        if not source.is_file() or source.stat().st_size > 64_000:
            raise ValueError("Extension must be a text file under 64 KB in the workspace")
        text = source.read_text()
        if "\x00" in text:
            raise PermissionDenied("Binary content is not a skill/persona")
        p = self.data_dir / kind / f"{name}.md"
        p.write_text(text)
        p.chmod(0o600)
        return name
