import pytest

from specbridge.auth.api_keys import KeyStore
from specbridge.auth.rbac import PERMISSIONS, has_permission


def test_keystore():
    ks = KeyStore([("k1", "alice", "viewer"), ("k2", "bob", "admin")])
    assert ks.authenticate("k2").user == "bob"
    assert ks.authenticate("nope") is None and ks.authenticate(None) is None
    with pytest.raises(ValueError):
        KeyStore([("k", "u", "root")])


@pytest.mark.parametrize(
    "perm,allowed",
    [
        ("query", {"viewer", "engineer", "approver", "admin"}),
        ("read", {"viewer", "engineer", "approver", "admin"}),
        ("write", {"engineer", "approver", "admin"}),
        ("approve", {"approver", "admin"}),
        ("admin", {"admin"}),
    ],
)
def test_matrix(perm, allowed):
    for role in ("viewer", "engineer", "approver", "admin"):
        assert has_permission(role, perm) == (role in allowed)


def test_unknown_permission():
    assert "write" in PERMISSIONS
    with pytest.raises(KeyError):
        has_permission("admin", "root")
