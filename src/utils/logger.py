import logging
import os

# Prosty logger aplikacyjny. Python logging to standardowa biblioteka. [web:19]
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # już skonfigurowany

    logger.setLevel(_LOG_LEVEL)
    handler = logging.StreamHandler()
    handler.setLevel(_LOG_LEVEL)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
