"""
Enhanced Campaign Details Dashboard Page  
Deep-dive analytics for individual campaigns using Mailchimp Marketing SDK
Features: click heatmaps, geographic analysis, subscriber tracking, A/B testing results
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Any, Optional

# Import SDK and configuration
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import get_mailchimp_client, get_config_manager
from scripts.ingest_mailchimp import MailchimpDataIngestion


class CampaignDetailsDashboard:
    """Enhanced Campaign Details Dashboard with deep analytics"""
    
    def __init__(self):
        self.client = get_mailchimp_client()
        self.ingester = MailchimpDataIngestion()
        
        # Configure Streamlit page
        st.set_page_config(
            page_title="📊 Campaign Details",
            page_icon="📊", 
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def get_campaign_list(self) -> Dict[str, str]:
        """Get list of recent campaigns for selection"""
        try:
            # Get recent campaigns
            response = self.client.campaigns.list(count=50, status='sent')
            campaigns = {}
            
            for campaign in response.get('campaigns', []):
                campaign_name = campaign.get('settings', {}).get('title', f"Campaign {campaign['id']}")
                send_time = campaign.get('send_time', '')
                if send_time:
                    send_date = pd.to_datetime(send_time).strftime('%Y-%m-%d')
                    display_name = f"{campaign_name} ({send_date})"
                else:
                    display_name = campaign_name
                
                campaigns[campaign['id']] = display_name
                
            return campaigns
            
        except Exception as e:
            st.error(f"Error loading campaigns: {e}")
            return {}
    
    def load_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """Load comprehensive campaign details using SDK"""
        try:
            with st.spinner("Loading detailed campaign analytics..."):
                # Basic campaign info
                campaign = self.client.campaigns.get(campaign_id)
                
                # Detailed report
                report = self.client.reports.get_campaign_report(campaign_id)
                
                # Enhanced analytics
                enhanced_data = {}
                
                # Click details and heatmap data
                try:
                    click_details = self.client.reports.get_campaign_click_details(campaign_id)
                    enhanced_data['click_details'] = click_details
                except:
                    enhanced_data['click_details'] = None
                
                # Geographic performance
                try:
                    locations = self.client.reports.get_locations_for_campaign(campaign_id)
                    enhanced_data['locations'] = locations
                except:
                    enhanced_data['locations'] = None
                
                # Email activity tracking (sample)
                try:
                    email_activity = self.client.reports.get_email_activity_for_campaign(
                        campaign_id, count=500
                    )
                    enhanced_data['email_activity'] = email_activity
                except:
                    enhanced_data['email_activity'] = None
                
                # Domain performance
                try:
                    domain_performance = self.client.reports.get_domain_performance_for_campaign(campaign_id)
                    enhanced_data['domain_performance'] = domain_performance
                except:
                    enhanced_data['domain_performance'] = None
                
                # A/B testing data if available
                try:
                    if campaign.get('variate_settings'):
                        # This is an A/B test campaign
                        enhanced_data['ab_test'] = campaign['variate_settings']
                    else:
                        enhanced_data['ab_test'] = None
                except:
                    enhanced_data['ab_test'] = None
                
                return {
                    'campaign': campaign,
                    'report': report,
                    'enhanced': enhanced_data
                }
                
        except Exception as e:
            st.error(f"Error loading campaign details: {e}")
            return {}
    
    def render_campaign_overview(self, data: Dict[str, Any]):
        """Render campaign overview with key metrics"""
        if not data:
            return
        
        campaign = data['campaign']
        report = data['report']
        
        # Campaign header
        st.title(f"📊 {campaign.get('settings', {}).get('title', 'Campaign Details')}")
        
        # Basic campaign info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**📧 Campaign Info:**")
            st.write(f"• Subject: {campaign.get('settings', {}).get('subject_line', 'N/A')}")
            st.write(f"• From: {campaign.get('settings', {}).get('from_name', 'N/A')}")
            st.write(f"• Send Time: {campaign.get('send_time', 'N/A')}")
            st.write(f"• Status: {campaign.get('status', 'N/A')}")
        
        with col2:
            st.write(f"**📨 Delivery Metrics:**")
            st.write(f"• Emails Sent: {report.get('emails_sent', 0):,}")
            st.write(f"• Delivered: {report.get('emails_sent', 0) - report.get('bounces', {}).get('hard_bounces', 0) - report.get('bounces', {}).get('soft_bounces', 0):,}")
            st.write(f"• Delivery Rate: {report.get('delivery_status', {}).get('delivery_rate', 0) * 100:.1f}%")
            st.write(f"• Bounces: {report.get('bounces', {}).get('hard_bounces', 0) + report.get('bounces', {}).get('soft_bounces', 0):,}")
        
        with col3:
            st.write("**📈 Engagement:**")
            st.write(f"• Opens: {report.get('opens', {}).get('unique_opens', 0):,} ({report.get('opens', {}).get('open_rate', 0) * 100:.1f}%)")
            st.write(f"• Clicks: {report.get('clicks', {}).get('unique_clicks', 0):,} ({report.get('clicks', {}).get('click_rate', 0) * 100:.1f}%)")
            st.write(f"• Unsubscribes: {report.get('unsubscribed', {}).get('unsubscribes', 0):,}")
            st.write(f"• Revenue: ${report.get('ecommerce', {}).get('total_revenue', 0):,.2f}")
        
        # Performance indicators
        st.subheader("🎯 Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            open_rate = report.get('opens', {}).get('open_rate', 0) * 100
            st.metric(
                "📬 Open Rate",
                f"{open_rate:.1f}%",
                delta=f"{open_rate - 21.3:.1f}% vs industry avg",
                delta_color="normal" if open_rate >= 21.3 else "inverse"
            )
        
        with col2:
            click_rate = report.get('clicks', {}).get('click_rate', 0) * 100
            st.metric(
                "🖱️ Click Rate", 
                f"{click_rate:.1f}%",
                delta=f"{click_rate - 2.6:.1f}% vs industry avg",
                delta_color="normal" if click_rate >= 2.6 else "inverse"
            )
        
        with col3:
            unsubscribe_rate = report.get('unsubscribed', {}).get('unsubscribe_rate', 0) * 100
            st.metric(
                "📛 Unsubscribe Rate",
                f"{unsubscribe_rate:.2f}%",
                delta=f"{unsubscribe_rate - 0.2:.2f}% vs target <0.2%",
                delta_color="inverse" if unsubscribe_rate >= 0.2 else "normal"
            )
        
        with col4:
            if report.get('ecommerce', {}).get('total_revenue', 0) > 0:
                revenue_per_recipient = report['ecommerce']['total_revenue'] / max(report.get('emails_sent', 1), 1)
                st.metric(
                    "💰 Revenue per Recipient",
                    f"${revenue_per_recipient:.2f}",
                    delta=f"${revenue_per_recipient - 1:.2f} vs target $1.00",
                    delta_color="normal" if revenue_per_recipient >= 1 else "inverse"
                )
            else:
                st.metric("💰 Revenue per Recipient", "$0.00")
    
    def render_click_heatmap(self, data: Dict[str, Any]):
        """Render click heatmap and link performance analysis"""
        enhanced = data.get('enhanced', {})
        click_details = enhanced.get('click_details')
        
        if not click_details or not click_details.get('urls_clicked'):
            st.warning("No click data available for this campaign")
            return
        
        st.subheader("🔥 Click Heatmap Analysis")
        
        # Process click data
        urls_data = []
        for url_data in click_details['urls_clicked']:
            urls_data.append({
                'url': url_data.get('url', 'Unknown')[:50] + '...' if len(url_data.get('url', '')) > 50 else url_data.get('url', 'Unknown'),
                'total_clicks': url_data.get('total_clicks', 0),
                'unique_clicks': url_data.get('unique_clicks', 0),
                'click_percentage': url_data.get('click_percentage', 0) * 100,
                'url_id': url_data.get('id', '')
            })
        
        if urls_data:
            df_clicks = pd.DataFrame(urls_data)
            
            # Top performing links
            col1, col2 = st.columns(2)
            
            with col1:
                # Bar chart of link performance
                fig_links = px.bar(
                    df_clicks.head(10), 
                    x='unique_clicks', 
                    y='url',
                    orientation='h',
                    title="🔗 Top 10 Links by Unique Clicks",
                    labels={'unique_clicks': 'Unique Clicks', 'url': 'Link URL'}
                )
                fig_links.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_links, use_container_width=True)
            
            with col2:
                # Click distribution pie chart
                fig_pie = px.pie(
                    df_clicks.head(8), 
                    values='total_clicks', 
                    names='url',
                    title="📊 Click Distribution by Link"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Detailed click table
            st.write("**📋 Detailed Link Performance:**")
            st.dataframe(
                df_clicks[['url', 'total_clicks', 'unique_clicks', 'click_percentage']],
                use_container_width=True
            )
    
    def render_geographic_analysis(self, data: Dict[str, Any]):
        """Render geographic performance analysis"""
        enhanced = data.get('enhanced', {})
        locations = enhanced.get('locations')
        
        if not locations or not locations.get('countries'):
            st.warning("No geographic data available for this campaign") 
            return
        
        st.subheader("🌍 Geographic Performance Analysis")
        
        # Process location data
        countries_data = []
        for country in locations['countries']:
            countries_data.append({
                'country': country.get('country', 'Unknown'),
                'total_opens': country.get('opens', 0),
                'total_clicks': country.get('clicks', 0),
                'open_rate': country.get('open_rate', 0) * 100,
                'click_rate': country.get('click_rate', 0) * 100
            })
        
        if countries_data:
            df_geo = pd.DataFrame(countries_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Geographic distribution map (choropleth)
                fig_map = px.choropleth(
                    df_geo,
                    locations='country',
                    color='total_opens',
                    hover_data=['total_clicks', 'open_rate', 'click_rate'],
                    title="🗺️ Opens by Country",
                    color_continuous_scale='Blues',
                    locationmode='country names'
                )
                st.plotly_chart(fig_map, use_container_width=True)
            
            with col2:
                # Top countries by engagement
                fig_bar_geo = px.bar(
                    df_geo.head(10),
                    x='country',
                    y='total_opens', 
                    color='open_rate',
                    title="📈 Top 10 Countries by Opens",
                    labels={'total_opens': 'Total Opens', 'country': 'Country', 'open_rate': 'Open Rate (%)'}
                )
                fig_bar_geo.update_xaxes(tickangle=45)
                st.plotly_chart(fig_bar_geo, use_container_width=True)
            
            # Geographic performance table
            st.write("**🌎 Geographic Performance Summary:**")
            st.dataframe(
                df_geo.head(15)[['country', 'total_opens', 'total_clicks', 'open_rate', 'click_rate']],
                use_container_width=True
            )
    
    def render_subscriber_activity(self, data: Dict[str, Any]):
        """Render subscriber activity and engagement timeline"""
        enhanced = data.get('enhanced', {})
        email_activity = enhanced.get('email_activity')
        
        if not email_activity or not email_activity.get('emails'):
            st.warning("No subscriber activity data available")
            return
        
        st.subheader("👥 Subscriber Activity Timeline")
        
        # Process email activity data
        activities = []
        for email in email_activity['emails'][:100]:  # Limit to first 100 for performance
            for activity in email.get('activity', []):
                activities.append({
                    'email': email.get('email_address', 'Unknown'),
                    'action': activity.get('action', 'unknown'),
                    'timestamp': activity.get('timestamp', ''),
                    'ip': activity.get('ip', ''),
                    'url': activity.get('url', '') if activity.get('action') == 'click' else ''
                })
        
        if activities:
            df_activity = pd.DataFrame(activities)
            df_activity['timestamp'] = pd.to_datetime(df_activity['timestamp'])
            
            # Activity timeline
            activity_counts = df_activity.groupby([
                df_activity['timestamp'].dt.floor('H'), 'action'
            ]).size().reset_index()
            activity_counts.columns = ['hour', 'action', 'count']
            
            fig_timeline = px.line(
                activity_counts,
                x='hour',
                y='count',
                color='action',
                title="⏰ Activity Timeline by Hour",
                labels={'hour': 'Hour', 'count': 'Activity Count', 'action': 'Action Type'}
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Activity summary
            col1, col2 = st.columns(2)
            
            with col1:
                action_summary = df_activity['action'].value_counts()
                fig_actions = px.bar(
                    x=action_summary.values,
                    y=action_summary.index,
                    orientation='h',
                    title="📊 Activity Types Distribution",
                    labels={'x': 'Count', 'y': 'Activity Type'}
                )
                st.plotly_chart(fig_actions, use_container_width=True)
            
            with col2:
                # Top active subscribers
                top_subscribers = df_activity['email'].value_counts().head(10)
                st.write("**🏆 Most Active Subscribers:**")
                for i, (email, count) in enumerate(top_subscribers.items(), 1):
                    st.write(f"{i}. {email} ({count} activities)")
    
    def render_ab_test_results(self, data: Dict[str, Any]):
        """Render A/B testing results if available"""
        enhanced = data.get('enhanced', {})
        ab_test = enhanced.get('ab_test')
        
        if not ab_test:
            st.info("This campaign was not an A/B test")
            return
        
        st.subheader("🔬 A/B Test Results")
        
        # Display A/B test configuration
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🧪 Test Configuration:**")
            st.write(f"• Test Type: {ab_test.get('test_type', 'Unknown')}")
            st.write(f"• Winner Criteria: {ab_test.get('winner_criteria', 'Unknown')}")
            st.write(f"• Test Size: {ab_test.get('test_size', 0)}%")
            st.write(f"• Wait Time: {ab_test.get('wait_time', 0)} hours")
        
        with col2:
            if ab_test.get('combinations'):
                st.write("**📊 Test Variations:**")
                for i, combo in enumerate(ab_test['combinations'][:2]):
                    st.write(f"• Variation {i+1}: {combo.get('subject_line', 'N/A')}")
        
        # If we have results data, show performance comparison
        # Note: This would require additional API calls to get variation-specific results
        st.info("Detailed A/B test performance comparison requires additional implementation")
    
    def render_domain_performance(self, data: Dict[str, Any]):
        """Render domain-specific performance analysis"""
        enhanced = data.get('enhanced', {})
        domain_performance = enhanced.get('domain_performance')
        
        if not domain_performance or not domain_performance.get('domains'):
            st.warning("No domain performance data available")
            return
        
        st.subheader("🌐 Domain Performance Analysis")
        
        # Process domain data
        domains_data = []
        for domain in domain_performance['domains']:
            domains_data.append({
                'domain': domain.get('domain', 'Unknown'),
                'emails_sent': domain.get('emails_sent', 0),
                'bounces': domain.get('bounces', 0),
                'opens': domain.get('opens', 0),
                'clicks': domain.get('clicks', 0),
                'bounce_rate': (domain.get('bounces', 0) / max(domain.get('emails_sent', 1), 1)) * 100,
                'open_rate': (domain.get('opens', 0) / max(domain.get('emails_sent', 1), 1)) * 100,
                'click_rate': (domain.get('clicks', 0) / max(domain.get('emails_sent', 1), 1)) * 100
            })
        
        if domains_data:
            df_domains = pd.DataFrame(domains_data)
            
            # Domain performance comparison
            fig_domains = make_subplots(
                rows=1, cols=2,
                subplot_titles=['📧 Emails Sent by Domain', '📊 Engagement by Domain']
            )
            
            # Emails sent
            fig_domains.add_trace(
                go.Bar(x=df_domains['domain'], y=df_domains['emails_sent'], name='Emails Sent'),
                row=1, col=1
            )
            
            # Engagement rates
            fig_domains.add_trace(
                go.Scatter(x=df_domains['domain'], y=df_domains['open_rate'], 
                          mode='markers', name='Open Rate', marker=dict(size=10)),
                row=1, col=2
            )
            fig_domains.add_trace(
                go.Scatter(x=df_domains['domain'], y=df_domains['click_rate'],
                          mode='markers', name='Click Rate', marker=dict(size=10)),
                row=1, col=2
            )
            
            fig_domains.update_layout(height=400)
            st.plotly_chart(fig_domains, use_container_width=True)
            
            # Domain performance table
            st.write("**📋 Domain Performance Summary:**")
            st.dataframe(
                df_domains[['domain', 'emails_sent', 'bounce_rate', 'open_rate', 'click_rate']],
                use_container_width=True
            )
    
    def render_sidebar_controls(self):
        """Render sidebar controls for campaign selection"""
        st.sidebar.header("📊 Campaign Details")
        
        # Campaign selection
        campaigns = self.get_campaign_list()
        
        if campaigns:
            selected_campaign = st.sidebar.selectbox(
                "📋 Select Campaign",
                options=list(campaigns.keys()),
                format_func=lambda x: campaigns[x]
            )
        else:
            st.sidebar.warning("No campaigns found")
            selected_campaign = None
        
        # Refresh button
        if st.sidebar.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.experimental_rerun()
        
        # Configuration display
        config_manager = get_config_manager()
        config_info = config_manager.get_config_info()
        
        st.sidebar.write("**⚙️ Configuration:**")
        st.sidebar.write(f"Server: {config_info.get('server', 'Not set')}")
        st.sidebar.write(f"API Key: {'✅ Configured' if config_info.get('api_key_configured') else '❌ Not set'}")
        
        return selected_campaign
    
    def run(self):
        """Main dashboard execution"""
        st.title("📊 Campaign Details Dashboard")
        st.write("Deep-dive analytics for individual email campaigns")
        
        # Sidebar controls
        selected_campaign = self.render_sidebar_controls()
        
        if not selected_campaign:
            st.warning("Please select a campaign from the sidebar to view details.")
            return
        
        # Load campaign data
        campaign_data = self.load_campaign_details(selected_campaign)
        
        if campaign_data:
            # Render dashboard sections
            self.render_campaign_overview(campaign_data)
            st.divider()
            
            self.render_click_heatmap(campaign_data)
            st.divider()
            
            self.render_geographic_analysis(campaign_data)
            st.divider()
            
            self.render_subscriber_activity(campaign_data)
            st.divider()
            
            self.render_ab_test_results(campaign_data)
            st.divider()
            
            self.render_domain_performance(campaign_data)
            
        else:
            st.error("Failed to load campaign details. Please try again or select a different campaign.")


# Streamlit app execution
def main():
    """Main function for standalone execution"""
    try:
        dashboard = CampaignDetailsDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"Dashboard error: {e}")
        st.info("Please check your Mailchimp API configuration and try again.")


if __name__ == "__main__":
    main()