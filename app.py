
import streamlit as st
import pandas as pd
import re
from datetime import datetime
from google.cloud import vision
from google.oauth2 import service_account
import json
import gspread
from gspread_dataframe import set_with_dataframe

# Load credentials from secrets
credentials_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
creds = service_account.Credentials.from_service_account_info(credentials_dict)
scoped_creds = creds.with_scopes([
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])

# Google Sheets setup
SHEET_ID = st.secrets["SHEET_ID"]
SHEET_NAME = "Sheet1"
gc = gspread.authorize(scoped_creds)
worksheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Categories and keywords
CATEGORIES = {
    "meal prep": ["chicken", "beef", "pork", "steak", "turkey", "sausage", "bacon", "ribs", "lamb", "ham",
                  "shrimp", "salmon", "tuna", "cod", "tilapia", "crab", "fish", "avocado", "lettuce", "kale",
                  "spinach", "onion", "garlic", "potato", "tomato", "brussels", "broccoli", "cabbage", "carrot",
                  "celery", "pepper", "mushroom", "cucumber", "herbs", "ground", "roast", "meat", "veggie", "vegetable"],
    "snacks": ["chips", "cracker", "cookie", "pretzel", "popcorn", "granola", "candy", "chocolate", "bar",
               "trail mix", "snack", "jerky"],
    "toiletries": ["toilet paper", "tissue", "toothpaste", "toothbrush", "shampoo", "soap", "deodorant",
                   "lotion", "razor", "floss", "wipes", "cotton"],
    "drinks": ["soda", "juice", "water", "sparkling", "coke", "pepsi", "tea", "coffee", "kombucha", "gatorade",
               "energy drink"],
    "alcohol": ["wine", "beer", "whiskey", "vodka", "gin", "tequila", "rum", "cider", "seltzer", "champagne"],
    "cleaning": ["detergent", "bleach", "cleaner", "sponge", "paper towel", "disinfectant", "dish soap", "laundry"],
    "dairy alternatives": ["almond milk", "oat milk", "soy milk", "coconut milk", "non-dairy", "plant-based",
                           "vegan", "cashew milk"],
    "pantry": ["rice", "pasta", "flour", "sugar", "oil", "vinegar", "spice", "cereal", "oats", "canned", "beans",
               "sauce", "broth", "peanut butter", "jam", "honey", "baking", "seasoning", "salt"]
}

def categorize(item):
    name = item.lower()
    for category, keywords in CATEGORIES.items():
        if any(k in name for k in keywords):
            return category
    return "Other"

def extract_text_google_vision(image_bytes):
    client = vision.ImageAnnotatorClient(credentials=creds)
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    text = response.text_annotations[0].description if response.text_annotations else ""
    return text

def parse_items(text):
    lines = text.split('\n')
    item_data = []
    for line in lines:
        match = re.match(r"(.+?)\s+\$?(\d+\.\d{2})$", line.strip())
        if match:
            item_name = match.group(1).strip()
            price = float(match.group(2))
            item_data.append((item_name, price))
    return item_data

st.set_page_config(page_title="Grocery Receipt Scanner", layout="wide")
st.title("📸 Grocery Receipt Scanner")

uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image_bytes = uploaded_file.read()
    text = extract_text_google_vision(image_bytes)
    raw_items = parse_items(text)
    today = datetime.today()
    date_str = today.strftime("%Y-%m-%d")
    day_str = today.strftime("%A")
    store_guess = text.split('\n')[0].strip() if text else "Unknown"

    store = st.text_input("Store Name", value=store_guess)

    df = pd.DataFrame(raw_items, columns=["Item", "Price"])
    df.insert(0, "Store", store)
    df.insert(0, "Day", day_str)
    df.insert(0, "Date", date_str)
    df["Category"] = df["Item"].apply(categorize)

    st.subheader("📋 Review and Edit")
    edited_df = st.data_editor(df, num_rows="dynamic", key="editable_table")

    if st.button("✅ Submit to Google Sheet"):
        worksheet.append_rows(edited_df.values.tolist())
        st.success("Data submitted to Google Sheet!")
