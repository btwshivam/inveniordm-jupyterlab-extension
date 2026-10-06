"""Create / upload / list / delete round-trips against a live InvenioRDM."""

import pytest

from inveniordm_jupyterlab.inveniordm_file_identifier import (
    InvenioRDMFileIdentifier,
)
from inveniordm_jupyterlab.inveniordm_record_identifier import (
    InvenioRDMRecordIdentifier,
)
from inveniordm_jupyterlab.util.job_types import JobCancelled

from .conftest import wait_until

pytestmark = pytest.mark.integration


def test_create_draft_with_files_uploads_and_deletes(make_requests, tmp_path):
    reqs = make_requests("a@b.com")
    data = tmp_path / "data.txt"
    data.write_bytes(b"hello vre")

    draft = reqs.create_inveniordm_record_draft_with_files(file_paths=[data])
    record_id = draft["id"]
    try:
        variant = reqs.get_inveniordm_record_variant(
            InvenioRDMRecordIdentifier(record_id=record_id, record_status="draft")
        )
        assert "data.txt" in variant.get("files", {}).get("entries", {})
    finally:
        reqs.delete_inveniordm_record_draft(record_id)


def test_user_records_listing_hydrates_draft_files(make_requests, tmp_path):
    # /api/user/records omits draft file entries; include_files=True re-fetches them.
    reqs = make_requests("a@b.com")
    data = tmp_path / "data.txt"
    data.write_bytes(b"hello vre")

    draft = reqs.create_inveniordm_record_draft_with_files(file_paths=[data])
    record_id = draft["id"]
    try:
        def find():
            hits = reqs.list_inveniordm_user_records(include_files=True)
            hits = hits.get("hits", {}).get("hits", [])
            return next((h for h in hits if h["id"] == record_id), None)

        record = wait_until(find)
        assert record is not None, "draft never appeared in /api/user/records"
        assert "data.txt" in record.get("files", {}).get("entries", {})
    finally:
        reqs.delete_inveniordm_record_draft(record_id)


def test_upload_files_to_existing_draft_reports_progress(make_requests, tmp_path):
    reqs = make_requests("a@b.com")
    initial = tmp_path / "initial.txt"
    initial.write_bytes(b"initial")

    draft = reqs.create_inveniordm_record_draft_with_files(file_paths=[initial])
    record_id = draft["id"]
    try:
        extra = tmp_path / "extra.txt"
        extra.write_bytes(b"added later")
        progress = []
        reqs.upload_inveniordm_record_files(
            record_id=record_id,
            file_paths=[extra],
            on_upload_progress=lambda done, total, name: progress.append(
                (done, total, name)
            ),
        )

        variant = reqs.get_inveniordm_record_variant(
            InvenioRDMRecordIdentifier(record_id=record_id, record_status="draft")
        )
        entries = variant.get("files", {}).get("entries", {})
        assert "initial.txt" in entries
        assert "extra.txt" in entries
        assert progress and progress[-1][0] == progress[-1][1]
    finally:
        reqs.delete_inveniordm_record_draft(record_id)


def test_upload_cancellation_removes_the_partial_file(make_requests, tmp_path):
    # a canceled upload must remove the empty entry created before streaming
    reqs = make_requests("a@b.com")
    seed = tmp_path / "seed.txt"
    seed.write_bytes(b"seed")

    draft = reqs.create_inveniordm_record_draft_with_files(file_paths=[seed])
    record_id = draft["id"]
    try:
        target = tmp_path / "canceled.txt"
        target.write_bytes(b"x" * 100_000)
        calls = {"n": 0}

        def should_cancel():
            calls["n"] += 1
            return calls["n"] > 1  # pass the pre-check, cancel during streaming

        with pytest.raises(JobCancelled):
            reqs.upload_inveniordm_record_files(
                record_id=record_id,
                file_paths=[target],
                should_cancel=should_cancel,
            )

        variant = reqs.get_inveniordm_record_variant(
            InvenioRDMRecordIdentifier(record_id=record_id, record_status="draft")
        )
        entries = variant.get("files", {}).get("entries", {})
        assert "canceled.txt" not in entries
        assert "seed.txt" in entries
    finally:
        reqs.delete_inveniordm_record_draft(record_id)


def test_download_published_file(make_requests, published_record):
    reqs = make_requests("a@b.com")
    file_id = InvenioRDMFileIdentifier(
        record_id=published_record, record_status="published", file_key="readme.txt"
    )
    response = reqs.open_inveniordm_file(file_id=file_id)
    try:
        content = b"".join(response.iter_bytes(4096))
    finally:
        response.close()
    assert content == b"integration test file"


def test_delete_draft_file(make_requests, tmp_path):
    reqs = make_requests("a@b.com")
    keep = tmp_path / "keep.txt"
    keep.write_bytes(b"keep")
    gone = tmp_path / "gone.txt"
    gone.write_bytes(b"gone")

    draft = reqs.create_inveniordm_record_draft_with_files(file_paths=[keep, gone])
    record_id = draft["id"]
    try:
        reqs.delete_inveniordm_record_file(
            file_id=InvenioRDMFileIdentifier(
                record_id=record_id, record_status="draft", file_key="gone.txt"
            )
        )
        variant = reqs.get_inveniordm_record_variant(
            InvenioRDMRecordIdentifier(record_id=record_id, record_status="draft")
        )
        entries = variant.get("files", {}).get("entries", {})
        assert "gone.txt" not in entries
        assert "keep.txt" in entries
    finally:
        reqs.delete_inveniordm_record_draft(record_id)
