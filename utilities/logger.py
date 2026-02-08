"""Logging Utilities Module for Ingestion Pipeline."""

import logging
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str = __name__, level: int = logging.INFO, log_file: str | None = None
) -> logging.Logger:
    """
    Configures and returns a logger instance.

    Prevents duplicate handlers if the logger is already initialized.

    Args:
        name: The name of the logger.
        level: Logging level.
        log_file: Optional path to a file for persistent logging.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        if log_file:
            file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
    test_logger = setup_logger("test_logger", logging.DEBUG)
    test_logger.debug("This is a debug message.")
    test_logger.info("This is an info message.")
    test_logger.warning("This is a warning message.")
    test_logger.error("This is an error message.")
    test_logger.critical("This is a critical message.")
