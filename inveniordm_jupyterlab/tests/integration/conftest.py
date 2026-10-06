"""Fixtures for the integration tests (see integration-tests/README.md).

Skipped unless a live InvenioRDM is reachable and tokens are provided, so the
offline suite is unaffected.
"""

import json
import os
import time
from pathlib import Path

import pytest
import requests

from inveniordm_jupyterlab.inveniordm_requests.inveniordm import (
    upload_inveniordm_draft_file,
)
from inveniordm_jupyterlab.inveniordm_requests.inveniordm_requests import (
    InvenioRDMRequests,
)

DEFAULT_BASE_URL = "https://localhost"

# Where start-instance.sh writes the tokens and the instance's TLS cert.
_INSTANCE_DIR = Path(__file__).resolve().parents[3] / "integration-tests"
_DEFAULT_TOKENS = _INSTANCE_DIR / ".tokens.json"
_DEFAULT_CA_BUNDLE = (
    _INSTANCE_DIR / ".instance/jlab-integration/docker/nginx/test.crt"
)

# Point requests at the instance's self-signed cert by default, so a plain
# `pytest -m integration` verifies TLS without exporting REQUESTS_CA_BUNDLE.
if "REQUESTS_CA_BUNDLE" not in os.environ and _DEFAULT_CA_BUNDLE.exists():
    os.environ["REQUESTS_CA_BUNDLE"] = str(_DEFAULT_CA_BUNDLE)


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("INVENIORDM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


@pytest.fixture(scope="session")
def require_instance(base_url):
    try:
        requests.get(f"{base_url}/api/records", timeout=5).raise_for_status()
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"No InvenioRDM reachable at {base_url}: {error}")


@pytest.fixture(scope="session")
def tokens(require_instance):
    # {email: access_token}, written by integration-tests/start-instance.sh.
    path = os.environ.get("INVENIORDM_INTEGRATION_TOKENS")
    if not path and _DEFAULT_TOKENS.exists():
        path = str(_DEFAULT_TOKENS)
    if not path or not os.path.exists(path):
        pytest.skip(
            "No tokens file. Run integration-tests/start-instance.sh, or set "
            "INVENIORDM_INTEGRATION_TOKENS."
        )
    with open(path) as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def make_requests(base_url, tokens):
    cache: dict[str, InvenioRDMRequests] = {}

    def _make(email: str) -> InvenioRDMRequests:
        if email not in cache:
            if email not in tokens:
                pytest.skip(f"No token for {email}")
            headers = {"Authorization": f"Bearer {tokens[email]}"}
            # get_inveniordm_record_permission needs the caller's numeric id.
            me = requests.get(f"{base_url}/api/me", headers=headers, timeout=10)
            me.raise_for_status()
            cache[email] = InvenioRDMRequests(
                url=base_url,
                headers=headers,
                inveniordm_user_id=str(me.json()["id"]),
            )
        return cache[email]

    return _make


def _invenio_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.inveniordm.v1+json",
    }


def create_published_record(base_url: str, token: str, title: str) -> str:
    # The extension never publishes; arrange a published record via the raw API
    # so the version and permission tests have something to act on.
    headers = _invenio_headers(token)
    draft = requests.post(
        f"{base_url}/api/records",
        headers=headers,
        json={
            "access": {"record": "public", "files": "public"},
            "files": {"enabled": True},
            "metadata": {
                "title": title,
                "publication_date": "2024-01-01",
                "resource_type": {"id": "dataset"},
                "creators": [
                    {
                        "person_or_org": {
                            "type": "personal",
                            "family_name": "Mustermann",
                            "given_name": "Max",
                        }
                    }
                ],
            },
        },
        timeout=30,
    )
    draft.raise_for_status()
    record_id = draft.json()["id"]
    # A files-enabled record cannot be published empty.
    upload_inveniordm_draft_file(
        record_id,
        base_url=base_url,
        headers={"Authorization": f"Bearer {token}"},
        filename="readme.txt",
        content=b"integration test file",
    )
    published = requests.post(
        f"{base_url}/api/records/{record_id}/draft/actions/publish",
        headers=headers,
        timeout=30,
    )
    published.raise_for_status()
    return record_id


@pytest.fixture(scope="session")
def published_record(base_url, tokens):
    if "a@b.com" not in tokens:
        pytest.skip("No token for the record owner a@b.com")
    return create_published_record(
        base_url, tokens["a@b.com"], "Integration test record"
    )


def wait_until(predicate, timeout=30.0, interval=1.0):
    # InvenioRDM indexes asynchronously; poll until the change is visible.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    return predicate()
