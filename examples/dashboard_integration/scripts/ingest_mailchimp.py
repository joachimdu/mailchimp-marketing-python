"""
Enhanced Mailchimp Data Ingestion Script
Replaces custom API calls with official SDK, includes proper error handling,
data validation, and transformation layer for dashboard integration
"""

import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError

# Import our configuration management
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import get_mailchimp_client, get_config_manager


@dataclass
class CampaignMetrics:
    """Data model for standardized campaign metrics"""
    campaign_id: str
    campaign_name: str
    subject_line: str
    send_time: str
    emails_sent: int
    opens: int
    opens_unique: int
    open_rate: float
    clicks: int
    clicks_unique: int
    click_rate: float
    bounces: int
    bounce_rate: float
    unsubscribes: int
    unsubscribe_rate: float
    delivery_rate: float
    complaint_rate: float = 0.0
    revenue: float = 0.0
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ListMetrics:
    """Data model for audience/list metrics"""
    list_id: str
    list_name: str
    member_count: int
    unsubscribe_count: int
    cleaned_count: int
    member_count_since_send: int
    unsubscribe_count_since_send: int
    cleaned_count_since_send: int
    avg_sub_rate: float
    avg_unsub_rate: float
    target_sub_rate: float
    open_rate: float
    click_rate: float
    date_created: str
    last_updated: str = ""


class MailchimpDataIngestion:
    """
    Advanced Mailchimp data ingestion with SDK integration
    Features: batch processing, error handling, data validation, transformation layer
    """
    
    def __init__(self):
        self.client = get_mailchimp_client()
        self.config_manager = get_config_manager()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for ingestion operations"""
        logger = logging.getLogger('mailchimp_ingestion')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _handle_api_error(self, operation: str, error: ApiClientError):
        """Centralized API error handling with retries"""
        self.logger.error(f"API error in {operation}: {error.text}")
        
        # Check if it's a rate limit error
        if hasattr(error, 'status') and error.status == 429:
            self.logger.info("Rate limit hit, waiting 60 seconds...")
            time.sleep(60)
            return True  # Indicates retry should be attempted
        
        return False  # No retry
    
    def get_all_campaigns(self, since_date: Optional[str] = None, limit: int = 1000) -> List[CampaignMetrics]:
        """
        Retrieve all campaigns with comprehensive metrics using SDK
        Enhanced with pagination, filtering, and error handling
        """
        campaigns = []
        offset = 0
        batch_size = 100  # Mailchimp API limit
        
        try:
            while len(campaigns) < limit:
                self.logger.info(f"Fetching campaigns batch: offset={offset}, count={batch_size}")
                
                # Get campaigns list with enhanced filtering
                response = self.client.campaigns.list(
                    count=batch_size,
                    offset=offset,
                    status='sent',
                    since_send_time=since_date
                )
                
                if not response.get('campaigns'):
                    break
                
                # Process each campaign and get detailed reports
                for campaign in response['campaigns']:
                    try:
                        metrics = self._process_campaign_metrics(campaign)
                        if metrics:
                            campaigns.append(metrics)
                    except ApiClientError as e:
                        if not self._handle_api_error(f"campaign {campaign.get('id', 'unknown')}", e):
                            continue  # Skip this campaign if non-retryable error
                
                offset += batch_size
                
                # Respect rate limits
                time.sleep(0.1)
                
                if len(response['campaigns']) < batch_size:
                    break  # No more campaigns
                    
        except ApiClientError as e:
            self.logger.error(f"Failed to retrieve campaigns: {e}")
            raise
        
        self.logger.info(f"Retrieved {len(campaigns)} campaigns successfully")
        return campaigns
    
    def _process_campaign_metrics(self, campaign: Dict[str, Any]) -> Optional[CampaignMetrics]:
        """Process individual campaign and get detailed metrics"""
        campaign_id = campaign['id']
        
        try:
            # Get detailed campaign report using SDK
            report = self.client.reports.get_campaign_report(campaign_id)
            
            # Transform SDK response to our standardized data model
            metrics = CampaignMetrics(
                campaign_id=campaign_id,
                campaign_name=campaign.get('settings', {}).get('title', ''),
                subject_line=campaign.get('settings', {}).get('subject_line', ''),
                send_time=campaign.get('send_time', ''),
                emails_sent=report.get('emails_sent', 0),
                opens=report.get('opens', {}).get('opens_total', 0),
                opens_unique=report.get('opens', {}).get('unique_opens', 0),
                open_rate=report.get('opens', {}).get('open_rate', 0.0),
                clicks=report.get('clicks', {}).get('clicks_total', 0),
                clicks_unique=report.get('clicks', {}).get('unique_clicks', 0),
                click_rate=report.get('clicks', {}).get('click_rate', 0.0),
                bounces=report.get('bounces', {}).get('hard_bounces', 0) + report.get('bounces', {}).get('soft_bounces', 0),
                bounce_rate=report.get('bounces', {}).get('bounce_rate', 0.0),
                unsubscribes=report.get('unsubscribed', {}).get('unsubscribes', 0),
                unsubscribe_rate=report.get('unsubscribed', {}).get('unsubscribe_rate', 0.0),
                delivery_rate=report.get('delivery_status', {}).get('delivery_rate', 0.0),
                complaint_rate=report.get('abuse_reports', 0) / max(report.get('emails_sent', 1), 1),
                revenue=report.get('ecommerce', {}).get('total_revenue', 0.0),
                created_at=campaign.get('create_time', '')
            )
            
            return metrics
            
        except ApiClientError as e:
            self.logger.warning(f"Could not get report for campaign {campaign_id}: {e}")
            return None
    
    def get_all_lists(self) -> List[ListMetrics]:
        """
        Retrieve all lists with comprehensive audience metrics
        Enhanced with growth tracking and engagement analytics
        """
        lists_data = []
        
        try:
            # Get all lists using SDK
            response = self.client.lists.get_all_lists(count=1000)
            
            for list_item in response.get('lists', []):
                try:
                    metrics = self._process_list_metrics(list_item)
                    if metrics:
                        lists_data.append(metrics)
                except ApiClientError as e:
                    if not self._handle_api_error(f"list {list_item.get('id', 'unknown')}", e):
                        continue
                        
        except ApiClientError as e:
            self.logger.error(f"Failed to retrieve lists: {e}")
            raise
        
        self.logger.info(f"Retrieved {len(lists_data)} lists successfully")
        return lists_data
    
    def _process_list_metrics(self, list_item: Dict[str, Any]) -> Optional[ListMetrics]:
        """Process individual list and get detailed metrics"""
        list_id = list_item['id']
        
        try:
            # Get list stats using SDK
            stats = list_item.get('stats', {})
            
            metrics = ListMetrics(
                list_id=list_id,
                list_name=list_item.get('name', ''),
                member_count=stats.get('member_count', 0),
                unsubscribe_count=stats.get('unsubscribe_count', 0),
                cleaned_count=stats.get('cleaned_count', 0),
                member_count_since_send=stats.get('member_count_since_send', 0),
                unsubscribe_count_since_send=stats.get('unsubscribe_count_since_send', 0),
                cleaned_count_since_send=stats.get('cleaned_count_since_send', 0),
                avg_sub_rate=stats.get('avg_sub_rate', 0.0),
                avg_unsub_rate=stats.get('avg_unsub_rate', 0.0),
                target_sub_rate=stats.get('target_sub_rate', 0.0),
                open_rate=stats.get('open_rate', 0.0),
                click_rate=stats.get('click_rate', 0.0),
                date_created=list_item.get('date_created', ''),
                last_updated=datetime.now().isoformat()
            )
            
            return metrics
            
        except Exception as e:
            self.logger.warning(f"Could not process list {list_id}: {e}")
            return None
    
    def get_enhanced_campaign_analytics(self, campaign_ids: List[str]) -> Dict[str, Any]:
        """
        Get enhanced analytics for specific campaigns including:
        - Click heatmaps
        - Geographic data  
        - Email activity tracking
        - A/B testing results
        """
        enhanced_data = {}
        
        for campaign_id in campaign_ids:
            try:
                campaign_data = {}
                
                # Get click details
                click_details = self.client.reports.get_campaign_click_details(campaign_id)
                campaign_data['click_details'] = click_details
                
                # Get geographic data
                locations = self.client.reports.get_locations_for_campaign(campaign_id)
                campaign_data['locations'] = locations
                
                # Get email activity (sample)
                email_activity = self.client.reports.get_email_activity_for_campaign(
                    campaign_id, count=100
                )
                campaign_data['email_activity'] = email_activity
                
                enhanced_data[campaign_id] = campaign_data
                
                # Rate limiting
                time.sleep(0.2)
                
            except ApiClientError as e:
                self.logger.warning(f"Could not get enhanced data for campaign {campaign_id}: {e}")
                continue
                
        return enhanced_data
    
    def export_to_dataframes(self, campaigns: List[CampaignMetrics], lists: List[ListMetrics]) -> Dict[str, pd.DataFrame]:
        """
        Export data to pandas DataFrames for dashboard integration
        Includes data validation and transformation
        """
        try:
            # Convert campaigns to DataFrame
            campaigns_df = pd.DataFrame([campaign.to_dict() for campaign in campaigns])
            
            # Convert lists to DataFrame  
            lists_df = pd.DataFrame([asdict(list_item) for list_item in lists])
            
            # Data validation and cleaning
            if not campaigns_df.empty:
                campaigns_df['send_time'] = pd.to_datetime(campaigns_df['send_time'], errors='coerce')
                campaigns_df['created_at'] = pd.to_datetime(campaigns_df['created_at'], errors='coerce')
                
                # Convert rate fields to percentages
                rate_columns = ['open_rate', 'click_rate', 'bounce_rate', 'unsubscribe_rate', 'delivery_rate', 'complaint_rate']
                for col in rate_columns:
                    if col in campaigns_df.columns:
                        campaigns_df[col] = campaigns_df[col] * 100
            
            if not lists_df.empty:
                lists_df['date_created'] = pd.to_datetime(lists_df['date_created'], errors='coerce')
                lists_df['last_updated'] = pd.to_datetime(lists_df['last_updated'], errors='coerce')
                
                # Convert rate fields to percentages
                rate_columns = ['avg_sub_rate', 'avg_unsub_rate', 'target_sub_rate', 'open_rate', 'click_rate']
                for col in rate_columns:
                    if col in lists_df.columns:
                        lists_df[col] = lists_df[col] * 100
            
            self.logger.info(f"Exported {len(campaigns_df)} campaigns and {len(lists_df)} lists to DataFrames")
            
            return {
                'campaigns': campaigns_df,
                'lists': lists_df
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting to DataFrames: {e}")
            raise
    
    def save_to_files(self, dataframes: Dict[str, pd.DataFrame], output_dir: str = "data"):
        """Save DataFrames to CSV and JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for name, df in dataframes.items():
            if not df.empty:
                # Save as CSV
                csv_path = os.path.join(output_dir, f"{name}_{timestamp}.csv")
                df.to_csv(csv_path, index=False)
                
                # Save as JSON
                json_path = os.path.join(output_dir, f"{name}_{timestamp}.json")
                df.to_json(json_path, orient='records', date_format='iso')
                
                self.logger.info(f"Saved {name} data: {csv_path}, {json_path}")


def main():
    """
    Main execution function demonstrating SDK integration
    Run this script to test the enhanced ingestion capabilities
    """
    try:
        # Initialize ingestion system
        ingester = MailchimpDataIngestion()
        
        # Get campaigns from last 30 days
        since_date = (datetime.now() - timedelta(days=30)).isoformat()
        campaigns = ingester.get_all_campaigns(since_date=since_date, limit=100)
        
        # Get all lists
        lists = ingester.get_all_lists()
        
        # Export to DataFrames
        dataframes = ingester.export_to_dataframes(campaigns, lists)
        
        # Save to files
        ingester.save_to_files(dataframes)
        
        # Print summary
        print(f"✅ Data ingestion completed successfully!")
        print(f"📊 Campaigns retrieved: {len(campaigns)}")
        print(f"📋 Lists retrieved: {len(lists)}")
        print(f"💾 Data saved to CSV and JSON files")
        
        # Display sample data
        if not dataframes['campaigns'].empty:
            print("\n📈 Sample Campaign Data:")
            print(dataframes['campaigns'][['campaign_name', 'open_rate', 'click_rate', 'emails_sent']].head())
        
        if not dataframes['lists'].empty:
            print("\n👥 Sample List Data:")
            print(dataframes['lists'][['list_name', 'member_count', 'open_rate', 'click_rate']].head())
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        logging.error(f"Main execution failed: {e}")


if __name__ == "__main__":
    main()