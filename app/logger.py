import os
import sys

from loguru import logger

from app.settings import settings

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "app.log")

# Remove default handler to avoid duplicate logs
logger.remove()

# Console handler
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    enqueue=True,
    backtrace=False,
    diagnose=False,
    serialize=False,
)

# File handler with rotation & retention
logger.add(
    log_file,
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    level=settings.LOG_LEVEL,
    enqueue=True,
)

