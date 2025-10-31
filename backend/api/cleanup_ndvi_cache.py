#!/usr/bin/env python3
"""
NDVI Cache Cleanup Script

Deletes NDVI data folders older than 1 day to prevent disk space buildup.
Run this script daily via cron or as a background task.

Usage:
    python backend/api/cleanup_ndvi_cache.py

Cron example (daily at 2am):
    0 2 * * * cd /path/to/project && python backend/api/cleanup_ndvi_cache.py
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_old_ndvi_data(ndvi_base_dir: str = "./ndvi_data", max_age_hours: int = 24):
    """
    Delete NDVI cache folders older than specified age.

    Args:
        ndvi_base_dir: Base directory containing NDVI data folders
        max_age_hours: Maximum age in hours (default: 24 = 1 day)

    Returns:
        Tuple of (deleted_count, freed_bytes)
    """
    ndvi_dir = Path(ndvi_base_dir)

    if not ndvi_dir.exists():
        logger.info(f"📁 NDVI directory does not exist: {ndvi_dir}")
        return 0, 0

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_timestamp = cutoff_time.timestamp()

    deleted_count = 0
    freed_bytes = 0

    logger.info(f"🔍 Scanning NDVI cache directory: {ndvi_dir}")
    logger.info(f"⏰ Deleting folders older than: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")

    for folder in ndvi_dir.iterdir():
        if not folder.is_dir():
            continue

        # Skip special folders (logs, intermediate, etc.)
        if folder.name in ['logs', 'intermediate', 'metadata', 'products', 'raw']:
            continue

        # Check folder modification time
        folder_mtime = folder.stat().st_mtime

        if folder_mtime < cutoff_timestamp:
            # Calculate folder size before deletion
            folder_size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
            folder_size_mb = folder_size / (1024 * 1024)

            try:
                shutil.rmtree(folder)
                deleted_count += 1
                freed_bytes += folder_size

                folder_age_hours = (datetime.now().timestamp() - folder_mtime) / 3600
                logger.info(f"🗑️  Deleted: {folder.name} (age: {folder_age_hours:.1f}h, size: {folder_size_mb:.1f} MB)")
            except Exception as e:
                logger.error(f"❌ Failed to delete {folder}: {e}")

    freed_mb = freed_bytes / (1024 * 1024)
    freed_gb = freed_bytes / (1024 * 1024 * 1024)

    if deleted_count > 0:
        logger.info(f"✅ Cleanup complete: Deleted {deleted_count} folder(s), freed {freed_gb:.2f} GB")
    else:
        logger.info(f"✅ No old folders to delete (all data is fresh)")

    return deleted_count, freed_bytes


if __name__ == "__main__":
    import sys

    # Allow custom max age via command line
    max_age_hours = 24  # Default: 1 day
    if len(sys.argv) > 1:
        try:
            max_age_hours = int(sys.argv[1])
            logger.info(f"📝 Using custom max age: {max_age_hours} hours")
        except ValueError:
            logger.error(f"❌ Invalid max_age argument: {sys.argv[1]}")
            sys.exit(1)

    deleted, freed = cleanup_old_ndvi_data(max_age_hours=max_age_hours)

    # Exit with status code
    sys.exit(0)
