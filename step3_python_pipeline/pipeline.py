"""
Step 3 - pipeline.py
-----------------------
Orchestrates extract -> transform -> load as one runnable pipeline,
logging every step (and any failure) to both the console and
pipeline.log. This is the "Python project" deliverable from the
roadmap: automate data movement and transformation using Python.

Prerequisite: the mock API must be running:
    python3 step3_python_pipeline/mock_api/app.py &

Usage:
    python3 step3_python_pipeline/pipeline.py
"""
import logging
import sys
import time
from pathlib import Path

import extract
import load
import transform

LOG_PATH = Path(__file__).resolve().parent / "pipeline.log"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH)],
    )


def main():
    setup_logging()
    logger = logging.getLogger("pipeline")
    started = time.time()
    logger.info("=== Pipeline run started ===")

    try:
        logger.info("Step 1/3: extract")
        raw_records = extract.extract_all()

        logger.info("Step 2/3: transform")
        valid_ids = transform.load_valid_product_ids()
        df_clean = transform.transform(raw_records, valid_ids)
        out_path = transform.OUT_DIR / "marketplace_orders_clean.parquet"
        df_clean.to_parquet(out_path, engine="pyarrow", index=False)

        logger.info("Step 3/3: load")
        load.main()

        elapsed = time.time() - started
        logger.info(f"=== Pipeline run succeeded in {elapsed:.1f}s "
                    f"({len(raw_records)} extracted, {len(df_clean)} loaded) ===")
    except Exception:
        logger.exception("=== Pipeline run FAILED ===")
        raise


if __name__ == "__main__":
    main()
