from __future__ import annotations

import hmac
from dataclasses import dataclass

ROLES = ("viewer", "engineer", "approver", "admin")


@dataclass(frozen=True)
class Principal:
    user: str
    role: str


class KeyStore:
    def __init__(self, entries: list[tuple[str, str, str]]) -> None:
        for _, _, role in entries:
            if role not in ROLES:
                raise ValueError(f"unknown role {role!r}")
        self._entries = entries

    def authenticate(self, presented: str | None) -> Principal | None:
        """Constant-time compare against every key (no early exit)."""
        if not presented:
            return None
        found: Principal | None = None
        for key, user, role in self._entries:
            if hmac.compare_digest(key.encode(), presented.encode()):
                found = Principal(user, role)
        return found
