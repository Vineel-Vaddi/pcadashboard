import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
import plotly.express as px
import logging
import io
import xlsxwriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Load environment variables from .env file
load_dotenv()

# Initialize MongoDB connection
@st.cache_resource
def init_mongodb():
    """
    Initialize MongoDB connection with caching
    """
    try:
        mongodb_url = os.getenv('MONGODB_URL')
        if not mongodb_url:
            raise ValueError("MongoDB URL not found in .env file")
        client = MongoClient(mongodb_url)
        return client
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")
        logging.error("Error connecting to MongoDB: %s", str(e))
        return None

def get_unique_values(collection, field):
    """
    Get unique values for a specific field in the collection
    """
    return sorted(collection.distinct(field))

def query_data(collection, filters):
    """
    Query data based on filters
    """
    query = {}
    logging.info("Building query with filters: %s", filters)
    
    # Date range filter
    if filters.get('start_date') and filters.get('end_date'):
        query['finishDate'] = {
            '$gte': filters['start_date'].strftime('%Y-%m-%d'),
            '$lte': filters['end_date'].strftime('%Y-%m-%d')
        }
    
    # Other filters
    for field in ['login', 'managerLogin', 'site']:
        if filters.get(field):
            query[field] = filters[field]
    
    logging.info("Executing query: %s", query)
    try:
        documents = list(collection.find(query))
        logging.info("Query returned %d documents", len(documents))
        return documents
    except Exception as e:
        logging.error("Error querying data: %s", str(e))
        return []

def create_dashboard(df):
    """
    Create dashboard visualizations
    """
    # Move the enhanced raw data table to the top
    st.subheader("Filtered Raw Data")
    selected_columns = st.multiselect("Select Columns to Display", df.columns.tolist(), default=df.columns.tolist())
    filtered_df = df[selected_columns]
    st.dataframe(filtered_df)

    # Summary metrics (updated metric label)
    st.subheader("Dashboard")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Cases", len(df))
    with col2:
        st.metric("Average Time (sec)", f"{df['totalTime'].mean():.2f}")
    with col3:
        st.metric("Unique Agents", df['login'].nunique())

    # Daily cases trend
    st.subheader("Daily Cases Trend")
    daily_cases = df.groupby('finishDate').size().reset_index(name='count')
    fig_trend = px.line(daily_cases, x='finishDate', y='count')
    st.plotly_chart(fig_trend)

    # Cases by site
    st.subheader("Cases by Site")
    site_cases = df['site'].value_counts()
    fig_site = px.pie(values=site_cases.values, names=site_cases.index)
    st.plotly_chart(fig_site)

    # Cases by category
    st.subheader("Cases by Category")
    category_cases = df['category'].value_counts()
    fig_category = px.bar(x=category_cases.index, y=category_cases.values)
    st.plotly_chart(fig_category)

    # Average Time per Category
    st.subheader("Average Time per Category")
    avg_time_category = df.groupby('category')['totalTime'].mean().reset_index()
    fig_avg_category = px.bar(
        avg_time_category,
        x='category',
        y='totalTime',
        labels={'totalTime': 'Average Time (sec)', 'category': 'Category'},
        title="Average Time Taken per Category"
    )
    st.plotly_chart(fig_avg_category)

    # Heatmap for daily case volume
    st.subheader("Daily Case Volume Heatmap")
    heatmap_data = df.groupby(['finishDate', 'site']).size().reset_index(name='count')
    heatmap_pivot = heatmap_data.pivot(index='finishDate', columns='site', values='count').fillna(0)
    fig_heatmap = px.imshow(
        heatmap_pivot,
        labels=dict(x="Site", y="Date", color="Cases"),
        x=heatmap_pivot.columns,
        y=heatmap_pivot.index,
        color_continuous_scale="Viridis"
    )
    st.plotly_chart(fig_heatmap)

    # Bar chart for case categories by site
    st.subheader("Case Categories by Site")
    category_site_data = df.groupby(['site', 'category']).size().reset_index(name='count')
    fig_category_site = px.bar(
        category_site_data,
        x='site',
        y='count',
        color='category',
        barmode='group',
        title="Case Categories by Site"
    )
    st.plotly_chart(fig_category_site)

    # Line chart for average case time trend
    st.subheader("Average Case Time Trend")
    avg_time_trend = df.groupby('finishDate')['totalTime'].mean().reset_index()
    fig_avg_time = px.line(
        avg_time_trend,
        x='finishDate',
        y='totalTime',
        title="Average Case Time Trend",
        labels={'totalTime': 'Average Time (seconds)', 'finishDate': 'Date'}
    )
    st.plotly_chart(fig_avg_time)

    # Pie chart for queue distribution
    st.subheader("Queue Distribution")
    queue_distribution = df['queue'].value_counts()
    fig_queue = px.pie(
        values=queue_distribution.values,
        names=queue_distribution.index,
        title="Queue Distribution"
    )
    st.plotly_chart(fig_queue)

def main():
    st.title("Cases Data Analysis Dashboard")
    
    # Initialize MongoDB connection
    client = init_mongodb()
    if not client:
        logging.error("Failed to initialize MongoDB client.")
        return
    
    try:
        # Connect to database and collection
        db = client['case_manager']
        collection = db['cases']
        logging.info("Connected to MongoDB collection: case_manager.cases")

        # Sidebar filters
        st.sidebar.header("Filters")

        # Date range filter
        default_start_date = datetime.now() - timedelta(days=30)
        default_end_date = datetime.now()
        
        start_date = st.sidebar.date_input(
            "Start Date",
            value=default_start_date,
            max_value=datetime.now()
        )
        end_date = st.sidebar.date_input(
            "End Date",
            value=default_end_date,
            max_value=datetime.now()
        )

        # Other filters
        login_options = ['All'] + get_unique_values(collection, 'login')
        manager_options = ['All'] + get_unique_values(collection, 'managerLogin')
        site_options = ['All'] + get_unique_values(collection, 'site')

        selected_login = st.sidebar.selectbox("Login", login_options)
        selected_manager = st.sidebar.selectbox("Manager Login", manager_options)
        selected_site = st.sidebar.selectbox("Site", site_options)

        # Prepare filters
        filters = {
            'start_date': start_date,
            'end_date': end_date,
            'login': selected_login if selected_login != 'All' else None,
            'managerLogin': selected_manager if selected_manager != 'All' else None,
            'site': selected_site if selected_site != 'All' else None
        }

        # Query data
        documents = query_data(collection, filters)
        
        if not documents:
            st.warning("No data found for the selected filters.")
            logging.warning("No data found for filters: %s", filters)
            return

        # Convert to DataFrame
        df = pd.DataFrame(documents)
        # Fix ObjectId conversion for Arrow compatibility
        if '_id' in df.columns:
            df['_id'] = df['_id'].astype(str)

        # Replace the Export button with a download button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = io.BytesIO()
        df_export = df.copy()
        if '_id' in df_export.columns:
            df_export = df_export.drop('_id', axis=1)
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        processed_data = output.getvalue()
        st.sidebar.download_button(
            label="Export to Excel",
            data=processed_data,
            file_name=f"cases_export_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        logging.info("Prepared Excel file for download as cases_export_%s.xlsx", timestamp)

        # Create dashboard (now shows Filtered Raw Data at top)
        create_dashboard(df)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logging.error("An error occurred: %s", str(e))
    
    finally:
        # Ensure the MongoDB client is not closed prematurely
        logging.info("MongoDB client will remain open for reuse.")
        # Do not close the client here to avoid "Cannot use MongoClient after close" error.

if __name__ == "__main__":
    main()