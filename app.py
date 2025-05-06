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

# Add page configuration and welcome message at the very top
st.set_page_config(page_title="Case Dashboard", layout="wide", page_icon=":bar_chart:")
st.markdown(
    "<h1 style='text-align: center;'>Welcome to the Case Dashboard!</h1>"
    "<p style='text-align: center;'>Use the sidebar filters, dark mode toggle and interactive charts to explore the data.</p>",
    unsafe_allow_html=True
)

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
    Query data based on filters using projection and batching.
    """
    query = {}
    logging.info("Building query with filters: %s", filters)
    if filters.get('start_date') and filters.get('end_date'):
        query['finishDate'] = {
            '$gte': filters['start_date'].strftime('%Y-%m-%d'),
            '$lte': filters['end_date'].strftime('%Y-%m-%d')
        }
    for field in ['login', 'managerLogin', 'site']:
        if filters.get(field):
            query[field] = filters[field]
    logging.info("Executing query: %s", query)
    # Retrieve only the required fields for both dashboard and raw table
    projection = {"_id": 1,
                  "caseID": 1,  # Added field for caseID
                  "finishDate": 1,
                  "totalTime": 1,
                  "login": 1,
                  "managerLogin": 1,
                  "category": 1,
                  "notes": 1,
                  "queue": 1,
                  "site": 1}
    try:
        cursor = collection.find(query, projection).batch_size(500)
        documents = list(cursor)
        logging.info("Query returned %d documents", len(documents))
        return documents
    except Exception as e:
        logging.error("Error querying data: %s", str(e))
        return []

@st.cache_data
def transform_data(_documents):
    """
    Transform documents into a full DataFrame (for charts) and a raw DataFrame (for display/export) 
    with only the necessary fields and renamed columns.
    """
    df = pd.DataFrame(_documents)  # Use _documents here instead of 'documents'
    if not df.empty and '_id' in df.columns:
        df['_id'] = df['_id'].astype(str)
    # Prepare a version for Raw Data Table and Export with renamed columns
    raw_columns_map = {"caseID": "Case ID",  # Updated to use caseID instead of _id
                       "finishDate": "Finish Date",
                       "category": "Category",
                       "login": "Login",
                       "managerLogin": "Manager Login",
                       "notes": "Notes",
                       "queue": "Queue",
                       "totalTime": "Total Time"}
    if not df.empty:
        raw_df = df[list(raw_columns_map.keys())].rename(columns=raw_columns_map)
    else:
        raw_df = pd.DataFrame()
    return df, raw_df

def create_dashboard(df):
    # Removed duplicate raw data table and summary metrics
    
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
    # Removed refresh button from main and added it to the sidebar
    if st.sidebar.button("Refresh Data"):
        st.rerun()
    with st.spinner("Loading data..."):
        client = init_mongodb()
        if not client:
            logging.error("Failed to initialize MongoDB client.")
            return
        try:
            db = client['case_manager']
            collection = db['cases']
            logging.info("Connected to MongoDB collection: case_manager.cases")
            with st.sidebar.expander("Filters 🔍", expanded=True):
                default_start_date = datetime.now() - timedelta(days=30)
                default_end_date = datetime.now()
                start_date = st.date_input(
                    "📅 Start Date", 
                    value=default_start_date, 
                    max_value=datetime.now(), 
                    help="Select the starting date for filtering cases."
                )
                end_date = st.date_input(
                    "📅 End Date", 
                    value=default_end_date, 
                    max_value=datetime.now(), 
                    help="Select the ending date for filtering cases."
                )
                login_options = ['All'] + get_unique_values(collection, 'login')
                selected_login = st.selectbox(
                    "👤 Login", 
                    login_options, 
                    help="Filter cases by user login."
                )
                manager_options = ['All'] + get_unique_values(collection, 'managerLogin')
                selected_manager = st.selectbox(
                    "👔 Manager Login", 
                    manager_options, 
                    help="Filter cases by manager login."
                )
                site_options = ['All'] + get_unique_values(collection, 'site')
                selected_site = st.selectbox(
                    "🏢 Site", 
                    site_options, 
                    help="Filter cases by site."
                )
            filters = {
                'start_date': start_date,
                'end_date': end_date,
                'login': selected_login if selected_login != 'All' else None,
                'managerLogin': selected_manager if selected_manager != 'All' else None,
                'site': selected_site if selected_site != 'All' else None
            }
            documents = query_data(collection, filters)
            if not documents:
                st.warning("No data found for the selected filters.")
                logging.warning("No data found for filters: %s", filters)
                return
            # Transform the retrieved documents (with caching)
            full_df, raw_df = transform_data(documents)
            # Prepare Excel export from raw_df
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = io.BytesIO()
            df_export = raw_df.copy()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False)
            processed_data = output.getvalue()
            st.sidebar.download_button(
                label="Export to Excel",
                data=processed_data,
                file_name=f"cases_export_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            total_cases = len(full_df)
            avg_time = full_df['totalTime'].mean() if total_cases > 0 else 0
            unique_agents = full_df['login'].nunique() if total_cases > 0 else 0
            metric_html = f"""
            <div style="display: flex; justify-content: space-around; margin-bottom: 20px;">
                <div style="padding: 10px; border-radius: 5px; background-color: {'#d4edda' if total_cases > 0 else '#f8d7da'}; width: 30%; text-align: center;">
                    <h3>Total Cases</h3>
                    <p style="font-size: 24px; margin: 0;">{total_cases}</p>
                </div>
                <div style="padding: 10px; border-radius: 5px; background-color: {'#d4edda' if avg_time < 60 else '#f8d7da'}; width: 30%; text-align: center;">
                    <h3>Average Time (sec)</h3>
                    <p style="font-size: 24px; margin: 0;">{avg_time:.2f}</p>
                </div>
                <div style="padding: 10px; border-radius: 5px; background-color: {'#d4edda' if unique_agents > 0 else '#f8d7da'}; width: 30%; text-align: center;">
                    <h3>Unique Agents</h3>
                    <p style="font-size: 24px; margin: 0;">{unique_agents}</p>
                </div>
            </div>
            """
            st.markdown(metric_html, unsafe_allow_html=True)
            # Display only the raw table with essential fields
            st.subheader("Filtered Raw Data")
            selected_columns = st.multiselect("Select Columns to Display", raw_df.columns.tolist(), default=raw_df.columns.tolist())
            filtered_df = raw_df[selected_columns]
            st.dataframe(filtered_df)
            create_dashboard(full_df)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error("An error occurred: %s", str(e))
        finally:
            logging.info("MongoDB client will remain open for reuse.")

if __name__ == "__main__":
    main()