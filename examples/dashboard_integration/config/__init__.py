"""
Configuration package for Mailchimp SDK integration
"""

from .mailchimp_config import (
    MailchimpConfig,
    MailchimpConfigManager, 
    get_mailchimp_client,
    get_config_manager
)

__all__ = [
    'MailchimpConfig',
    'MailchimpConfigManager',
    'get_mailchimp_client', 
    'get_config_manager'
]