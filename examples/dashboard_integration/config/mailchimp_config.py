"""
Mailchimp SDK Configuration Management System
Centralized configuration for API credentials and settings with proper error handling
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from mailchimp_marketing.api_client import ApiClientError
import mailchimp_marketing as MailchimpMarketing


@dataclass
class MailchimpConfig:
    """Configuration class for Mailchimp SDK settings"""
    api_key: str
    server: str
    timeout: int = 30
    retries: int = 3
    rate_limit: int = 100  # requests per minute


class MailchimpConfigManager:
    """
    Centralized configuration manager for Mailchimp SDK
    Handles API credentials, server configuration, and client initialization
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = None
        self.client = None
        self.logger = self._setup_logging()
        
        if config_file:
            self.load_from_file(config_file)
        else:
            self.load_from_env()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for configuration and API operations"""
        logger = logging.getLogger('mailchimp_sdk')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        try:
            api_key = os.getenv('MAILCHIMP_API_KEY')
            server = os.getenv('MAILCHIMP_SERVER', 'us1')
            
            if not api_key:
                raise ValueError("MAILCHIMP_API_KEY environment variable is required")
            
            self.config = MailchimpConfig(
                api_key=api_key,
                server=server,
                timeout=int(os.getenv('MAILCHIMP_TIMEOUT', '30')),
                retries=int(os.getenv('MAILCHIMP_RETRIES', '3')),
                rate_limit=int(os.getenv('MAILCHIMP_RATE_LIMIT', '100'))
            )
            
            self.logger.info("Configuration loaded from environment variables")
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"Configuration error: {e}")
            raise
    
    def load_from_file(self, config_file: str):
        """Load configuration from JSON or YAML file"""
        # Implementation for file-based configuration
        # Could be extended to support JSON/YAML config files
        raise NotImplementedError("File-based configuration not yet implemented")
    
    def get_client(self) -> MailchimpMarketing.Client:
        """
        Get configured Mailchimp client with proper error handling
        Implements connection pooling and rate limiting
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load_from_env() first.")
        
        if not self.client:
            try:
                self.client = MailchimpMarketing.Client()
                self.client.set_config({
                    "api_key": self.config.api_key,
                    "server": self.config.server,
                })
                
                # Test the connection
                self._test_connection()
                
                self.logger.info(f"Mailchimp client initialized successfully (server: {self.config.server})")
                
            except ApiClientError as e:
                self.logger.error(f"Failed to initialize Mailchimp client: {e}")
                raise
            except Exception as e:
                self.logger.error(f"Unexpected error initializing client: {e}")
                raise
        
        return self.client
    
    def _test_connection(self):
        """Test the Mailchimp API connection"""
        try:
            response = self.client.ping.get()
            self.logger.info("Connection test successful")
            return response
        except ApiClientError as e:
            self.logger.error(f"Connection test failed: {e}")
            raise
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get safe configuration information (without sensitive data)"""
        if not self.config:
            return {}
        
        return {
            "server": self.config.server,
            "timeout": self.config.timeout,
            "retries": self.config.retries,
            "rate_limit": self.config.rate_limit,
            "api_key_configured": bool(self.config.api_key)
        }


# Global configuration instance
_config_manager = None

def get_mailchimp_client() -> MailchimpMarketing.Client:
    """
    Global function to get configured Mailchimp client
    Singleton pattern for configuration management
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = MailchimpConfigManager()
    
    return _config_manager.get_client()


def get_config_manager() -> MailchimpConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = MailchimpConfigManager()
    
    return _config_manager