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
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_debug(message: str):
    logger.debug(message)
    log_info(f"Debug: {message}")
    log_error(f"Debug: {message}")

def log_info(message: str):
    logger.info(message)

def log_warning(message: str):
    logger.warning(message)
    log_info(f"Warning: {message}")
    log_error(f"Warning: {message}")

def log_error(message: str):
    logger.error(message)

def log_critical(message: str):
    logger.critical(message)
    log_info(f"Critical: {message}")
    log_error(f"Critical: {message}")
