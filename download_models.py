#!/usr/bin/env python3
"""
Model downloader for Face Attendance project (root-level)

Downloads lightweight YOLO weights (yolov8n.pt) and prepares InsightFace (antelopev2)
into the local 'models' directory. Skips downloads if files already exist. Designed
to work on Windows and POSIX systems.
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from typing import Optional

try:
    import urllib.request as urlreq
except Exception:  # pragma: no cover
    urlreq = None  # type: ignore


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


ROOT_DIR = Path(__file__).resolve().parent
MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


YOLO_TARGET = MODELS_DIR / "yolov8n.pt"
YOLO_URLS = [
    # Primary Ultralytics assets URL
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
    # Mirror (fallback) - if you have an internal mirror, add it here
]


def download_with_retries(url: str, dest: Path, retries: int = 3, backoff_sec: float = 2.0) -> bool:
    """Download a file with simple retry/backoff. Returns True on success."""
    if urlreq is None:
        logger.error("urllib.request not available; cannot download %s", url)
        return False
    for attempt in range(1, retries + 1):
        try:
            logger.info("Downloading %s -> %s (attempt %d/%d)", url, dest, attempt, retries)
            tmp_path = dest.with_suffix(dest.suffix + ".part")
            with urlreq.urlopen(url, timeout=60) as response, open(tmp_path, "wb") as out:
                shutil.copyfileobj(response, out)
            tmp_path.replace(dest)
            logger.info("Downloaded %s", dest)
            return True
        except Exception as e:
            logger.warning("Download failed (%s). Retrying in %.1fs...", e, backoff_sec)
            time.sleep(backoff_sec)
            backoff_sec *= 1.5
    return False


def ensure_yolo() -> Optional[Path]:
    """Ensure YOLO v8n weights exist in models/."""
    if YOLO_TARGET.exists():
        logger.info("YOLO weights already present: %s", YOLO_TARGET)
        return YOLO_TARGET

    for url in YOLO_URLS:
        if download_with_retries(url, YOLO_TARGET):
            return YOLO_TARGET

    logger.error("Failed to download YOLO weights after retries")
    return None


def ensure_insightface() -> bool:
    """
    Ensure InsightFace (antelopev2) is available.

    InsightFace typically manages its own model cache under the user directory.
    We trigger a warm-up so the required models are downloaded. If models are
    already present, this is a quick no-op. We drop a marker file under models/.
    """
    marker = MODELS_DIR / "insightface_buffalo_l_READY.txt"
    if marker.exists():
        logger.info("InsightFace models already prepared (marker present)")
        return True

    try:
        import insightface
        from insightface.app import FaceAnalysis

        logger.info("Preparing InsightFace models (buffalo_l)...")
        app = FaceAnalysis(name='buffalo_l')
        try:
            app.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as gpu_e:
            logger.info("GPU not available (%s); falling back to CPU", gpu_e)
            app.prepare(ctx_id=-1, det_size=(640, 640))
        # Touch marker to indicate preparation done
        marker.write_text("prepared")
        logger.info("InsightFace models prepared")
        return True
    except Exception as e:
        logger.warning("InsightFace preparation failed or not installed: %s", e)
        # Still create a marker to avoid repeated attempts if desired
        return False


def main() -> int:
    logger.info("🚀 Starting model verification/download...")

    y_ok = ensure_yolo() is not None
    i_ok = ensure_insightface()

    if y_ok and i_ok:
        logger.info("🎉 All models are ready.")
        return 0

    if not y_ok:
        logger.error("✗ YOLO weights are missing. Please check your network and rerun this script.")
    if not i_ok:
        logger.warning("⚠ InsightFace could not be prepared. If you do not need it, you can continue;")
        logger.warning("  otherwise install 'insightface' and rerun this script.")

    return 1 if not y_ok else 0


if __name__ == "__main__":
    sys.exit(main())


