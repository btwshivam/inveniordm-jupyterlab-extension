#!/usr/bin/env bash
# Boot a local InvenioRDM (official invenio-cli + cookiecutter, pinned to v12 --
# what Zenodo/CDS run), create the mock users, mint tokens, write .tokens.json.
#
#   bash integration-tests/start-instance.sh
#   INVENIORDM_INTEGRATION_TOKENS=integration-tests/.tokens.json pytest -m integration -vv
#
# Needs Docker and Python. Re-run to rebuild.
set -euo pipefail

RDM_VERSION="${RDM_VERSION:-v12.0}"      # cookiecutter tag (matches the extension's target)
PROJECT="${PROJECT:-jlab-integration}"
here="$(cd "$(dirname "$0")" && pwd)"
work="${INSTANCE_DIR:-$here/.instance}"
tokens_file="${INVENIORDM_INTEGRATION_TOKENS:-$here/.tokens.json}"
compose_file="docker-compose.full.yml"
users=("a@b.com" "bertha.beispiel@example.com" "john.smith@example.com")

python -m pip install -q invenio-cli

# 1. Scaffold once, non-interactively, at the pinned version.
if [ ! -f "$work/$PROJECT/.invenio" ]; then
    mkdir -p "$work"
    cat > "$work/config.invenio" <<EOF
[cookiecutter]
project_name = $PROJECT
project_shortname = $PROJECT
package_name = ${PROJECT//-/_}
project_site = $PROJECT.example
author_name = CERN
author_email = info@example.org
year = 2024
file_storage = local
development_tools = no
site_code = no
use_reduced_vocabs = yes
database = postgresql
search = opensearch2
EOF
    (cd "$work" && invenio-cli init rdm --checkout "$RDM_VERSION" --no-input --config config.invenio)
fi
cd "$work/$PROJECT"

# The scaffold's cert is CN-only; urllib3>=2 needs a SAN. Regenerate it so the
# extension can verify https://localhost (the frontend redirects http->https).
cert="docker/nginx/test.crt"
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -keyout docker/nginx/test.key -out "$cert" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1" 2>/dev/null

# The v12 compose binds the internal :5000 ports as "IP:5000" (missing the
# second colon), which newer docker compose rejects as an invalid hostPort.
# These ports are internal (nginx proxies to them), so drop the host binding.
sed -i 's|"${DOCKER_SERVICES_IP_BIND:-127.0.0.1}:5000"|"5000"|g' docker-compose.full.yml

# The Dockerfile does `COPY site ./site`, but site_code=no generates no site/
# dir (it is copied, never installed). Provide an empty one so the build works.
mkdir -p site && touch site/.gitkeep

# A fresh lock pulls the `libpass` fork of passlib, which dropped str_to_uascii
# that invenio-accounts v12 imports. libpass is pinned by name, so reinstall
# real passlib last to win the shared `passlib` namespace.
grep -q '^passlib ' Pipfile || sed -i '/^\[packages\]/a passlib = "==1.7.4"' Pipfile
grep -q 'force-reinstall --no-deps "passlib' Dockerfile || \
    sed -i '/RUN pipenv install --deploy --system/a RUN pip install --force-reinstall --no-deps "passlib==1.7.4"' Dockerfile

# 2. The v12 Pipfile pins Python 3.9; generate the lock in a 3.9 container so it
#    works whatever the host Python is, then build/setup without re-locking.
if [ ! -f Pipfile.lock ]; then
    docker run --rm -e PIP_DEFAULT_TIMEOUT=120 -e PIP_RETRIES=10 \
        -v "$PWD":/app -w /app python:3.9 \
        sh -c 'pip install -q pipenv && pipenv lock'
fi
invenio-cli containers start --skip-lock --build --setup --no-demo-data

svc() { docker compose -f "$compose_file" exec -T web-api "$@"; }

# 3. Mock users (all confirmed/active, password test123).
for email in "${users[@]}"; do
    svc invenio users create "$email" --password test123 --active --confirm || true
done

# 4. One access token per user.
echo "{" > "$tokens_file.tmp"
first=1
for email in "${users[@]}"; do
    token="$(svc invenio tokens create -n jlab-integration -u "$email" | tr -d '\r' | tail -n 1)"
    [ -n "$token" ] || { echo "failed to mint a token for $email"; exit 1; }
    [ $first -eq 1 ] || echo "," >> "$tokens_file.tmp"
    first=0
    printf '  "%s": "%s"' "$email" "$token" >> "$tokens_file.tmp"
done
printf '\n}\n' >> "$tokens_file.tmp"
mv "$tokens_file.tmp" "$tokens_file"

echo "Done. Run the tests with:"
echo "  pytest -m integration -vv"
echo "Stop with: docker compose -f $work/$PROJECT/$compose_file down -v"
