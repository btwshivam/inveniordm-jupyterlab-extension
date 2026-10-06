"""Version listing and new-version-draft merging against a live InvenioRDM."""

import pytest

from .conftest import wait_until

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "include_drafts, draft_visible",
    [
        (False, False),  # published-only view
        (True, True),    # draft merged in
    ],
)
def test_version_listing(
    make_requests, published_record, include_drafts, draft_visible
):
    reqs = make_requests("a@b.com")
    draft_id = str(reqs.create_inveniordm_record_version(published_record)["id"])
    try:
        def listed():
            ids = {
                str(v["id"])
                for v in reqs.list_inveniordm_record_versions(
                    published_record, include_drafts=include_drafts
                )
            }
            return ids if (draft_id in ids) == draft_visible else None

        # only the merge (draft_visible) has to wait for indexing
        ids = wait_until(listed) if draft_visible else listed()
        assert ids, "version list never reached the expected state"
        assert str(published_record) in ids
    finally:
        reqs.delete_inveniordm_record_draft(draft_id)
