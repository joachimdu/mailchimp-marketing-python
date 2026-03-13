"""
Enhanced Email Overview Dashboard Page
Demonstrates integration with Mailchimp Marketing SDK for advanced email analytics
Features: real-time metrics, trend analysis, cross-campaign comparison
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Any

# Import SDK and configuration
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import get_mailchimp_client, get_config_manager
from scripts.ingest_mailchimp import MailchimpDataIngestion


class EmailOverviewDashboard:
    """Enhanced Email Overview Dashboard with SDK integration"""
    
    def __init__(self):
        self.client = get_mailchimp_client()
        self.ingester = MailchimpDataIngestion()
        
        # Configure Streamlit page
        st.set_page_config(
            page_title="📧 Email Overview",
            page_icon="📧",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def load_data(self, days_back: int = 30) -> Dict[str, pd.DataFrame]:
        """Load enhanced campaign data using SDK"""
        try:
            with st.spinner("Loading campaign data from Mailchimp..."):
                # Get campaigns from specified time period
                since_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                campaigns = self.ingester.get_all_campaigns(since_date=since_date, limit=200)
                
                # Get lists data
                lists = self.ingester.get_all_lists()
                
                # Convert to DataFrames
                dataframes = self.ingester.export_to_dataframes(campaigns, lists)
                
            return dataframes
            
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return {'campaigns': pd.DataFrame(), 'lists': pd.DataFrame()}
    
    def render_kpi_metrics(self, df: pd.DataFrame):
        """Render enhanced KPI metrics with SDK data"""
        if df.empty:
            st.warning("No campaign data available")
            return
        
        # Calculate enhanced KPIs
        total_campaigns = len(df)
        total_emails_sent = df['emails_sent'].sum()
        avg_open_rate = df['open_rate'].mean()
        avg_click_rate = df['click_rate'].mean()
        total_revenue = df['revenue'].sum()
        avg_delivery_rate = df['delivery_rate'].mean()
        avg_complaint_rate = df['complaint_rate'].mean()
        
        # Create enhanced KPI layout
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📤 Total Campaigns",
                value=f"{total_campaigns:,}",
                delta=f"+{total_campaigns - max(total_campaigns - 5, 0)} this period"
            )
            st.metric(
                label="✉️ Emails Sent",
                value=f"{total_emails_sent:,}",
                delta=f"{(total_emails_sent / max(total_campaigns, 1)):,.0f} avg per campaign"
            )
        
        with col2:
            st.metric(
                label="📬 Avg Open Rate",
                value=f"{avg_open_rate:.1f}%",
                delta=f"{avg_open_rate - 21.3:.1f}% vs industry avg",
                delta_color="normal" if avg_open_rate >= 21.3 else "inverse"
            )
            st.metric(
                label="🖱️ Avg Click Rate", 
                value=f"{avg_click_rate:.1f}%",
                delta=f"{avg_click_rate - 2.6:.1f}% vs industry avg",
                delta_color="normal" if avg_click_rate >= 2.6 else "inverse"
            )
        
        with col3:
            st.metric(
                label="💰 Total Revenue",
                value=f"${total_revenue:,.2f}",
                delta=f"${total_revenue / max(total_campaigns, 1):,.2f} per campaign"
            )
            st.metric(
                label="📊 Delivery Rate",
                value=f"{avg_delivery_rate:.1f}%",
                delta=f"{avg_delivery_rate - 95:.1f}% vs target 95%",
                delta_color="normal" if avg_delivery_rate >= 95 else "inverse"
            )
        
        with col4:
            bounce_rate = df['bounce_rate'].mean()
            unsubscribe_rate = df['unsubscribe_rate'].mean()
            
            st.metric(
                label="⚠️ Avg Bounce Rate",
                value=f"{bounce_rate:.2f}%",
                delta=f"{bounce_rate - 2:.2f}% vs target <2%",
                delta_color="inverse" if bounce_rate >= 2 else "normal"
            )
            st.metric(
                label="📛 Complaint Rate",
                value=f"{avg_complaint_rate:.3f}%", 
                delta=f"{avg_complaint_rate - 0.1:.3f}% vs target <0.1%",
                delta_color="inverse" if avg_complaint_rate >= 0.1 else "normal"
            )
    
    def render_trend_analysis(self, df: pd.DataFrame):
        """Enhanced trend analysis with time-series data"""
        if df.empty:
            return
        
        st.subheader("📈 Campaign Performance Trends")
        
        # Prepare time-series data
        df_trends = df.copy()
        df_trends['send_date'] = pd.to_datetime(df_trends['send_time']).dt.date
        
        # Daily aggregations
        daily_metrics = df_trends.groupby('send_date').agg({
            'emails_sent': 'sum',
            'open_rate': 'mean',
            'click_rate': 'mean',
            'delivery_rate': 'mean',
            'revenue': 'sum',
            'campaign_id': 'count'
        }).reset_index()
        daily_metrics.rename(columns={'campaign_id': 'campaigns_sent'}, inplace=True)
        
        # Create subplots for comprehensive view
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('📊 Email Volume & Campaigns', '📬 Engagement Rates', 
                          '💰 Revenue Trend', '📋 Delivery Performance'),
            specs=[[{"secondary_y": True}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Email Volume & Campaign Count
        fig.add_trace(
            go.Scatter(x=daily_metrics['send_date'], y=daily_metrics['emails_sent'],
                      name='Emails Sent', line=dict(color='blue')),
            row=1, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=daily_metrics['send_date'], y=daily_metrics['campaigns_sent'],
                      name='Campaigns', line=dict(color='orange')),
            row=1, col=1, secondary_y=True
        )
        
        # Engagement Rates
        fig.add_trace(
            go.Scatter(x=daily_metrics['send_date'], y=daily_metrics['open_rate'],
                      name='Open Rate', line=dict(color='green')),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(x=daily_metrics['send_date'], y=daily_metrics['click_rate'],
                      name='Click Rate', line=dict(color='red')),
            row=1, col=2
        )
        
        # Revenue
        fig.add_trace(
            go.Scatter(x=daily_metrics['send_date'], y=daily_metrics['revenue'],
                      name='Revenue', line=dict(color='purple'), fill='tonexty'),
            row=2, col=1
        )
        
        # Delivery Performance
        fig.add_trace(
            go.Scatter(x=daily_metrics['send_date'], y=daily_metrics['delivery_rate'],
                      name='Delivery Rate', line=dict(color='teal')),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(height=600, showlegend=False, title_text="")
        fig.update_yaxes(title_text="Emails Sent", secondary_y=False, row=1, col=1)
        fig.update_yaxes(title_text="Campaigns", secondary_y=True, row=1, col=1)
        fig.update_yaxes(title_text="Rate (%)", row=1, col=2)
        fig.update_yaxes(title_text="Revenue ($)", row=2, col=1)
        fig.update_yaxes(title_text="Delivery Rate (%)", row=2, col=2)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_campaign_comparison(self, df: pd.DataFrame):
        """Enhanced campaign comparison with portfolio analytics"""
        if df.empty:
            return
        
        st.subheader("🔍 Campaign Performance Comparison")
        
        # Top performing campaigns
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🏆 Top Campaigns by Open Rate**")
            top_opens = df.nlargest(5, 'open_rate')[['campaign_name', 'open_rate', 'emails_sent']]
            for _, row in top_opens.iterrows():
                st.write(f"• {row['campaign_name'][:50]}... - {row['open_rate']:.1f}% ({row['emails_sent']:,} sent)")
        
        with col2:
            st.write("**🖱️ Top Campaigns by Click Rate**")
            top_clicks = df.nlargest(5, 'click_rate')[['campaign_name', 'click_rate', 'clicks_unique']]
            for _, row in top_clicks.iterrows():
                st.write(f"• {row['campaign_name'][:50]}... - {row['click_rate']:.1f}% ({row['clicks_unique']:,} clicks)")
        
        # Performance distribution
        fig_scatter = px.scatter(
            df, x='open_rate', y='click_rate', 
            size='emails_sent', color='revenue',
            hover_data=['campaign_name', 'send_time'],
            title="📊 Campaign Performance Matrix",
            labels={
                'open_rate': 'Open Rate (%)',
                'click_rate': 'Click Rate (%)',
                'revenue': 'Revenue ($)'
            }
        )
        
        # Add benchmark lines
        fig_scatter.add_hline(y=df['click_rate'].mean(), line_dash="dash", 
                             annotation_text="Avg Click Rate", line_color="red")
        fig_scatter.add_vline(x=df['open_rate'].mean(), line_dash="dash",
                             annotation_text="Avg Open Rate", line_color="green")
        
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    def render_advanced_analytics(self, df: pd.DataFrame):
        """Advanced analytics with benchmarking and insights"""
        if df.empty:
            return
        
        st.subheader("🎯 Advanced Analytics & Insights")
        
        # Performance benchmarking
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Engagement scoring
            df['engagement_score'] = (
                (df['open_rate'] * 0.4) + 
                (df['click_rate'] * 0.6) + 
                (df['delivery_rate'] * 0.2) - 
                (df['bounce_rate'] * 0.3)
            )
            
            top_performers = df.nlargest(10, 'engagement_score')
            
            fig_engagement = px.bar(
                top_performers, x='engagement_score', y='campaign_name',
                orientation='h', title="🏅 Top 10 by Engagement Score",
                labels={'engagement_score': 'Engagement Score', 'campaign_name': 'Campaign'}
            )
            fig_engagement.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_engagement, use_container_width=True)
        
        with col2:
            # Revenue per recipient analysis
            df['revenue_per_recipient'] = df['revenue'] / df['emails_sent'].replace(0, 1)
            
            fig_revenue = px.histogram(
                df, x='revenue_per_recipient', nbins=20,
                title="💰 Revenue per Recipient Distribution",
                labels={'revenue_per_recipient': 'Revenue per Recipient ($)'}
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col3:
            # Performance correlation heatmap
            correlation_cols = ['open_rate', 'click_rate', 'bounce_rate', 'unsubscribe_rate', 'revenue']
            correlation_matrix = df[correlation_cols].corr()
            
            fig_corr = px.imshow(
                correlation_matrix, 
                title="🔗 Metric Correlations",
                color_continuous_scale='RdBu_r',
                aspect='auto'
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        
        # Actionable insights
        st.write("**💡 Key Insights:**")
        
        best_day = df.groupby(df['send_time'].dt.day_name())['open_rate'].mean().idxmax()
        best_time = df.groupby(df['send_time'].dt.hour)['open_rate'].mean().idxmax()
        
        insights = [
            f"📅 Best performing day: {best_day}",
            f"🕐 Best performing hour: {best_time}:00",
            f"📊 Average engagement score: {df['engagement_score'].mean():.1f}",
            f"💰 Top revenue generator: {df.loc[df['revenue'].idxmax(), 'campaign_name'][:50]}...",
            f"🎯 Campaigns above average open rate: {(df['open_rate'] > df['open_rate'].mean()).sum()}/{len(df)}"
        ]
        
        for insight in insights:
            st.write(f"• {insight}")
    
    def render_sidebar_controls(self):
        """Render sidebar controls for filtering and configuration"""
        st.sidebar.header("📧 Email Overview Controls")
        
        # Date range selector
        days_back = st.sidebar.selectbox(
            "📅 Time Period",
            options=[7, 14, 30, 60, 90],
            index=2,  # Default to 30 days
            format_func=lambda x: f"Last {x} days"
        )
        
        # Refresh data button
        if st.sidebar.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.experimental_rerun()
        
        # Configuration display
        config_manager = get_config_manager()
        config_info = config_manager.get_config_info()
        
        st.sidebar.write("**⚙️ Configuration:**")
        st.sidebar.write(f"Server: {config_info.get('server', 'Not set')}")
        st.sidebar.write(f"API Key: {'✅ Configured' if config_info.get('api_key_configured') else '❌ Not set'}")
        
        return days_back
    
    def run(self):
        """Main dashboard execution"""
        st.title("📧 Email Marketing Overview")
        st.write("Enhanced email campaign analytics powered by Mailchimp Marketing SDK")
        
        # Sidebar controls
        days_back = self.render_sidebar_controls()
        
        # Load data
        dataframes = self.load_data(days_back)
        campaigns_df = dataframes.get('campaigns', pd.DataFrame())
        
        if not campaigns_df.empty:
            # Render dashboard sections
            self.render_kpi_metrics(campaigns_df)
            st.divider()
            
            self.render_trend_analysis(campaigns_df)
            st.divider()
            
            self.render_campaign_comparison(campaigns_df)
            st.divider()
            
            self.render_advanced_analytics(campaigns_df)
            
            # Export options
            with st.expander("💾 Export Data"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 Download CSV"):
                        csv = campaigns_df.to_csv(index=False)
                        st.download_button(
                            label="Download campaigns.csv",
                            data=csv,
                            file_name=f"mailchimp_campaigns_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("📊 Generate Report"):
                        st.info("Report generation functionality coming soon!")
        
        else:
            st.warning("No campaign data found for the selected time period.")
            st.info("Check your API configuration and ensure you have sent campaigns in the selected timeframe.")


# Streamlit app execution
def main():
    """Main function for standalone execution"""
    try:
        dashboard = EmailOverviewDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"Dashboard error: {e}")
        st.info("Please check your Mailchimp API configuration and try again.")


if __name__ == "__main__":
    main()