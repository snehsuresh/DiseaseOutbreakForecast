"""
data_preprocessing.py

This script loads the raw JSON data from data_collection.py,
cleans and standardizes it, then saves the clean data to clean_data.csv.
"""

import json
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_raw_data(file_path="raw_data.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def preprocess_data(raw_data):
    # Combine outbreak data from different sources into one list
    combined = []
    for source in ["WHO", "CDC", "HealthMap"]:
        entries = raw_data.get(source, [])
        for item in entries:
            # Standardize field names (use title, description, pubDate, and add a source field)
            combined.append({
                "source": item.get("source", source),
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "link": item.get("link", ""),
                "pubDate": item.get("pubDate", ""),
                "location": item.get("location", "Unknown")
            })
    # Convert to DataFrame
    df = pd.DataFrame(combined)
    
    # Handle missing values and duplicates
    df.drop_duplicates(inplace=True)
    df.fillna("Unknown", inplace=True)
    
    # Convert publication dates to datetime if possible
    try:
        df["pubDate"] = pd.to_datetime(df["pubDate"], errors="coerce")
    except Exception as e:
        logging.warning("Error converting pubDate: %s", e)
    
    return df

def main():
    raw_data = load_raw_data("raw_data.json")
    df_clean = preprocess_data(raw_data)
    df_clean.to_csv("clean_data.csv", index=False)
    logging.info("Clean data saved to clean_data.csv")

if __name__ == "__main__":
    main()
