#!/usr/bin/env bash
# Runs the whole TechMart data platform end to end, in roadmap order.
# Safe to re-run from scratch at any time.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Shared master data =="
python3 data/generate_master_data.py
python3 data/generate_raw_export.py

echo
echo "== Step 1: Fundamentals =="
python3 step1_fundamentals/explore_and_convert.py

echo
echo "== Step 2: SQL =="
python3 step2_sql_modeling/seed_data.py
python3 step2_sql_modeling/run_analysis.py

echo
echo "== Step 3: Python pipeline (starting mock API) =="
python3 step3_python_pipeline/mock_api/app.py > /tmp/techmart_mock_api.log 2>&1 &
API_PID=$!
sleep 2
( cd step3_python_pipeline && python3 pipeline.py )
kill "$API_PID" 2>/dev/null || true

echo
echo "== Step 4: Incremental ETL =="
python3 step4_incremental_etl/incremental_pipeline.py --reset
python3 step4_incremental_etl/simulate_new_orders.py --n 25
python3 step4_incremental_etl/incremental_pipeline.py

echo
echo "== Step 5: Data warehouse =="
python3 step5_data_warehouse/build_warehouse.py

echo
echo "== Step 6: Spark clickstream (requires a JVM) =="
python3 step6_spark_clickstream/generate_clickstream.py --sessions 40000
python3 step6_spark_clickstream/spark_pipeline.py
python3 step6_spark_clickstream/pandas_comparison.py

echo
echo "All steps completed."
