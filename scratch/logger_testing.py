import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.utils.logger import setup_logging 
import logging
import src.utils.logger as logger

logger.setup_logging()
# Manually trigger different log levels
logging.debug("This is a Debug message (detailed debugging)")
logging.info("This is an Info message (normal program operation)")
logging.warning("This is a Warning message (potential issue detected)")
logging.error("This is an Error message (error occurred!)")
