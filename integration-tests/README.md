# Backend integration tests

These run the extension's Python backend (`InvenioRDMRequests`) against a
**real, local InvenioRDM** instead of mocked HTTP, to check the extension
*interacts with InvenioRDM correctly*: permission resolution, version/draft
merging, the draft-file workaround, and record create/upload/delete round-trips.
They live in `inveniordm_jupyterlab/tests/integration/` and are marked
`@pytest.mark.integration`.

Because they need a running server, they **skip** unless one is reachable, so a
normal offline `pytest` run is unaffected.

## Running them

You need Docker and Python. Three steps: set up the environment, boot an
InvenioRDM, then run the tests.

**1. Install the test dependencies**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
```

**2. Boot a local InvenioRDM.** Do this first, or the tests skip.

```bash
bash integration-tests/start-instance.sh
```

This scaffolds a fresh instance with the official `invenio-cli`, builds and
starts it, and mints an access token per mock user. It takes a few minutes the
first time. Three users are created (all password `test123`): `a@b.com` (the
record owner), `bertha.beispiel@example.com`, and `john.smith@example.com`;
their tokens are written to `.tokens.json`.

**3. Run the tests**

```bash
pytest -m integration -vv
```

No env vars needed. The tokens file and the instance's self-signed cert are
found automatically under `integration-tests/`. To point at an instance
elsewhere, set `INVENIORDM_BASE_URL`, `INVENIORDM_INTEGRATION_TOKENS`, and
`REQUESTS_CA_BUNDLE`.

When you're done, tear the instance down:

```bash
docker compose -f integration-tests/.instance/jlab-integration/docker-compose.full.yml down -v
```

## Why v12

The instance is pinned (`RDM_VERSION`, default `v12.0`) to the InvenioRDM
release the extension's REST calls were written against. Newer InvenioRDM (v15+)
changed the file-transfer API, so testing against it would exercise a different
contract than the extension actually uses.

## CI

`.github/workflows/integration-inveniordm.yml` runs these when a PR changes the
integration tests (or on manual dispatch), kept separate from the fast unit
build, since booting InvenioRDM is heavy.
