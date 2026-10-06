"""Local requests factory against a live InvenioRDM."""

from types import SimpleNamespace

import pytest

from inveniordm_auth.remote_servers import RemoteServerRegistry
from inveniordm_auth.token_store import FileTokenStore
from inveniordm_jupyterlab.inveniordm_requests.inveniordm_requests_factory_create import (
    create_inveniordm_requests_factory,
)

pytestmark = pytest.mark.integration


def test_local_factory_builds_and_validates_client(
    base_url, tokens, tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "INVENIORDM_JUPYTERLAB_TOKEN_STORE", str(tmp_path / "tokens.json")
    )
    FileTokenStore().set_token("local", tokens["a@b.com"], True, "local")

    registry = RemoteServerRegistry(
        {"local": {"label": "Local", "base_url": base_url}}, "local"
    )
    factory = create_inveniordm_requests_factory(registry, factory_type="local")

    # no ?remote_server override -> the default server
    handler = SimpleNamespace(get_query_argument=lambda *args, **kwargs: None)
    status = factory.get_access_token_status(handler)

    assert status.access_token_present is True
    assert status.access_token_valid is True  # validated against the live /api/me
    assert status.remote_server_id == "local"
