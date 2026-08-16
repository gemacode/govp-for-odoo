#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -p govp_odoo_native -f "$TEST_DIR/docker-compose.yml")

cleanup() {
  "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

"${COMPOSE[@]}" up -d --wait db

"${COMPOSE[@]}" run --rm odoo odoo \
  --database govp_native \
  --init govp_for_odoo \
  --without-demo all \
  --stop-after-init \
  --db_host db \
  --db_user odoo \
  --db_password odoo \
  --log-level warn

"${COMPOSE[@]}" run --rm odoo odoo \
  --database govp_native \
  --update govp_for_odoo \
  --test-enable \
  --test-tags /govp_for_odoo \
  --without-demo all \
  --stop-after-init \
  --db_host db \
  --db_user odoo \
  --db_password odoo \
  --log-level test

installed="$("${COMPOSE[@]}" exec -T db psql -U odoo -d govp_native -Atc "SELECT state FROM ir_module_module WHERE name='govp_for_odoo'")"
test "$installed" = "installed"

"${COMPOSE[@]}" run --rm odoo odoo \
  --database govp_native \
  --update govp_for_odoo \
  --without-demo all \
  --stop-after-init \
  --db_host db \
  --db_user odoo \
  --db_password odoo \
  --log-level warn

"${COMPOSE[@]}" run --rm -T odoo odoo shell \
  --database govp_native \
  --no-http \
  --db_host db \
  --db_user odoo \
  --db_password odoo \
  < "$TEST_DIR/uninstall.py"

uninstalled="$("${COMPOSE[@]}" exec -T db psql -U odoo -d govp_native -Atc "SELECT state FROM ir_module_module WHERE name='govp_for_odoo'")"
test "$uninstalled" = "uninstalled"

echo "GOVP for Odoo native install, update and uninstall passed."
