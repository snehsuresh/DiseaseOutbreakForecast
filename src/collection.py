"""
data_collection.py

This script collects real-time data on disease outbreaks from:
- WHO (using an RSS feed)
- CDC (using a sample JSON API endpoint)
- HealthMap (via web scraping)
- Wikipedia (for additional disease background info)

The collected data is saved to a file "raw_data.json".
"""

import requests
import json
import time
import logging
import os
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.parse

# ✅ Configuration
DATA_FILE = "healthmap_data.json"
RAW_DATA_FILE = "raw_data.json"
REQUEST_TIMEOUT = 10  # Timeout for all API calls
RATE_LIMIT = 1  # Sleep time between requests

# ✅ Keywords for filtering outbreak-related news
OUTBREAK_KEYWORDS = ["outbreak", "epidemic", "pandemic", "infection", "disease", "virus", "health emergency", "Influenza"]

# ✅ Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- 🔍 WHO Data Fetching ---
def fetch_who_data():
    """
    Fetch disease outbreak news from WHO's general RSS feed and filter relevant articles.
    """
    url = "https://www.who.int/rss-feeds/news-english.xml"
    logging.info("Fetching WHO general news and filtering for outbreaks...")

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.findAll("item")

        who_data = []
        for item in items:
            title = item.title.text
            description = item.description.text

            # Filter relevant news
            if any(keyword.lower() in (title + description).lower() for keyword in OUTBREAK_KEYWORDS):
                data = {
                    "source": "WHO",
                    "title": title,
                    "link": item.link.text,
                    "description": description,
                    "pubDate": item.pubDate.text,
                }
                who_data.append(data)

        time.sleep(RATE_LIMIT)
        return who_data

    except Exception as e:
        logging.error("Error fetching WHO data: %s", e)
        return []


# --- 🔍 CDC Data Fetching ---
def fetch_cdc_data():
    """
    Fetch the latest disease outbreak news from the CDC.
    """
    url = "https://tools.cdc.gov/api/v2/resources/media"
    params = {
        "q": "outbreak OR epidemic OR pandemic",
        "sort": "datePublished",
        "order": "desc",
        "max": 20,
        "format": "json",
    }

    logging.info("Fetching CDC outbreak data...")
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        cdc_json = response.json()

        cdc_data = []
        for item in cdc_json.get("results", []):
            title = item.get("name", "N/A")
            description = item.get("description", "N/A")

            data = {
                "source": "CDC",
                "title": title,
                "description": description,
                "link": item.get("url", "N/A"),
                "pubDate": item.get("datePublished", "N/A"),
            }
            cdc_data.append(data)

        time.sleep(1)
        return cdc_data

    except Exception as e:
        logging.error("Error fetching CDC data: %s", e)
        return []


# --- 🔍 HealthMap Data Fetching (via Web Scraping) ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import logging

def fetch_healthmap_data():
    """
    Fetches disease outbreak data from HealthMap using Selenium with explicit wait.
    """
    url = "https://www.healthmap.org/en/"
    logging.info("Fetching HealthMap outbreak data...")

    # Initialize Selenium WebDriver (make sure you have the correct driver installed)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (optional)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # Wait until the outbreak elements are present (adjust the selector if needed)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "outbreak-container"))
        )

        # Get page source after waiting
        time.sleep(3)  # Additional wait in case of delayed content loading
        soup = BeautifulSoup(driver.page_source, "html.parser")

        healthmap_data = []
        
        # Extract outbreak sections
        outbreak_sections = soup.find_all('div', class_='outbreak-container')
        logging.info(f"Found {len(outbreak_sections)} outbreak entries.")

        for section in outbreak_sections:
            title = section.find('h3').text.strip() if section.find('h3') else "N/A"
            description = section.find('p').text.strip() if section.find('p') else "N/A"

            # Debugging output
            print(f"Title: {title}, Description: {description}")

            if any(keyword.lower() in (title + " " + description).lower() for keyword in OUTBREAK_KEYWORDS):
                data = {
                    "source": "HealthMap",
                    "title": title,
                    "description": description,
                    "location": "Unknown",
                    "pubDate": datetime.today().strftime("%Y-%m-%d"),
                }
                healthmap_data.append(data)

        driver.quit()
        return healthmap_data

    except Exception as e:
        logging.error(f"Error fetching HealthMap data: {e}")
        driver.quit()
        return []




# --- 🔍 Wikipedia Data Fetching ---
def fetch_wikipedia_data():
    """
    Fetches recent disease outbreaks from Wikipedia's 'Current Events' page.
    """
    url = "https://en.wikipedia.org/wiki/Portal:Current_events"

    logging.info("Fetching Wikipedia current events for disease outbreaks...")
    
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        outbreak_events = []
        
        # Find outbreak-related events in the main content section
        event_sections = soup.find_all('li')  # Wikipedia current events use <li> tags for listing

        for event in event_sections:
            event_text = event.text.strip()
            if any(keyword.lower() in event_text.lower() for keyword in OUTBREAK_KEYWORDS):
                outbreak_events.append(event_text)

        # Format results into a dictionary
        data = {
            "source": "Wikipedia",
            "title": "Current Outbreak Events",
            "events": outbreak_events[:10],  # Limit to top 10 events
        }

        time.sleep(RATE_LIMIT)
        return data

    except Exception as e:
        logging.error("Error fetching Wikipedia current events: %s", e)
        return {"source": "Wikipedia", "title": "Current Outbreak Events", "events": []}


# --- 🔍 Main Function ---
def main():
    all_data = {
        "WHO": fetch_who_data(),
        "CDC": fetch_cdc_data(),
        "HealthMap": fetch_healthmap_data(),
        "Wikipedia": fetch_wikipedia_data("disease outbreak"),
    }

    # Save data to a JSON file
    with open(RAW_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4)

    logging.info("Raw data saved to %s", RAW_DATA_FILE)


# --- Run Script ---
if __name__ == "__main__":
    main()
