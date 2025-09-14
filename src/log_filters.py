"""
===============================================================================
LOG FILTERS FOR P2P SWAP BOT - SENSITIVE DATA PROTECTION
===============================================================================
Implements comprehensive filtering to prevent sensitive data from appearing
in log files. Protects private keys, API keys, Bitcoin addresses, Lightning
invoices, and other confidential information.

Part of Issue #30 Phase 1 implementation.
"""

import re
import logging
from typing import Optional, Pattern, List


class SensitiveDataFilter(logging.Filter):
    """
    Filter to remove or mask sensitive data from log messages.
    Prevents accidental exposure of private keys, addresses, and API tokens.
    """

    def __init__(self):
        super().__init__()
        self._setup_patterns()

    def _setup_patterns(self):
        """Initialize regex patterns for sensitive data detection"""

        # Bitcoin address patterns (mainnet and testnet)
        self.bitcoin_address_patterns = [
            # Legacy addresses (1...)
            re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'),
            # SegWit addresses (3...)
            re.compile(r'\b3[a-km-zA-HJ-NP-Z1-9]{25,34}\b'),
            # Bech32 addresses (bc1... or tb1...)
            re.compile(r'\b(bc1|tb1)[a-zA-HJ-NP-Z0-9]{25,87}\b'),
        ]

        # Lightning Network patterns
        self.lightning_patterns = [
            # Lightning invoices (lnbc, lntb, lnbcrt)
            re.compile(r'\b(lnbc|lntb|lnbcrt)[a-zA-Z0-9]{100,2000}\b', re.IGNORECASE),
            # Lightning node public keys (66 hex characters)
            re.compile(r'\b[a-fA-F0-9]{66}\b'),
        ]

        # Private key patterns
        self.private_key_patterns = [
            # WIF format private keys
            re.compile(r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b'),
            # Compressed WIF format
            re.compile(r'\bc[1-9A-HJ-NP-Za-km-z]{50,51}\b'),
            # Hex private keys (64 hex characters)
            re.compile(r'\b[a-fA-F0-9]{64}\b'),
        ]

        # API keys and tokens
        self.api_key_patterns = [
            # Generic API key patterns
            re.compile(r'\b[Aa][Pp][Ii]_?[Kk][Ee][Yy]\s*[=:]\s*[\'"]?([a-zA-Z0-9_\-]{20,})[\'"]?'),
            re.compile(r'\b[Tt][Oo][Kk][Ee][Nn]\s*[=:]\s*[\'"]?([a-zA-Z0-9_\-]{20,})[\'"]?'),
            # Telegram bot token pattern
            re.compile(r'\b\d{8,10}:[a-zA-Z0-9_\-]{35}\b'),
            # Common API key formats
            re.compile(r'\bsk_[a-zA-Z0-9]{20,50}\b'),  # Stripe-style
            re.compile(r'\bpk_[a-zA-Z0-9]{20,50}\b'),  # Public keys
        ]

        # Seed phrases and mnemonics
        self.seed_patterns = [
            # BIP39 seed phrases (12-24 words)
            re.compile(r'\b(?:[a-z]+\s+){11,23}[a-z]+\b', re.IGNORECASE),
        ]

        # Personal information patterns
        self.personal_patterns = [
            # Email addresses
            re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
            # Phone numbers (basic pattern)
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to remove sensitive data.
        Returns True to keep the record, False to discard it.
        """
        try:
            # Get the message to filter
            if hasattr(record, 'getMessage'):
                message = record.getMessage()
            else:
                message = str(record.msg)

            # Apply all filters
            filtered_message = self._filter_message(message)

            # Update the record with filtered message
            record.msg = filtered_message
            record.args = ()  # Clear args to prevent re-formatting

            # Also filter custom fields if they exist
            if hasattr(record, 'details'):
                record.details = self._filter_message(str(record.details))

            if hasattr(record, 'entity'):
                record.entity = self._filter_entity(str(record.entity))

            return True

        except Exception as e:
            # If filtering fails, log the error but keep the record
            # (better to have unfiltered logs than no logs)
            print(f"Log filtering error: {e}")
            return True

    def _filter_message(self, message: str) -> str:
        """Apply all sensitive data filters to a message"""
        if not message:
            return message

        # Filter Bitcoin addresses (show first 8 chars + ...)
        for pattern in self.bitcoin_address_patterns:
            message = pattern.sub(lambda m: f"{m.group()[:8]}...", message)

        # Filter Lightning invoices (show first 10 chars + ...)
        for pattern in self.lightning_patterns:
            message = pattern.sub(lambda m: f"{m.group()[:10]}...", message)

        # Filter private keys (completely remove)
        for pattern in self.private_key_patterns:
            message = pattern.sub("[PRIVATE_KEY_FILTERED]", message)

        # Filter API keys and tokens (completely remove)
        for pattern in self.api_key_patterns:
            message = pattern.sub("[API_KEY_FILTERED]", message)

        # Filter seed phrases (completely remove)
        for pattern in self.seed_patterns:
            message = pattern.sub("[SEED_PHRASE_FILTERED]", message)

        # Filter personal information (mask most characters)
        message = self._filter_emails(message)
        message = self._filter_phone_numbers(message)

        return message

    def _filter_entity(self, entity: str) -> str:
        """Filter entity field (usually contains user IDs which are safe)"""
        # Entity field typically contains safe identifiers like 'user_123456'
        # No filtering needed for now, but method exists for future expansion
        return entity

    def _filter_emails(self, message: str) -> str:
        """Mask email addresses while keeping domain for debugging"""
        def mask_email(match):
            email = match.group()
            local, domain = email.split('@', 1)
            masked_local = local[0] + '*' * (len(local) - 1) if len(local) > 1 else '*'
            return f"{masked_local}@{domain}"

        return self.personal_patterns[0].sub(mask_email, message)

    def _filter_phone_numbers(self, message: str) -> str:
        """Mask phone numbers"""
        return self.personal_patterns[1].sub("***-***-****", message)


class LogEventFilter(logging.Filter):
    """
    Filter to include only specific event categories in themed log files.
    Used by specialized loggers (user_interactions.log, payments.log, etc.)
    """

    def __init__(self, category: str = None, level: int = None):
        super().__init__()
        self.category = category
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter records based on category and/or level.
        Returns True to include the record in the log.
        """
        # Check category filter
        if self.category:
            record_category = getattr(record, 'category', 'SYSTEM')
            if record_category != self.category:
                return False

        # Check level filter
        if self.level and record.levelno < self.level:
            return False

        return True


class DebugOnlyFilter(logging.Filter):
    """
    Filter that only allows records through when debug mode is enabled.
    Useful for performance-sensitive debug logging.
    """

    def __init__(self, debug_enabled: bool = False):
        super().__init__()
        self.debug_enabled = debug_enabled

    def filter(self, record: logging.LogRecord) -> bool:
        """Only allow debug records when debug mode is enabled"""
        if record.levelno == logging.DEBUG:
            return self.debug_enabled
        return True

    def enable_debug(self):
        """Enable debug logging"""
        self.debug_enabled = True

    def disable_debug(self):
        """Disable debug logging"""
        self.debug_enabled = False


class RateLimitFilter(logging.Filter):
    """
    Rate limiting filter to prevent log spam from repeated identical messages.
    Useful for preventing overwhelming logs during API failures or errors.
    """

    def __init__(self, max_rate: int = 10, time_window: int = 60):
        super().__init__()
        self.max_rate = max_rate  # Maximum messages per time window
        self.time_window = time_window  # Time window in seconds
        self.message_counts = {}  # Track message counts
        self.last_cleanup = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Rate limit identical log messages.
        Returns True to allow the message, False to suppress it.
        """
        import time

        current_time = time.time()
        message_key = f"{record.levelname}:{record.getMessage()}"

        # Clean up old entries periodically
        if current_time - self.last_cleanup > self.time_window:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time

        # Check if message is within rate limit
        if message_key in self.message_counts:
            count, first_seen = self.message_counts[message_key]

            # Reset counter if time window has passed
            if current_time - first_seen > self.time_window:
                self.message_counts[message_key] = (1, current_time)
                return True

            # Increment counter and check limit
            self.message_counts[message_key] = (count + 1, first_seen)
            return count < self.max_rate
        else:
            # First occurrence of this message
            self.message_counts[message_key] = (1, current_time)
            return True

    def _cleanup_old_entries(self, current_time: float):
        """Remove entries older than the time window"""
        expired_keys = []
        for key, (count, first_seen) in self.message_counts.items():
            if current_time - first_seen > self.time_window:
                expired_keys.append(key)

        for key in expired_keys:
            del self.message_counts[key]