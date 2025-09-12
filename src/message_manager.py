#!/usr/bin/env python3
"""
===============================================================================
MESSAGE MANAGER - P2P SWAP BOT
===============================================================================
Centralized message management system for P2P Bitcoin Swap Bot.
Loads messages from messages.yaml and provides lookup by MSG-XXX ID.

Issue #36: Centralized Message Management System
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MessageManager:
    """
    Centralized message manager that loads from messages.yaml
    and provides MSG-XXX lookup with variable substitution.
    """
    
    def __init__(self, messages_path: str = None):
        """
        Initialize MessageManager by loading messages from YAML file.
        
        Args:
            messages_path: Path to messages.yaml file (auto-detects if None)
        """
        # Auto-detect messages.yaml path
        if messages_path is None:
            # Try different possible paths
            possible_paths = [
                'messages.yaml',           # When running from src/
                'src/messages.yaml',       # When running from project root
                '../messages.yaml'         # Alternative path
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    messages_path = path
                    break
            else:
                messages_path = 'messages.yaml'  # Default fallback
        
        self.messages_path = messages_path
        self.messages = {}
        self.message_index = {}  # MSG-XXX -> message data index
        self._load_messages()
        
    def _load_messages(self):
        """Load messages from YAML file and build MSG-XXX index"""
        try:
            if not os.path.exists(self.messages_path):
                logger.error(f"Messages file not found: {self.messages_path}")
                return
                
            with open(self.messages_path, 'r', encoding='utf-8') as file:
                self.messages = yaml.safe_load(file)
                
            # Build MSG-XXX index for fast lookup
            self._build_message_index()
            
            logger.info(f"Loaded {len(self.message_index)} messages from {self.messages_path}")
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML: {e}")
            self.messages = {}
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            self.messages = {}
    
    def _build_message_index(self):
        """
        Build MSG-XXX -> message index for efficient lookup.
        Traverses all categories in the YAML structure.
        """
        self.message_index = {}
        
        for category_name, category in self.messages.items():
            if isinstance(category, dict):
                for message_key, message_data in category.items():
                    if isinstance(message_data, dict) and 'id' in message_data:
                        msg_id = message_data['id']
                        self.message_index[msg_id] = {
                            'text': message_data.get('text', ''),
                            'description': message_data.get('description', ''),
                            'category': category_name,
                            'key': message_key,
                            'variables': message_data.get('variables', [])
                        }
        
        logger.debug(f"Built message index with {len(self.message_index)} entries")
    
    def get_message(self, message_id: str, **kwargs) -> str:
        """
        Get message by MSG-XXX ID with variable substitution.
        
        Args:
            message_id: Message ID (e.g., 'MSG-001')
            **kwargs: Variables to substitute in the message
            
        Returns:
            Formatted message with variables substituted
        """
        if message_id not in self.message_index:
            logger.error(f"Message ID '{message_id}' not found")
            return f"❌ Message {message_id} not found"
        
        message_data = self.message_index[message_id]
        text = message_data['text']
        
        try:
            # Substitute variables in the text
            formatted_text = text.format(**kwargs)
            
            logger.debug(f"Retrieved message {message_id}: {message_data['description'][:50]}...")
            return formatted_text
            
        except KeyError as e:
            missing_var = str(e).strip("'")
            logger.warning(f"Missing variable '{missing_var}' for message {message_id}")
            return text  # Return original text if substitution fails
        except Exception as e:
            logger.error(f"Error formatting message {message_id}: {e}")
            return text
    
    def get_by_category(self, category: str, message_key: str, **kwargs) -> str:
        """
        Get message by category and key (alternative to MSG-XXX lookup).
        
        Args:
            category: Category name (e.g., 'carlos_messages')
            message_key: Message key (e.g., 'deal_started_swapout')
            **kwargs: Variables to substitute
            
        Returns:
            Formatted message
        """
        try:
            if category not in self.messages:
                logger.error(f"Category '{category}' not found")
                return f"❌ Category {category} not found"
            
            if message_key not in self.messages[category]:
                logger.error(f"Message key '{message_key}' not found in category '{category}'")
                return f"❌ Message {message_key} not found"
            
            message_data = self.messages[category][message_key]
            text = message_data.get('text', '')
            
            # Substitute variables
            return text.format(**kwargs)
            
        except Exception as e:
            logger.error(f"Error getting message {category}.{message_key}: {e}")
            return f"❌ Error loading message"
    
    def format_amount(self, amount: int) -> str:
        """Format amount with dots as thousand separators (Latin format)"""
        return f"{amount:,}".replace(",", ".")
    
    def get_rating_stars(self, rating: float) -> str:
        """Convert numeric rating to stars"""
        return '⭐' * int(rating)
    
    def list_messages(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        List all messages or messages in a specific category.
        Useful for debugging and validation.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            Dictionary of messages
        """
        if category:
            return self.messages.get(category, {})
        return self.message_index
    
    def validate_message(self, message_id: str, required_vars: list) -> bool:
        """
        Validate that a message exists and has all required variables.
        
        Args:
            message_id: Message ID to validate
            required_vars: List of required variable names
            
        Returns:
            True if message is valid with all variables
        """
        if message_id not in self.message_index:
            logger.error(f"Message {message_id} not found for validation")
            return False
        
        message_text = self.message_index[message_id]['text']
        
        # Check if all required variables are in the message text
        for var in required_vars:
            if f"{{{var}}}" not in message_text:
                logger.warning(f"Variable '{var}' not found in message {message_id}")
                return False
        
        return True
    
    def reload_messages(self):
        """Reload messages from YAML file (useful for development)"""
        logger.info("Reloading messages from file")
        self._load_messages()


def test_message_manager():
    """
    Test function to validate MessageManager functionality.
    """
    print("Testing MessageManager with P2P Swap Bot messages...\n")
    
    # Initialize manager with auto-path detection
    msg = MessageManager()
    
    # Test 1: Basic message retrieval
    print("Test 1: Basic message (MSG-001)")
    welcome = msg.get_message('MSG-001')
    print(f"Result: {welcome[:100]}...\n")
    
    # Test 2: Message with variables
    print("Test 2: Message with variables (MSG-009)")
    deal_msg = msg.get_message('MSG-009', 
                              offer_id=42,
                              amount_text="10.000",
                              TXID_TIMEOUT_MINUTES=30)
    print(f"Result: {deal_msg[:150]}...\n")
    
    # Test 3: Category-based retrieval
    print("Test 3: Category-based retrieval")
    category_msg = msg.get_by_category('carlos_messages', 'take_usage_error')
    print(f"Result: {category_msg[:100]}...\n")
    
    # Test 4: Helper functions
    print("Test 4: Helper functions")
    formatted_amount = msg.format_amount(100000)
    stars = msg.get_rating_stars(4.5)
    print(f"Amount: {formatted_amount}, Stars: {stars}\n")
    
    # Test 5: Error handling
    print("Test 5: Error handling")
    missing_msg = msg.get_message('MSG-999')
    print(f"Missing message: {missing_msg}\n")
    
    # Test 6: Message validation
    print("Test 6: Message validation")
    is_valid = msg.validate_message('MSG-009', ['offer_id', 'amount_text'])
    print(f"MSG-009 validation: {is_valid}\n")
    
    # Test 7: List messages count
    print("Test 7: Messages loaded")
    total_messages = len(msg.message_index)
    print(f"Total messages loaded: {total_messages}")


if __name__ == '__main__':
    # Set up basic logging for testing
    logging.basicConfig(level=logging.INFO)
    test_message_manager()
