import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logger = logging.getLogger("food_analyzer")
logger.setLevel(logging.DEBUG)

# Create a file handler that logs debug and higher level messages
file_handler = RotatingFileHandler("food_analyzer.log", maxBytes=5*1024*1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)

# Create a console handler that logs error and higher level messages
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)

# Create a formatter and set it for both handlers
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_debug(message: str):
    logger.debug(message)

def log_info(message: str):
    logger.info(message)

def log_warning(message: str):
    logger.warning(message)

def log_error(message: str, exc: Exception = None):
    if exc:
        logger.error(message, exc_info=True)
    else:
        logger.error(message)

def log_critical(message: str):
    logger.critical(message)
