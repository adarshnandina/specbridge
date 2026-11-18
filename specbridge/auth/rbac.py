"""Permission matrix (Section 7.9)."""

from __future__ import annotations

PERMISSIONS: dict[str, frozenset[str]] = {
    "query": frozenset({"viewer", "engineer", "approver", "admin"}),
    "read": frozenset({"viewer", "engineer", "approver", "admin"}),
    "write": frozenset({"engineer", "approver", "admin"}),  # upload, extract, review, start runs
    "approve": frozenset({"approver", "admin"}),  # approve extraction/push/change requests
    "admin": frozenset({"admin"}),  # ingest folders, read audit log
}


def has_permission(role: str, permission: str) -> bool:
    if permission not in PERMISSIONS:
        raise KeyError(f"unknown permission {permission!r}")
    return role in PERMISSIONS[permission]
