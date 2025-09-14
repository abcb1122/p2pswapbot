"""
===============================================================================
CENTRALIZED LOGGING CONFIGURATION FOR P2P SWAP BOT
===============================================================================
Provides comprehensive logging infrastructure with synchronous file rotation
and sensitive data filtering. Implements Issue #30 Phase 1 requirements.

Log Format: YYYY-MM-DD HH:MM:SS | LEVEL | CATEGORY | ENTITY | ACTION | DETAILS
Categories: USER_INTERACTION, DEAL_STATE, PAYMENT, SYSTEM, ERROR
"""

import os
import logging
import logging.handlers
import atexit
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from log_filters import SensitiveDataFilter, LogEventFilter




class SwapBotLogFormatter(logging.Formatter):
    """
    Custom formatter implementing the required log format:
    YYYY-MM-DD HH:MM:SS | LEVEL | CATEGORY | ENTITY | ACTION | DETAILS
    """

    def format(self, record):
        # Extract custom fields from log record
        category = getattr(record, 'category', 'SYSTEM')
        entity = getattr(record, 'entity', '')
        action = getattr(record, 'action', '')
        details = getattr(record, 'details', '')

        # Format timestamp in UTC
        dt = datetime.fromtimestamp(record.created, timezone.utc)
        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')

        # Build the formatted message
        parts = [
            timestamp,
            record.levelname,
            category,
            entity,
            action,
            details if details else record.getMessage()
        ]

        return ' | '.join(str(part) for part in parts)


class SwapBotLogger:
    """
    Main logger class for P2P Swap Bot implementing comprehensive logging
    infrastructure with synchronous processing and sensitive data filtering.
    """

    def __init__(self):
        self.logs_dir = Path('logs')
        self._setup_directories()
        self._setup_loggers()

    def _setup_directories(self):
        """Create logs directory structure"""
        self.logs_dir.mkdir(exist_ok=True)

        # Create individual log files if they don't exist
        log_files = [
            'bot.log',
            'user_interactions.log',
            'payments.log',
            'timeouts.log',
            'errors.log'
        ]

        for log_file in log_files:
            (self.logs_dir / log_file).touch(exist_ok=True)

    def _setup_loggers(self):
        """Configure all loggers with proper handlers and filters"""

        # Main bot logger - all events
        self.main_logger = self._create_logger(
            'swap_bot',
            self.logs_dir / 'bot.log',
            level=logging.INFO
        )

        # User interactions logger
        self.user_logger = self._create_logger(
            'swap_bot.user',
            self.logs_dir / 'user_interactions.log',
            level=logging.INFO,
            filter_category='USER_INTERACTION'
        )

        # Payment events logger
        self.payment_logger = self._create_logger(
            'swap_bot.payment',
            self.logs_dir / 'payments.log',
            level=logging.INFO,
            filter_category='PAYMENT'
        )

        # Timeout events logger
        self.timeout_logger = self._create_logger(
            'swap_bot.timeout',
            self.logs_dir / 'timeouts.log',
            level=logging.WARNING,
            filter_category='TIMEOUT'
        )

        # Error-only logger
        self.error_logger = self._create_logger(
            'swap_bot.error',
            self.logs_dir / 'errors.log',
            level=logging.ERROR
        )

        # Register cleanup on exit
        atexit.register(self.shutdown)

    def _create_logger(self, name: str, log_file: Path, level: int,
                      filter_category: Optional[str] = None) -> logging.Logger:
        """Create a configured logger with file rotation and filtering"""

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Create rotating file handler (10MB max, keep 30 files)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=30,
            encoding='utf-8'
        )

        # Apply custom formatter
        formatter = SwapBotLogFormatter()
        file_handler.setFormatter(formatter)

        # Add sensitive data filter
        sensitive_filter = SensitiveDataFilter()
        file_handler.addFilter(sensitive_filter)

        # Add category filter if specified
        if filter_category:
            event_filter = LogEventFilter(category=filter_category)
            file_handler.addFilter(event_filter)

        logger.addHandler(file_handler)
        logger.propagate = False  # Prevent duplicate logging

        return logger

    def shutdown(self):
        """Shutdown all loggers and flush remaining logs"""
        logging.shutdown()

    def log_user_interaction(self, user_id: int, action: str, details: str = '',
                           level: int = logging.INFO):
        """Log user interaction events"""
        self._log_with_context(
            self.user_logger,
            level,
            category='USER_INTERACTION',
            entity=f'user_{user_id}',
            action=action,
            details=details
        )

    def log_command(self, user_id: int, command: str, details: Dict[str, Any] = None):
        """Log command execution"""
        details_str = self._format_details(details) if details else ''
        self.log_user_interaction(
            user_id=user_id,
            action=command,
            details=details_str
        )

    def log_button_click(self, user_id: int, callback_data: str, context: str = ''):
        """Log button click events"""
        details = f"callback={callback_data}"
        if context:
            details += f" context={context}"

        self.log_user_interaction(
            user_id=user_id,
            action='button_click',
            details=details
        )

    def log_user_registration(self, user_id: int, username: str = '',
                            registration_type: str = 'manual'):
        """Log user registration events"""
        details = f"type={registration_type}"
        if username:
            details += f" username={username}"

        self.log_user_interaction(
            user_id=user_id,
            action='user_registration',
            details=details
        )

    def log_error(self, message: str, exception: Exception = None,
                 user_id: Optional[int] = None, context: str = ''):
        """Log error events"""
        entity = f'user_{user_id}' if user_id else 'system'
        details = message

        if exception:
            details += f" | exception={type(exception).__name__}: {str(exception)}"
        if context:
            details += f" | context={context}"

        self._log_with_context(
            self.error_logger,
            logging.ERROR,
            category='ERROR',
            entity=entity,
            action='error',
            details=details
        )

    def log_system_event(self, action: str, details: str = '', level: int = logging.INFO):
        """Log system-level events"""
        self._log_with_context(
            self.main_logger,
            level,
            category='SYSTEM',
            entity='bot',
            action=action,
            details=details
        )

    def _log_with_context(self, logger: logging.Logger, level: int,
                         category: str, entity: str, action: str, details: str):
        """Internal method to log with structured context"""
        # Apply sensitive data filtering before logging
        from log_filters import SensitiveDataFilter
        sensitive_filter = SensitiveDataFilter()
        filtered_details = sensitive_filter._filter_message(details)

        # Create log record with custom attributes
        record = logger.makeRecord(
            logger.name, level, '', 0, filtered_details, None, None
        )
        record.category = category
        record.entity = entity
        record.action = action
        record.details = filtered_details

        logger.handle(record)

    def _format_details(self, details: Dict[str, Any]) -> str:
        """Format details dictionary as key=value pairs"""
        if not details:
            return ''

        return ' '.join(f"{key}={value}" for key, value in details.items())


# Global logger instance
_swap_logger = None

def get_swap_logger() -> SwapBotLogger:
    """Get the global SwapBotLogger instance"""
    global _swap_logger
    if _swap_logger is None:
        _swap_logger = SwapBotLogger()
    return _swap_logger

def init_logging():
    """Initialize logging - call this on bot startup"""
    logger = get_swap_logger()
    return logger