"""Record permission resolution against a live InvenioRDM.

InvenioRDM doesn't return the caller's effective permission, so the extension
derives it from parent.access.grants and a grant-token search.
"""

import pytest

pytestmark = pytest.mark.integration


# "edit" (a user holding an edit grant) is not asserted: on v12 the grant-token
# search does not surface records shared with the grantee, so it resolves to
# "preview".
@pytest.mark.parametrize(
    "user, expected",
    [
        ("a@b.com", "manage"),                  # record owner
        ("john.smith@example.com", "preview"),  # unrelated user
    ],
)
def test_record_permission(make_requests, published_record, user, expected):
    reqs = make_requests(user)
    assert (
        reqs.get_inveniordm_record_permission(published_record, "published")
        == expected
    )
