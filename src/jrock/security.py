from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path


class PermissionDenied(RuntimeError):
    pass


@dataclass
class Approval:
    id: str
    owner: int
    action: str
    digest: str
    payload: dict
    expires: float
    description: str
    state: str = "pending"


class Permissions:
    """One-shot, expiring, owner-bound capabilities. A prompt can never approve itself."""

    def __init__(self, allowed_users: list[int], workspace: Path, host_terminal: bool = False):
        self.allowed_users = set(allowed_users)
        self.workspace = workspace.resolve()
        self.host_terminal = host_terminal
        self.pending: dict[str, Approval] = {}
        self.edit_auto: set[int] = set()

    def authorize(self, owner: int, private_chat: bool = True) -> None:
        if owner not in self.allowed_users or not private_chat:
            raise PermissionDenied("Only allowlisted users in private chats can control this agent")

    @staticmethod
    def digest(action: str, payload: dict) -> str:
        return hashlib.sha256(json.dumps([action, payload], sort_keys=True).encode()).hexdigest()

    def request(self, owner: int, action: str, payload: dict, description: str) -> Approval:
        self.authorize(owner)
        aid = secrets.token_hex(8)
        approval = Approval(aid, owner, action, self.digest(action, payload), payload,
                            time.time() + 300, description)
        self.pending[aid] = approval
        self.pending = {k: v for k, v in self.pending.items() if v.expires > time.time()}
        return approval

    def approve(self, owner: int, aid: str) -> Approval:
        self.authorize(owner)
        a = self.pending.get(aid)
        if not a or a.owner != owner or a.expires < time.time() or a.state != "pending":
            raise PermissionDenied("Invalid, expired, already-used, or foreign approval")
        a.state = "approved"
        return a

    def consume(self, owner: int, aid: str, action: str, payload: dict) -> None:
        self.authorize(owner)
        a = self.pending.get(aid)
        if not a or a.owner != owner or a.expires < time.time() or a.state != "approved":
            raise PermissionDenied("An explicit, unexpired approval is required")
        if a.digest != self.digest(action, payload):
            raise PermissionDenied("The action changed after approval")
        del self.pending[aid]

    def deny(self, owner: int, aid: str) -> None:
        self.authorize(owner)
        a = self.pending.get(aid)
        if not a or a.owner != owner:
            raise PermissionDenied("Approval not found")
        del self.pending[aid]

    def revoke(self, owner: int) -> None:
        self.pending = {key: a for key, a in self.pending.items() if a.owner != owner}

    def safe_path(self, relative: str, allow_sensitive: bool = False) -> Path:
        p = (self.workspace / relative).resolve()
        if not p.is_relative_to(self.workspace):
            raise PermissionDenied("Path escapes the configured workspace (including symlinks)")
        if not allow_sensitive and any(
            part.startswith(".env") or part in {".git", ".ssh", ".aws", ".netrc", "credentials"}
            for part in p.relative_to(self.workspace).parts
        ):
            raise PermissionDenied("Credential and Git internals are not agent-readable/editable")
        return p
