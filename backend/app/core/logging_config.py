import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Formatter
log_format = logging.Formatter(
    "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

# File handler with rotation (10MB files, keeping 5 backups) - only if filesystem is writeable
try:
    log_dir = "/tmp/logs" if os.getenv("VERCEL") else "logs"
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
except Exception as exc:
    # On serverless platforms with read-only filesystems, fallback to stdout console logging
    pass

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger by name."""
    return logging.getLogger(name)

def get_memory_usage_mb() -> float:
    """Returns current process RAM usage in Megabytes (MB)."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

