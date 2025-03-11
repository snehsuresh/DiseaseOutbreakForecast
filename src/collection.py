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

# --- 🔍 HealthMap Data Fetching (via Web Scraping) ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import logging

# ✅ Configuration
DATA_FILE = "healthmap_data.json"
RAW_DATA_FILE = "raw_data.json"
REQUEST_TIMEOUT = 10  # Timeout for all API calls
RATE_LIMIT = 1  # Sleep time between requests

# ✅ Keywords for filtering outbreak-related news
OUTBREAK_KEYWORDS = [
    "outbreak",
    "epidemic",
    "pandemic",
    "infection",
    "disease",
    "virus",
    "health emergency",
    "Influenza",
]

# ✅ Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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
            if any(
                keyword.lower() in (title + description).lower()
                for keyword in OUTBREAK_KEYWORDS
            ):
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
        "sort": "datePublished",
        "order": "desc",
        "max": 50,  # Increase max results to ensure we get relevant items
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

            # **Manually filter for relevant outbreaks**
            combined_text = f"{title} {description}".lower()
            if any(keyword in combined_text for keyword in OUTBREAK_KEYWORDS):
                data = {
                    "source": "CDC",
                    "title": title,
                    "description": description,
                    "link": item.get("url", "N/A"),
                    "pubDate": item.get("datePublished", "N/A"),
                }
                cdc_data.append(data)

        logging.info(f"Found {len(cdc_data)} relevant CDC outbreak entries.")

        time.sleep(1)  # Rate-limiting
        return cdc_data

    except Exception as e:
        logging.error("Error fetching CDC data: %s", e)
        return []


def fetch_healthmap_data():
    """
    Fetches disease outbreak data from HealthMap using Selenium with explicit wait.
    """
    url = "https://www.healthmap.org/en/"
    logging.info("Fetching HealthMap outbreak data...")

    # Initialize Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # **Temporarily Disable Headless Mode for Debugging**
    # options.add_argument("--headless")  # Uncomment after confirming it works

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # **Wait for the section map_canvas to appear**
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "map_canvas"))
        )

        # **Wait for outbreak markers to load**
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@title]"))
        )

        # **Additional sleep (some maps delay JavaScript rendering)**
        time.sleep(5)

        # Parse page content
        soup = BeautifulSoup(driver.page_source, "html.parser")

        healthmap_data = []

        # Find the map container
        map_canvas = soup.find("section", id="map_canvas")
        if not map_canvas:
            logging.warning("No map_canvas section found!")
            driver.quit()
            return []

        # **Find all outbreak markers (divs with title attribute inside #map_canvas)**
        outbreak_sections = map_canvas.find_all("div", title=True)
        logging.info(f"Found {len(outbreak_sections)} outbreak entries.")

        for section in outbreak_sections:
            title = section.get("title", "N/A").strip()  # Extract title
            description = section.find("p").text.strip() if section.find("p") else "N/A"

            # Debugging output
            print(f"Title: {title}, Description: {description}")

            # **Skip 'Your Location' Entries**
            if "your location" in title.lower():
                continue

            if any(
                keyword.lower() in (title + " " + description).lower()
                for keyword in OUTBREAK_KEYWORDS
            ):
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
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        outbreak_events = []

        # **Find the main current events container**
        event_sections = soup.find_all(
            "div", class_="current-events-content description"
        )
        print(len(event_sections))

        for section in event_sections:
            # **Find all events (nested inside <ul> lists)**
            for event in section.find_all("li"):
                event_text = event.text.strip()
                link_tag = event.find("a")  # Find first hyperlink in event

                # **Filter only outbreak-related events**
                if any(
                    keyword.lower() in event_text.lower()
                    for keyword in OUTBREAK_KEYWORDS
                ):
                    outbreak_events.append(
                        {
                            "title": event_text,
                            "link": (
                                f"https://en.wikipedia.org{link_tag['href']}"
                                if link_tag
                                else "N/A"
                            ),
                        }
                    )

        # **Format results into a dictionary**
        data = {
            "source": "Wikipedia",
            "title": "Current Outbreak Events",
            "events": outbreak_events[:10],  # Limit to top 10 events
        }

        time.sleep(2)  # Rate-limiting to avoid hitting Wikipedia too frequently
        return data

    except Exception as e:
        logging.error("Error fetching Wikipedia current events: %s", e)
        return {"source": "Wikipedia", "title": "Current Outbreak Events", "events": []}


# --- 🔍 Main Function ---
def main():
    all_data = {
        # "WHO": fetch_who_data(),
        # "CDC": fetch_cdc_data(),
        # "HealthMap": fetch_healthmap_data(),
        "Wikipedia": fetch_wikipedia_data(),
    }

    # Save data to a JSON file
    with open(RAW_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4)

    logging.info("Raw data saved to %s", RAW_DATA_FILE)


# --- Run Script ---
if __name__ == "__main__":
    main()
