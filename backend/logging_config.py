import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def configure_logging():
    log_dir = os.getenv("LOG_DIR", "/app/logs")
    log_file = os.path.join(log_dir, "app.log")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    root = logging.getLogger()
    # Clean slate so we don't duplicate handlers if called twice
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(log_level)

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # Daily rotating file, keep 14 days
    fh = TimedRotatingFileHandler(
        log_file, when="midnight", backupCount=15, encoding="utf-8"
    )
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    root.addHandler(fh)

     # IMPORTANT: make uvicorn use the same handlers/format
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []          # remove uvicorn's defaults
        lg.setLevel(log_level)
        lg.propagate = False      # don't double-log to root
        lg.addHandler(ch)
        lg.addHandler(fh)
