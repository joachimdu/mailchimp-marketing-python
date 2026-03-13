"""
Enhanced Email Audience Dashboard Page
Advanced audience analytics and segmentation using Mailchimp Marketing SDK
Features: subscriber lifecycle, engagement scoring, list health, growth attribution
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


class EmailAudienceDashboard:
    """Enhanced Email Audience Dashboard with advanced segmentation"""
    
    def __init__(self):
        self.client = get_mailchimp_client()
        self.ingester = MailchimpDataIngestion()
        
        # Configure Streamlit page
        st.set_page_config(
            page_title="👥 Email Audience",
            page_icon="👥",
            layout="wide", 
            initial_sidebar_state="expanded"
        )
    
    def load_audience_data(self) -> Dict[str, Any]:
        """Load comprehensive audience data using SDK"""
        try:
            with st.spinner("Loading audience analytics from Mailchimp..."):
                # Get all lists
                lists_response = self.client.lists.get_all_lists(count=100)
                lists_data = []
                members_data = []
                growth_data = []
                
                for list_item in lists_response.get('lists', []):
                    list_id = list_item['id']
                    
                    # Basic list data
                    list_stats = list_item.get('stats', {})
                    lists_data.append({
                        'list_id': list_id,
                        'list_name': list_item.get('name', 'Unknown'),
                        'member_count': list_stats.get('member_count', 0),
                        'unsubscribe_count': list_stats.get('unsubscribe_count', 0),
                        'cleaned_count': list_stats.get('cleaned_count', 0),
                        'open_rate': list_stats.get('open_rate', 0) * 100,
                        'click_rate': list_stats.get('click_rate', 0) * 100,
                        'date_created': list_item.get('date_created', ''),
                        'avg_sub_rate': list_stats.get('avg_sub_rate', 0),
                        'avg_unsub_rate': list_stats.get('avg_unsub_rate', 0)
                    })
                    
                    # Get growth history
                    try:
                        growth_response = self.client.lists.get_list_growth_history(list_id)
                        for growth_point in growth_response.get('history', [])[-12:]:  # Last 12 months
                            growth_data.append({
                                'list_id': list_id,
                                'list_name': list_item.get('name', 'Unknown'),
                                'month': growth_point.get('month', ''),
                                'existing': growth_point.get('existing', 0),
                                'imports': growth_point.get('imports', 0),
                                'optins': growth_point.get('optins', 0)
                            })
                    except:
                        continue  # Skip if growth data not available
                    
                    # Get member sample for engagement analysis
                    try:
                        members_response = self.client.lists.get_list_members_info(list_id, count=100)
                        for member in members_response.get('members', []):
                            members_data.append({
                                'list_id': list_id,
                                'list_name': list_item.get('name', 'Unknown'),
                                'email': member.get('email_address', ''),
                                'status': member.get('status', ''),
                                'member_rating': member.get('member_rating', 0),
                                'timestamp_signup': member.get('timestamp_signup', ''),
                                'timestamp_opt': member.get('timestamp_opt', ''),
                                'last_changed': member.get('last_changed', ''),
                                'avg_open_rate': member.get('stats', {}).get('avg_open_rate', 0) * 100,
                                'avg_click_rate': member.get('stats', {}).get('avg_click_rate', 0) * 100
                            })
                    except:
                        continue  # Skip if members data not available
                
                return {
                    'lists': pd.DataFrame(lists_data),
                    'members': pd.DataFrame(members_data),
                    'growth': pd.DataFrame(growth_data)
                }
                
        except Exception as e:
            st.error(f"Error loading audience data: {e}")
            return {
                'lists': pd.DataFrame(),
                'members': pd.DataFrame(), 
                'growth': pd.DataFrame()
            }
    
    def load_list_segments(self, list_id: str) -> List[Dict[str, Any]]:
        """Load segments for a specific list"""
        try:
            segments_response = self.client.lists.list_segments(list_id)
            segments_data = []
            
            for segment in segments_response.get('segments', []):
                segments_data.append({
                    'segment_id': segment.get('id', ''),
                    'name': segment.get('name', ''),
                    'member_count': segment.get('member_count', 0),
                    'type': segment.get('type', ''),
                    'created_at': segment.get('created_at', ''),
                    'updated_at': segment.get('updated_at', '')
                })
            
            return segments_data
            
        except Exception as e:
            st.warning(f"Could not load segments for list {list_id}: {e}")
            return []
    
    def render_audience_overview(self, data: Dict[str, pd.DataFrame]):
        """Render audience overview with key metrics"""
        lists_df = data.get('lists', pd.DataFrame())
        members_df = data.get('members', pd.DataFrame())
        
        if lists_df.empty:
            st.warning("No audience data available")
            return
        
        st.subheader("👥 Audience Overview")
        
        # Calculate aggregate metrics
        total_subscribers = lists_df['member_count'].sum()
        total_unsubscribes = lists_df['unsubscribe_count'].sum() 
        total_cleaned = lists_df['cleaned_count'].sum()
        avg_open_rate = lists_df['open_rate'].mean()
        avg_click_rate = lists_df['click_rate'].mean()
        total_lists = len(lists_df)
        
        # KPI metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="👥 Total Subscribers",
                value=f"{total_subscribers:,}",
                delta=f"{total_lists} lists"
            )
            st.metric(
                label="📈 Avg Growth Rate",
                value=f"{lists_df['avg_sub_rate'].mean():.1f}%",
                delta=f"vs {lists_df['avg_unsub_rate'].mean():.1f}% churn"
            )
        
        with col2:
            churn_rate = (total_unsubscribes / max(total_subscribers, 1)) * 100
            st.metric(
                label="📉 Churn Rate", 
                value=f"{churn_rate:.1f}%",
                delta=f"{total_unsubscribes:,} unsubscribes",
                delta_color="inverse"
            )
            st.metric(
                label="🧹 Cleaned Rate",
                value=f"{(total_cleaned / max(total_subscribers, 1)) * 100:.1f}%",
                delta=f"{total_cleaned:,} cleaned"
            )
        
        with col3:
            st.metric(
                label="📬 Avg Open Rate",
                value=f"{avg_open_rate:.1f}%",
                delta=f"{avg_open_rate - 21.3:.1f}% vs industry",
                delta_color="normal" if avg_open_rate >= 21.3 else "inverse"
            )
            st.metric(
                label="🖱️ Avg Click Rate",
                value=f"{avg_click_rate:.1f}%", 
                delta=f"{avg_click_rate - 2.6:.1f}% vs industry",
                delta_color="normal" if avg_click_rate >= 2.6 else "inverse"
            )
        
        with col4:
            if not members_df.empty:
                high_rating = len(members_df[members_df['member_rating'] >= 4])
                engagement_score = (high_rating / len(members_df)) * 100
                st.metric(
                    label="⭐ High Engagement",
                    value=f"{engagement_score:.1f}%",
                    delta=f"{high_rating:,} highly rated"
                )
                
                active_members = len(members_df[members_df['avg_open_rate'] > 0])
                activity_rate = (active_members / len(members_df)) * 100
                st.metric(
                    label="🔥 Activity Rate",
                    value=f"{activity_rate:.1f}%",
                    delta=f"{active_members:,} active"
                )
            else:
                st.metric("⭐ High Engagement", "N/A")
                st.metric("🔥 Activity Rate", "N/A")
    
    def render_list_performance(self, data: Dict[str, pd.DataFrame]):
        """Render individual list performance analysis"""
        lists_df = data.get('lists', pd.DataFrame())
        
        if lists_df.empty:
            return
        
        st.subheader("📋 List Performance Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # List size comparison
            fig_size = px.bar(
                lists_df.head(10),
                x='list_name',
                y='member_count',
                color='open_rate',
                title="📊 List Size & Open Rate Performance",
                labels={'member_count': 'Subscribers', 'list_name': 'List Name', 'open_rate': 'Open Rate (%)'}
            )
            fig_size.update_xaxes(tickangle=45)
            st.plotly_chart(fig_size, use_container_width=True)
        
        with col2:
            # Engagement scatter plot
            fig_engagement = px.scatter(
                lists_df,
                x='open_rate',
                y='click_rate',
                size='member_count',
                hover_data=['list_name', 'avg_sub_rate', 'avg_unsub_rate'],
                title="📈 List Engagement Matrix",
                labels={'open_rate': 'Open Rate (%)', 'click_rate': 'Click Rate (%)', 'member_count': 'Subscribers'}
            )
            
            # Add benchmark lines
            fig_engagement.add_hline(y=lists_df['click_rate'].mean(), line_dash="dash", 
                                   annotation_text="Avg Click Rate", line_color="red")
            fig_engagement.add_vline(x=lists_df['open_rate'].mean(), line_dash="dash",
                                   annotation_text="Avg Open Rate", line_color="green")
            
            st.plotly_chart(fig_engagement, use_container_width=True)
        
        # List health indicators
        st.write("**🏥 List Health Indicators:**")
        
        # Calculate health scores
        lists_df['health_score'] = (
            (lists_df['open_rate'] * 0.4) + 
            (lists_df['click_rate'] * 0.3) +
            (lists_df['avg_sub_rate'] * 0.2) -
            (lists_df['avg_unsub_rate'] * 0.1)
        )
        
        # Display top and bottom performers
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**🏆 Top Performers:**")
            top_lists = lists_df.nlargest(5, 'health_score')[['list_name', 'health_score', 'member_count']]
            for _, row in top_lists.iterrows():
                st.write(f"• {row['list_name'][:30]}... - Score: {row['health_score']:.1f}")
        
        with col2:
            st.write("**⚠️ Needs Attention:**")
            bottom_lists = lists_df.nsmallest(5, 'health_score')[['list_name', 'health_score', 'member_count']]
            for _, row in bottom_lists.iterrows():
                st.write(f"• {row['list_name'][:30]}... - Score: {row['health_score']:.1f}")
        
        with col3:
            st.write("**📊 List Stats:**")
            st.write(f"• Avg Health Score: {lists_df['health_score'].mean():.1f}")
            st.write(f"• Best Performer: {lists_df.loc[lists_df['health_score'].idxmax(), 'list_name'][:30]}...")
            st.write(f"• Largest List: {lists_df.loc[lists_df['member_count'].idxmax(), 'list_name'][:30]}...")
    
    def render_growth_analysis(self, data: Dict[str, pd.DataFrame]):
        """Render audience growth and attribution analysis"""
        growth_df = data.get('growth', pd.DataFrame())
        
        if growth_df.empty:
            st.warning("No growth data available")
            return
        
        st.subheader("📈 Growth Analysis & Attribution")
        
        # Convert month to datetime for better plotting
        growth_df['month_date'] = pd.to_datetime(growth_df['month'])
        
        # Aggregate growth data by month
        monthly_growth = growth_df.groupby('month_date').agg({
            'existing': 'sum',
            'imports': 'sum', 
            'optins': 'sum'
        }).reset_index()
        
        # Calculate net growth
        monthly_growth['net_growth'] = monthly_growth['imports'] + monthly_growth['optins']
        monthly_growth['total_growth'] = monthly_growth['net_growth'] + monthly_growth['existing']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Growth trend over time
            fig_growth = go.Figure()
            
            fig_growth.add_trace(go.Scatter(
                x=monthly_growth['month_date'],
                y=monthly_growth['existing'],
                mode='lines+markers',
                name='Existing',
                fill='tonexty'
            ))
            
            fig_growth.add_trace(go.Scatter(
                x=monthly_growth['month_date'], 
                y=monthly_growth['optins'],
                mode='lines+markers',
                name='Opt-ins',
                fill='tonexty'
            ))
            
            fig_growth.add_trace(go.Scatter(
                x=monthly_growth['month_date'],
                y=monthly_growth['imports'], 
                mode='lines+markers',
                name='Imports',
                fill='tonexty'
            ))
            
            fig_growth.update_layout(
                title="📊 Monthly Growth Breakdown",
                xaxis_title="Month",
                yaxis_title="Subscribers",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_growth, use_container_width=True)
        
        with col2:
            # Growth source attribution
            total_optins = growth_df['optins'].sum()
            total_imports = growth_df['imports'].sum()
            
            attribution_data = pd.DataFrame({
                'source': ['Organic Opt-ins', 'Manual Imports'],
                'count': [total_optins, total_imports]
            })
            
            fig_attribution = px.pie(
                attribution_data,
                values='count',
                names='source',
                title="🎯 Growth Source Attribution"
            )
            st.plotly_chart(fig_attribution, use_container_width=True)
        
        # Growth insights
        st.write("**💡 Growth Insights:**")
        
        recent_growth = monthly_growth.tail(3)['net_growth'].mean()
        previous_growth = monthly_growth.head(3)['net_growth'].mean()
        growth_trend = ((recent_growth - previous_growth) / max(previous_growth, 1)) * 100
        
        insights = [
            f"📊 Recent growth rate: {recent_growth:.0f} subscribers/month",
            f"📈 Growth trend: {growth_trend:+.1f}% vs earlier period",
            f"🎯 Primary growth source: {'Organic opt-ins' if total_optins > total_imports else 'Manual imports'}",
            f"📅 Best growth month: {monthly_growth.loc[monthly_growth['net_growth'].idxmax(), 'month_date'].strftime('%B %Y')}",
            f"📋 Total new subscribers: {total_optins + total_imports:,}"
        ]
        
        for insight in insights:
            st.write(f"• {insight}")
    
    def render_engagement_scoring(self, data: Dict[str, pd.DataFrame]):
        """Render subscriber engagement scoring and lifecycle analysis"""
        members_df = data.get('members', pd.DataFrame())
        
        if members_df.empty:
            st.warning("No member data available for engagement analysis")
            return
        
        st.subheader("⭐ Engagement Scoring & Lifecycle")
        
        # Calculate enhanced engagement scores
        members_df['engagement_score'] = (
            (members_df['member_rating'] * 20) +  # Mailchimp rating (0-5) -> 0-100
            (members_df['avg_open_rate'] * 0.5) +   # Open rate contribution
            (members_df['avg_click_rate'] * 1.5)    # Click rate contribution (higher weight)
        )
        
        # Categorize subscribers
        def categorize_engagement(score):
            if score >= 80:
                return "🔥 Super Engaged"
            elif score >= 60:
                return "👍 Engaged"
            elif score >= 40:
                return "😐 Moderate"
            elif score >= 20:
                return "😴 Low"
            else:
                return "💀 Inactive"
        
        members_df['engagement_category'] = members_df['engagement_score'].apply(categorize_engagement)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Engagement distribution
            engagement_dist = members_df['engagement_category'].value_counts()
            
            fig_engagement = px.bar(
                x=engagement_dist.values,
                y=engagement_dist.index,
                orientation='h',
                title="👥 Subscriber Engagement Distribution",
                labels={'x': 'Subscribers', 'y': 'Engagement Level'}
            )
            fig_engagement.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_engagement, use_container_width=True)
        
        with col2:
            # Engagement score distribution
            fig_score_dist = px.histogram(
                members_df,
                x='engagement_score',
                nbins=20,
                title="📊 Engagement Score Distribution",
                labels={'engagement_score': 'Engagement Score (0-100)'}
            )
            st.plotly_chart(fig_score_dist, use_container_width=True)
        
        # Lifecycle analysis
        if 'timestamp_signup' in members_df.columns and members_df['timestamp_signup'].notna().any():
            st.write("**📅 Subscriber Lifecycle Analysis:**")
            
            members_df['signup_date'] = pd.to_datetime(members_df['timestamp_signup'])
            members_df['days_subscribed'] = (datetime.now() - members_df['signup_date']).dt.days
            
            # Lifecycle stages
            def get_lifecycle_stage(days):
                if days <= 30:
                    return "🌱 New (0-30 days)"
                elif days <= 90:
                    return "🌿 Growing (30-90 days)"
                elif days <= 365:
                    return "🌳 Mature (90-365 days)"
                else:
                    return "🦴 Veteran (365+ days)"
            
            members_df['lifecycle_stage'] = members_df['days_subscribed'].apply(get_lifecycle_stage)
            
            lifecycle_engagement = members_df.groupby('lifecycle_stage').agg({
                'engagement_score': 'mean',
                'avg_open_rate': 'mean',
                'avg_click_rate': 'mean',
                'email': 'count'
            }).reset_index()
            lifecycle_engagement.rename(columns={'email': 'subscriber_count'}, inplace=True)
            
            fig_lifecycle = px.bar(
                lifecycle_engagement,
                x='lifecycle_stage',
                y='engagement_score',
                color='subscriber_count',
                title="🌱 Engagement by Lifecycle Stage",
                labels={'engagement_score': 'Avg Engagement Score', 'lifecycle_stage': 'Lifecycle Stage'}
            )
            st.plotly_chart(fig_lifecycle, use_container_width=True)
        
        # Engagement insights
        st.write("**💡 Engagement Insights:**")
        
        high_engagement = len(members_df[members_df['engagement_score'] >= 60])
        low_engagement = len(members_df[members_df['engagement_score'] < 20])
        avg_score = members_df['engagement_score'].mean()
        
        insights = [
            f"⭐ Average engagement score: {avg_score:.1f}/100",
            f"🔥 High engagement subscribers: {high_engagement:,} ({(high_engagement/len(members_df))*100:.1f}%)",
            f"💀 At-risk subscribers: {low_engagement:,} ({(low_engagement/len(members_df))*100:.1f}%)",
            f"🎯 Top engagement category: {members_df['engagement_category'].value_counts().index[0]}",
            f"📈 Re-engagement opportunity: {low_engagement:,} subscribers"
        ]
        
        for insight in insights:
            st.write(f"• {insight}")
    
    def render_segmentation_analysis(self, data: Dict[str, pd.DataFrame]):
        """Render advanced segmentation and targeting recommendations"""
        lists_df = data.get('lists', pd.DataFrame())
        
        if lists_df.empty:
            return
        
        st.subheader("🎯 Segmentation & Targeting")
        
        # Select a list for detailed segmentation
        selected_list = st.selectbox(
            "📋 Select List for Segmentation Analysis",
            options=lists_df['list_id'].tolist(),
            format_func=lambda x: lists_df[lists_df['list_id'] == x]['list_name'].iloc[0]
        )
        
        if selected_list:
            # Load segments for selected list
            segments = self.load_list_segments(selected_list)
            
            if segments:
                segments_df = pd.DataFrame(segments)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Segment size distribution
                    fig_segments = px.bar(
                        segments_df,
                        x='name',
                        y='member_count',
                        color='type',
                        title=f"📊 Segments in {lists_df[lists_df['list_id'] == selected_list]['list_name'].iloc[0]}",
                        labels={'member_count': 'Members', 'name': 'Segment Name'}
                    )
                    fig_segments.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_segments, use_container_width=True)
                
                with col2:
                    # Segment type distribution
                    type_dist = segments_df['type'].value_counts()
                    fig_types = px.pie(
                        values=type_dist.values,
                        names=type_dist.index,
                        title="🔧 Segment Types Distribution"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
                
                # Segments table
                st.write("**📋 Segment Details:**")
                display_segments = segments_df[['name', 'member_count', 'type', 'created_at']].copy()
                display_segments['created_at'] = pd.to_datetime(display_segments['created_at']).dt.strftime('%Y-%m-%d')
                st.dataframe(display_segments, use_container_width=True)
                
            else:
                st.info(f"No segments found for the selected list. Create segments in Mailchimp to see analysis here.")
        
        # Segmentation recommendations
        st.write("**💡 Segmentation Recommendations:**")
        
        recommendations = [
            "🎯 **Engagement-Based**: Segment by open/click rates (High, Medium, Low)",
            "📅 **Lifecycle**: New subscribers (0-30 days), Active (30-90), Veteran (90+)",
            "🌍 **Geographic**: Target by location for region-specific campaigns", 
            "💰 **Purchase Behavior**: High-value customers, Recent purchasers, Non-purchasers",
            "📱 **Device/Client**: Mobile vs Desktop users for optimized content",
            "⏰ **Send Time**: Best engagement times for personalized delivery"
        ]
        
        for rec in recommendations:
            st.write(f"• {rec}")
    
    def render_sidebar_controls(self):
        """Render sidebar controls"""
        st.sidebar.header("👥 Audience Analytics")
        
        # Analysis type selector
        analysis_type = st.sidebar.radio(
            "📊 Analysis Focus",
            options=["Overview", "Growth", "Engagement", "Segmentation"],
            index=0
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
        
        return analysis_type
    
    def run(self):
        """Main dashboard execution"""
        st.title("👥 Email Audience Analytics")
        st.write("Advanced audience insights and segmentation powered by Mailchimp Marketing SDK")
        
        # Sidebar controls
        analysis_type = self.render_sidebar_controls()
        
        # Load data
        audience_data = self.load_audience_data()
        
        if not audience_data['lists'].empty:
            # Always show overview
            self.render_audience_overview(audience_data)
            st.divider()
            
            # Render selected analysis
            if analysis_type == "Overview":
                self.render_list_performance(audience_data)
                
            elif analysis_type == "Growth":
                self.render_growth_analysis(audience_data)
                
            elif analysis_type == "Engagement":
                self.render_engagement_scoring(audience_data)
                
            elif analysis_type == "Segmentation":
                self.render_segmentation_analysis(audience_data)
            
            # Export options
            with st.expander("💾 Export Data"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 Download Lists CSV"):
                        csv = audience_data['lists'].to_csv(index=False)
                        st.download_button(
                            label="Download lists.csv",
                            data=csv,
                            file_name=f"mailchimp_lists_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if not audience_data['members'].empty and st.button("📥 Download Members CSV"):
                        csv = audience_data['members'].to_csv(index=False)
                        st.download_button(
                            label="Download members.csv",
                            data=csv,
                            file_name=f"mailchimp_members_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
        else:
            st.warning("No audience data found.")
            st.info("Check your API configuration and ensure you have lists with subscribers.")


# Streamlit app execution
def main():
    """Main function for standalone execution"""
    try:
        dashboard = EmailAudienceDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"Dashboard error: {e}")
        st.info("Please check your Mailchimp API configuration and try again.")


if __name__ == "__main__":
    main()