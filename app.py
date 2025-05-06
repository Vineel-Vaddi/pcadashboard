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
                  "finishDate": 1,Added field for caseID
                  "totalTime": 1,,
                  "login": 1,: 1,
                  "managerLogin": 1,
                  "category": 1,: 1,
                  "notes": 1, 1,
                  "queue": 1,
                  "site": 1},
    try:          "site": 1}
        cursor = collection.find(query, projection).batch_size(500)
        documents = list(cursor)(query, projection).batch_size(500)
        logging.info("Query returned %d documents", len(documents))
        return documentsery returned %d documents", len(documents))
    except Exception as e:
        logging.error("Error querying data: %s", str(e))
        return []rror("Error querying data: %s", str(e))
        return []
@st.cache_data
def transform_data(_documents):
    """nsform_data(_documents):
    Transform documents into a full DataFrame (for charts) and a raw DataFrame (for display/export) 
    with only the necessary fields and renamed columns.ts) and a raw DataFrame (for display/export) 
    """h only the necessary fields and renamed columns.
    df = pd.DataFrame(_documents)
    # Removed conversion for '_id' as raw table now uses caseIDcuments here instead of 'documents'
    raw_columns_map = {"caseID": "Case ID",  # Now using caseID instead of _idns:
                       "finishDate": "Finish Date",
                       "category": "Category",le and Export with renamed columns
                       "login": "Login",ted to use caseID instead of _id
                       "managerLogin": "Manager Login",ate",
                       "notes": "Notes",gory",
                       "queue": "Queue",
                       "totalTime": "Total Time"}Manager Login",
    if not df.empty:
        raw_df = df[list(raw_columns_map.keys())].rename(columns=raw_columns_map)
    else:   "totalTime": "Total Time"}
        raw_df = pd.DataFrame()
    return df, raw_dfaw_df = df[list(raw_columns_map.keys())].rename(columns=raw_columns_map)

def create_dashboard(df):ataFrame()
    # Removed duplicate raw data table and summary metrics    return df, raw_df
    
    # Daily cases trend
    st.subheader("Daily Cases Trend")# Removed duplicate raw data table and summary metrics
    daily_cases = df.groupby('finishDate').size().reset_index(name='count')
    fig_trend = px.line(daily_cases, x='finishDate', y='count')
    st.plotly_chart(fig_trend)
    ame='count')
    # Cases by sitecases, x='finishDate', y='count')
    st.subheader("Cases by Site")st.plotly_chart(fig_trend)
    site_cases = df['site'].value_counts()
    fig_site = px.pie(values=site_cases.values, names=site_cases.index)
    st.plotly_chart(fig_site)
    
    # Cases by categorysite_cases.values, names=site_cases.index)
    st.subheader("Cases by Category")st.plotly_chart(fig_site)
    category_cases = df['category'].value_counts()
    fig_category = px.bar(x=category_cases.index, y=category_cases.values)
    st.plotly_chart(fig_category)
    
    # Average Time per Categoryory_cases.index, y=category_cases.values)
    st.subheader("Average Time per Category")st.plotly_chart(fig_category)
    avg_time_category = df.groupby('category')['totalTime'].mean().reset_index()
    fig_avg_category = px.bar(
        avg_time_category,
        x='category',upby('category')['totalTime'].mean().reset_index()
        y='totalTime',bar(
        labels={'totalTime': 'Average Time (sec)', 'category': 'Category'},gory,
        title="Average Time Taken per Category"
    )
    st.plotly_chart(fig_avg_category))', 'category': 'Category'},
       title="Average Time Taken per Category"
    # Bar chart for case categories by site
    st.subheader("Case Categories by Site")st.plotly_chart(fig_avg_category)
    category_site_data = df.groupby(['site', 'category']).size().reset_index(name='count')
    fig_category_site = px.bar(
        category_site_data,
        x='site',upby(['site', 'category']).size().reset_index(name='count')
        y='count',bar(
        color='category',site_data,
        barmode='group',
        title="Case Categories by Site"
    ),
    st.plotly_chart(fig_category_site)
       title="Case Categories by Site"
    # Line chart for average case time trend
    st.subheader("Average Case Time Trend")st.plotly_chart(fig_category_site)
    avg_time_trend = df.groupby('finishDate')['totalTime'].mean().reset_index()
    fig_avg_time = px.line(d
        avg_time_trend,
        x='finishDate',upby('finishDate')['totalTime'].mean().reset_index()
        y='totalTime',ine(
        title="Average Case Time Trend",
        labels={'totalTime': 'Average Time (seconds)', 'finishDate': 'Date'},
    )
    st.plotly_chart(fig_avg_time)
       labels={'totalTime': 'Average Time (seconds)', 'finishDate': 'Date'}
    # Pie chart for queue distribution
    st.subheader("Queue Distribution")st.plotly_chart(fig_avg_time)
    queue_distribution = df['queue'].value_counts()
    fig_queue = px.pie(
        values=queue_distribution.values,
        names=queue_distribution.index,= df['queue'].value_counts()
        title="Queue Distribution"
    )s,
    st.plotly_chart(fig_queue)ndex,
   title="Queue Distribution"
def main():
    st.title("Cases Data Analysis Dashboard")    st.plotly_chart(fig_queue)
    # Removed refresh button from main and added it to the sidebar
    if st.sidebar.button("Refresh Data"):
        st.rerun()
    with st.spinner("Loading data..."):d added it to the sidebar
        client = init_mongodb()button("Refresh Data"):
        if not client:
            logging.error("Failed to initialize MongoDB client.")ta..."):
            returnmongodb()
        try:
            db = client['case_manager']g.error("Failed to initialize MongoDB client.")
            collection = db['cases']return
            logging.info("Connected to MongoDB collection: case_manager.cases")
            with st.sidebar.expander("Filters 🔍", expanded=True):r']
                default_start_date = datetime.now() - timedelta(days=30)
                default_end_date = datetime.now()nager.cases")
                start_date = st.date_input(
                    "📅 Start Date", () - timedelta(days=30)
                    value=default_start_date, .now()
                    max_value=datetime.now(), input(
                    help="Select the starting date for filtering cases."
                )
                end_date = st.date_input(
                    "📅 End Date",    help="Select the starting date for filtering cases."
                    value=default_end_date, 
                    max_value=datetime.now(), input(
                    help="Select the ending date for filtering cases."
                )
                login_options = ['All'] + get_unique_values(collection, 'login')
                selected_login = st.selectbox(   help="Select the ending date for filtering cases."
                    "👤 Login", 
                    login_options, unique_values(collection, 'login')
                    help="Filter cases by user login." st.selectbox(
                )
                manager_options = ['All'] + get_unique_values(collection, 'managerLogin')
                selected_manager = st.selectbox(   help="Filter cases by user login."
                    "👔 Manager Login", 
                    manager_options, unique_values(collection, 'managerLogin')
                    help="Filter cases by manager login."lectbox(
                )", 
                site_options = ['All'] + get_unique_values(collection, 'site')
                selected_site = st.selectbox(   help="Filter cases by manager login."
                    "🏢 Site", 
                    site_options, unique_values(collection, 'site')
                    help="Filter cases by site." st.selectbox(
                )
            filters = {
                'start_date': start_date,   help="Filter cases by site."
                'end_date': end_date,
                'login': selected_login if selected_login != 'All' else None,
                'managerLogin': selected_manager if selected_manager != 'All' else None,ate,
                'site': selected_site if selected_site != 'All' else None
            }
            documents = query_data(collection, filters)All' else None,
            if not documents:   'site': selected_site if selected_site != 'All' else None
                st.warning("No data found for the selected filters.")
                logging.warning("No data found for filters: %s", filters)_data(collection, filters)
                return
            # Transform the retrieved documents (with caching)
            full_df, raw_df = transform_data(documents)g.warning("No data found for filters: %s", filters)
            # Prepare Excel export from raw_df
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")aching)
            output = io.BytesIO()ocuments)
            df_export = raw_df.copy()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:now().strftime("%Y%m%d_%H%M%S")
                df_export.to_excel(writer, index=False)
            processed_data = output.getvalue()
            st.sidebar.download_button(ter') as writer:
                label="Export to Excel",ex=False)
                data=processed_data,value()
                file_name=f"cases_export_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"el",
            )
            total_cases = len(full_df)
            avg_time = full_df['totalTime'].mean() if total_cases > 0 else 0   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            unique_agents = full_df['login'].nunique() if total_cases > 0 else 0
            metric_html = f"""
            <div style="display: flex; justify-content: space-around; margin-bottom: 20px;">
                <div style="padding: 10px; border-radius: 5px; background-color: {'#d4edda' if total_cases > 0 else '#f8d7da'}; width: 30%; text-align: center;">ll_df['login'].nunique() if total_cases > 0 else 0
                    <h3>Total Cases</h3>
                    <p style="font-size: 24px; margin: 0;">{total_cases}</p>
                </div>x; border-radius: 5px; background-color: {'#d4edda' if total_cases > 0 else '#f8d7da'}; width: 30%; text-align: center;">
                <div style="padding: 10px; border-radius: 5px; background-color: {'#d4edda' if avg_time < 60 else '#f8d7da'}; width: 30%; text-align: center;">
                    <h3>Average Time (sec)</h3> style="font-size: 24px; margin: 0;">{total_cases}</p>
                    <p style="font-size: 24px; margin: 0;">{avg_time:.2f}</p>
                </div>er-radius: 5px; background-color: {'#d4edda' if avg_time < 60 else '#f8d7da'}; width: 30%; text-align: center;">
                <div style="padding: 10px; border-radius: 5px; background-color: {'#d4edda' if unique_agents > 0 else '#f8d7da'}; width: 30%; text-align: center;">
                    <h3>Unique Agents</h3> style="font-size: 24px; margin: 0;">{avg_time:.2f}</p>
                    <p style="font-size: 24px; margin: 0;">{unique_agents}</p>
                </div> border-radius: 5px; background-color: {'#d4edda' if unique_agents > 0 else '#f8d7da'}; width: 30%; text-align: center;">
            </div>
            """ style="font-size: 24px; margin: 0;">{unique_agents}</p>
            st.markdown(metric_html, unsafe_allow_html=True)div>
            # Display only the raw table with essential fieldsiv>
            st.subheader("Filtered Raw Data")
            selected_columns = st.multiselect("Select Columns to Display", raw_df.columns.tolist(), default=raw_df.columns.tolist())
            filtered_df = raw_df[selected_columns] essential fields
            st.dataframe(filtered_df)
            create_dashboard(full_df)ect Columns to Display", raw_df.columns.tolist(), default=raw_df.columns.tolist())
        except Exception as e:cted_columns]
            st.error(f"An error occurred: {str(e)}")
            logging.error("An error occurred: %s", str(e))ull_df)
        finally:
            logging.info("MongoDB client will remain open for reuse.")
ing.error("An error occurred: %s", str(e))
if __name__ == "__main__":
    main()    main()