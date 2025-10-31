# NDVI Cache Cleanup - Setup Guide

## Overview

The NDVI cache cleanup script deletes satellite data older than **1 day (24 hours)** to prevent disk space buildup.

## Manual Execution

Run the cleanup script manually anytime:

```bash
# From project root
python backend/api/cleanup_ndvi_cache.py

# With custom max age (e.g., 12 hours)
python backend/api/cleanup_ndvi_cache.py 12
```

**Example output:**
```
2025-10-24 15:30:00 - INFO - 🔍 Scanning NDVI cache directory: ndvi_data
2025-10-24 15:30:00 - INFO - ⏰ Deleting folders older than: 2025-10-23 15:30:00
2025-10-24 15:30:01 - INFO - 🗑️  Deleted: 2025-10-19_2025-10-20_72b3637e (age: 25.2h, size: 458.3 MB)
2025-10-24 15:30:02 - INFO - 🗑️  Deleted: 2025-10-20_2025-10-21_c71d85b3 (age: 24.5h, size: 12.1 MB)
2025-10-24 15:30:02 - INFO - ✅ Cleanup complete: Deleted 2 folder(s), freed 0.46 GB
```

## Automated Cleanup (Recommended)

### Option 1: Cron Job (Linux/Mac)

Add to your crontab to run daily at 2am:

```bash
# Edit crontab
crontab -e

# Add this line (replace /path/to/project with actual path)
0 2 * * * cd /home/ggous/Models/Transition && python backend/api/cleanup_ndvi_cache.py >> logs/cleanup.log 2>&1
```

**Cron schedule examples:**
```bash
0 2 * * *       # Daily at 2am
0 */6 * * *     # Every 6 hours
*/30 * * * *    # Every 30 minutes (aggressive)
```

### Option 2: Systemd Timer (Linux)

Create a systemd service:

```bash
# /etc/systemd/system/ndvi-cleanup.service
[Unit]
Description=NDVI Cache Cleanup

[Service]
Type=oneshot
WorkingDirectory=/home/ggous/Models/Transition
ExecStart=/usr/bin/python3 backend/api/cleanup_ndvi_cache.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create a timer:

```bash
# /etc/systemd/system/ndvi-cleanup.timer
[Unit]
Description=NDVI Cache Cleanup Timer

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable ndvi-cleanup.timer
sudo systemctl start ndvi-cleanup.timer

# Check status
sudo systemctl status ndvi-cleanup.timer
```

### Option 3: Background Task (Python/FastAPI)

Add to FastAPI startup events for automatic cleanup:

```python
# backend/api/server.py
from apscheduler.schedulers.background import BackgroundScheduler
from backend.api.cleanup_ndvi_cache import cleanup_old_ndvi_data

scheduler = BackgroundScheduler()

@app.on_event("startup")
async def startup_event():
    # Run cleanup daily at 2am
    scheduler.add_job(
        cleanup_old_ndvi_data,
        'cron',
        hour=2,
        minute=0,
        kwargs={'max_age_hours': 24}
    )
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
```

Install required package:
```bash
pip install apscheduler
```

## What Gets Deleted?

### Deleted:
- ✅ Timestamped NDVI folders (e.g., `ndvi_data/2025-10-19_2025-10-20_72b3637e/`)
- ✅ Folders older than 24 hours (based on modification time)

### Preserved:
- ❌ Recent data (< 24 hours old)
- ❌ Special folders (`logs/`, `intermediate/`, `metadata/`, `products/`, `raw/`)

## Testing

Test the cleanup script without waiting 24 hours:

```bash
# Use 1-hour max age for testing
python backend/api/cleanup_ndvi_cache.py 1

# Or 0 hours to delete everything immediately
python backend/api/cleanup_ndvi_cache.py 0
```

## Monitoring

Check cleanup logs:
```bash
# If using cron with log redirection
tail -f logs/cleanup.log

# If using systemd
journalctl -u ndvi-cleanup.service -f
```

## Disk Space Estimates

**Typical NDVI cache sizes:**
- Single date range: **100-500 MB** (with NDVI, NDWI, RGB)
- 10 cached requests: **1-5 GB**
- 100 cached requests: **10-50 GB**

**With 24-hour cleanup:**
- If 10 users/day × 2 requests each = **20 folders/day**
- Disk usage: **2-10 GB** (cleaned daily)

## Troubleshooting

**"Permission denied" error:**
```bash
# Make script executable
chmod +x backend/api/cleanup_ndvi_cache.py

# Check ownership
ls -la ndvi_data/
```

**Cron not running:**
```bash
# Check cron service is running
systemctl status cron  # or crond on some systems

# Check cron logs
grep CRON /var/log/syslog
```

**Script runs but doesn't delete:**
- Check if data is actually older than 24 hours
- Run with custom age: `python backend/api/cleanup_ndvi_cache.py 0`
- Check file permissions on `ndvi_data/` folder

---

**Last Updated**: 2025-10-24
**Cleanup Policy**: Delete NDVI data older than **1 day (24 hours)**
