import os
from dotenv import load_dotenv
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def connect_to_mongodb():
    """
    Establishes connection to MongoDB using URL from .env file
    """
    try:
        # Get MongoDB URL from .env file
        mongodb_url = os.getenv('MONGODB_URL')
        if not mongodb_url:
            raise ValueError("MongoDB URL not found in .env file")
        
        # Create MongoDB client
        client = MongoClient(mongodb_url)
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        return None

def export_to_excel(collection, output_path):
    """
    Exports MongoDB collection data to Excel file
    """
    try:
        # Fetch all documents from the collection
        documents = list(collection.find({}))
        
        if not documents:
            print("No documents found in the collection")
            return False
        
        # Convert MongoDB documents to DataFrame
        df = pd.DataFrame(documents)
        
        # Drop MongoDB's default _id field if not needed
        if '_id' in df.columns:
            df = df.drop('_id', axis=1)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_path}/cases_export_{timestamp}.xlsx"
        
        # Export to Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Data successfully exported to {filename}")
        return True
        
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")
        return False

def main():
    """
    Main function to handle the export process
    """
    # Connect to MongoDB
    client = connect_to_mongodb()
    if not client:
        return
    
    try:
        # Select database (replace 'your_database' with your actual database name)
        db = client['case_manager']
        
        # Select collection
        collection = db['cases']
        
        # Define output directory
        output_dir = 'exports'
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Export data
        export_to_excel(collection, output_dir)
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Close MongoDB connection
        client.close()

if __name__ == "__main__":
    main()