import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import datetime
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Receipt Scanner", layout="wide")

st.title("📸 Grocery Receipt Scanner")
uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])

reader = easyocr.Reader(['en'], gpu=False)

def parse_items_from_text(text_lines):
    items = []
    for line in text_lines:
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

def upload_to_gsheet(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    secrets = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).worksheet("Receipts")
    rows = data.values.tolist()
    sheet.append_rows(rows)

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    with st.spinner("Reading receipt with OCR..."):
        results = reader.readtext(image)
        lines = [text for (_, text, _) in results]
        items = parse_items_from_text(lines)

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
