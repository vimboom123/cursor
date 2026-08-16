from datetime import datetime, timedelta, timezone

import pytest

from awcollector.models import Permit
from awcollector.permit import PermitError, assert_permit_active, assert_task_allowed, assert_url_allowed


def make_permit(**overrides) -> Permit:
    data = {
        "permit_id": "P-1",
        "operator": "tester",
        "organization": "demo",
        "purpose": "unit test",
        "allowed_url_prefixes": ["http://127.0.0.1", "file://"],
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        "read_only": True,
    }
    data.update(overrides)
    return Permit.model_validate(data)


def test_active_permit_allows_prefixed_url() -> None:
    permit = make_permit()
    assert_permit_active(permit)
    assert_url_allowed(permit, "http://127.0.0.1:8080/list")
    assert_url_allowed(permit, "file:///tmp/demo.html")


def test_expired_permit_is_rejected() -> None:
    permit = make_permit(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    with pytest.raises(PermitError, match="过期"):
        assert_permit_active(permit)


def test_out_of_scope_url_is_rejected() -> None:
    permit = make_permit()
    with pytest.raises(PermitError, match="不在许可范围"):
        assert_url_allowed(permit, "https://example.com/secret")


def test_wildcard_permit_is_rejected() -> None:
    with pytest.raises(ValueError, match="通配"):
        make_permit(allowed_url_prefixes=["*"])


def test_readonly_permit_blocks_write_task() -> None:
    permit = make_permit(read_only=True)
    with pytest.raises(PermitError, match="只读"):
        assert_task_allowed(permit, allow_write=True)
