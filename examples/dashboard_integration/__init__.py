"""
Mailchimp Marketing SDK Dashboard Integration Example

This package provides a complete implementation of Phase 1 of the Mailchimp
SDK integration plan, including:

- Centralized configuration management
- Enhanced data ingestion with error handling
- Interactive dashboard pages with advanced analytics
- Jupyter notebook for API exploration
- Production-ready code patterns

Usage:
    from config import get_mailchimp_client
    from scripts.ingest_mailchimp import MailchimpDataIngestion
    
    client = get_mailchimp_client()
    ingester = MailchimpDataIngestion()
"""

__version__ = "1.0.0"
__author__ = "Phase 1 Implementation"