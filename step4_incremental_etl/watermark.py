"""
Step 4 - watermark.py
------------------------
Tiny helper around a watermark file. The watermark is the timestamp of
the last successfully-loaded record. Every incremental run:
  1. reads the current watermark
  2. pulls only source rows newer than it
  3. ONLY advances the watermark after a successful load

That last point is what makes the pipeline safely resumable: if a run
crashes mid-load, the watermark hasn't moved, so the next run re-pulls
the same batch instead of silently skipping it.
"""
import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "state" / "watermark.json"
STATE_PATH.parent.mkdir(exist_ok=True)

DEFAULT_WATERMARK = "1970-01-01T00:00:00"


def get_watermark() -> str:
    if not STATE_PATH.exists():
        return DEFAULT_WATERMARK
    return json.loads(STATE_PATH.read_text())["watermark"]


def set_watermark(value: str) -> None:
    STATE_PATH.write_text(json.dumps({"watermark": value}, indent=2))


def reset_watermark() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()
