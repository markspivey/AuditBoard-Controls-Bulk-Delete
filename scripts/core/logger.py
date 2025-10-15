#!/usr/bin/env python3
"""
Logging Utilities
Standardized logging for all AuditBoard scripts.
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


class ScriptLogger:
    """Standardized logger for AuditBoard scripts."""

    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        log_level: Optional[str] = None,
        console_output: bool = True
    ):
        """
        Initialize script logger.

        Args:
            name: Logger name (usually script name)
            log_file: Path to log file (optional)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to output to console
        """
        self.logger = logging.getLogger(name)

        # Get log level from env or parameter
        level_str = log_level or os.getenv('LOG_LEVEL', 'INFO')
        level = getattr(logging, level_str.upper(), logging.INFO)
        self.logger.setLevel(level)

        # Clear existing handlers
        self.logger.handlers = []

        # Create formatter with timestamp
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)

    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)

    def section(self, title: str, width: int = 80):
        """Log a section header."""
        self.logger.info("=" * width)
        self.logger.info(title)
        self.logger.info("=" * width)

    def subsection(self, title: str, width: int = 80):
        """Log a subsection header."""
        self.logger.info("-" * width)
        self.logger.info(title)
        self.logger.info("-" * width)


def get_logger(
    name: str,
    log_dir: Optional[str] = None,
    log_level: Optional[str] = None
) -> ScriptLogger:
    """
    Get a standardized logger for a script.

    Args:
        name: Script name
        log_dir: Directory for log files (uses results/ if not specified)
        log_level: Logging level

    Returns:
        Configured ScriptLogger instance
    """
    if log_dir is None:
        log_dir = os.getenv('LOG_DIR', 'results')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/{name}_{timestamp}.log"

    return ScriptLogger(
        name=name,
        log_file=log_file,
        log_level=log_level,
        console_output=True
    )
