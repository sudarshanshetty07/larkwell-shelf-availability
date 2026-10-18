#!/usr/bin/env bash
# One-time Lakebase setup for Larkwell Shelf Availability. Bundles don't manage Lakebase objects yet, so this script does.
# Run from the repo root after the first pipeline update has built the gold table:
#   DATABRICKS_CONFIG_PROFILE=<your-profile> bash lakebase/setup.sh
# It is safe to re-run: each step checks whether its object already exists.
set -euo pipefail
PROFILE=${DATABRICKS_CONFIG_PROFILE:-DEFAULT}
CATALOG=$(python3 -c "import json; print(json.load(open('conf/settings.json'))['catalog'])")
PROJECT=$(python3 -c "import json; print(json.load(open('conf/settings.json'))['lakebase_project'])")
BRANCH=projects/$PROJECT/branches/production
ENDPOINT=$BRANCH/endpoints/primary
DATABASE=$BRANCH/databases/databricks-postgres
SYNCED=${CATALOG}_pg.serving.product_location_status

echo "1/6 Lakebase project (Postgres 17, autoscaling compute)"
databricks postgres get-project projects/$PROJECT --profile "$PROFILE" >/dev/null 2>&1 \
  || databricks postgres create-project "$PROJECT" --profile "$PROFILE" \
       --json '{"spec": {"display_name": "Larkwell shelf availability (synthetic demo)"}}'
databricks postgres update-endpoint "$ENDPOINT" "spec.autoscaling_limit_min_cu,spec.autoscaling_limit_max_cu" --profile "$PROFILE" \
  --json '{"spec": {"autoscaling_limit_min_cu": 1, "autoscaling_limit_max_cu": 8}}' >/dev/null

echo "2/6 Register the Postgres database in Unity Catalog as ${CATALOG}_pg"
databricks catalogs get "${CATALOG}_pg" --profile "$PROFILE" >/dev/null 2>&1 \
  || databricks postgres create-catalog "${CATALOG}_pg" --profile "$PROFILE" \
       --json "{\"spec\": {\"postgres_database\": \"databricks_postgres\", \"branch\": \"$BRANCH\"}}"

echo "3/6 Sync gold.product_location_status into Postgres for Shelf Scan (snapshot; the daily job refreshes it)"
databricks postgres get-synced-table "synced_tables/$SYNCED" --profile "$PROFILE" >/dev/null 2>&1 \
  || databricks postgres create-synced-table "$SYNCED" --profile "$PROFILE" --json "{
       \"spec\": {
         \"source_table_full_name\": \"$CATALOG.gold.product_location_status\",
         \"primary_key_columns\": [\"store\", \"upc\"],
         \"scheduling_policy\": \"SNAPSHOT\",
         \"branch\": \"$BRANCH\",
         \"postgres_database\": \"databricks_postgres\",
         \"create_database_objects_if_missing\": true,
         \"new_pipeline_spec\": {\"storage_catalog\": \"$CATALOG\", \"storage_schema\": \"ops\"}}}"

echo "4/6 The app's operational tables (ops schema)"
databricks psql --project "$PROJECT" --profile "$PROFILE" -- -d databricks_postgres -v ON_ERROR_STOP=1 -q -f lakebase/ops_schema.sql

echo "5/6 Lakehouse Sync: stream every change in the ops schema back into $CATALOG.ops"
databricks postgres list-cdf-configs "$DATABASE" --profile "$PROFILE" >/dev/null 2>&1 \
  || databricks postgres create-cdf-config "$DATABASE" "$CATALOG" ops ops --cdf-config-id ops_to_lakehouse --profile "$PROFILE"

echo "6/6 Done. Put this sync pipeline id in databricks.yml (lakebase_sync_pipeline_id):"
databricks postgres get-synced-table "synced_tables/$SYNCED" --profile "$PROFILE" -o json \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['status']['pipeline_id'])"
echo "After the app exists, grant its service principal access: lakebase/grants.sql and governance/grants.sql"
