import streamlit as st
import pandas as pd
import base64
import json
import datetime
from google.oauth2 import service_account
from google.cloud import vision

st.set_page_config(page_title="Receipt Scanner", layout="wide")
st.title("📸 Grocery Receipt Scanner")

uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])

def parse_items_from_text(text):
    lines = text.split("\n")
    items = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                price = float(parts[-1].replace('$', '').replace(',', ''))
                name = ' '.join(parts[:-1])
                items.append({"Item": name, "Price": price})
            except ValueError:
                continue
    return items

def categorize_item(item_name):
    item_name = item_name.lower()
    if any(x in item_name for x in ["chips", "cookie", "candy"]):
        return "Snacks"
    elif any(x in item_name for x in ["soap", "toothpaste", "shampoo"]):
        return "Toiletries"
    elif any(x in item_name for x in ["soda", "juice", "coffee"]):
        return "Drinks"
    elif any(x in item_name for x in ["chicken", "beef", "pasta", "rice"]):
        return "Dinner"
    else:
        return "Other"

def extract_text_google_vision(image_bytes):
    credentials_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(credentials_dict)
    client = vision.ImageAnnotatorClient(credentials=creds)
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return ""

def upload_to_gsheet(data):
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    secrets = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).worksheet("Receipts")
    rows = data.values.tolist()
    sheet.append_rows(rows)

if uploaded_file:
    image_bytes = uploaded_file.read()
    st.image(image_bytes, caption="Uploaded Receipt", use_column_width=True)

    with st.spinner("Extracting text from image..."):
        text = extract_text_google_vision(image_bytes)
        items = parse_items_from_text(text)

    if items:
        df = pd.DataFrame(items)
        df["Category"] = df["Item"].apply(categorize_item)

        today = datetime.date.today()
        df.insert(0, "Date", today.isoformat())
        df.insert(1, "Day", today.strftime("%A"))
        store = st.text_input("Store Name", value="Unknown")
        df.insert(2, "Store", store)

        st.subheader("📋 Review and Edit")
        edited_df = st.data_editor(df, num_rows="dynamic")

        if st.button("✅ Submit to Google Sheet"):
            upload_to_gsheet(edited_df)
            st.success("Uploaded successfully!")
    else:
        st.warning("No items detected.")
