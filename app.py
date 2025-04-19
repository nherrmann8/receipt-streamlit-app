
import streamlit as st
import datetime
import pandas as pd
import re
import json
import gspread
from google.oauth2 import service_account
from google.cloud import vision

# === GOOGLE CREDENTIALS ===
credentials_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
credentials = service_account.Credentials.from_service_account_info(credentials_dict)
client = vision.ImageAnnotatorClient(credentials=credentials)

gc = gspread.authorize(credentials)
SHEET_ID = st.secrets["SHEET_ID"]
worksheet = gc.open_by_key(SHEET_ID).worksheet("Sheet1")

# === TITLE ===
st.title("📸 Grocery Receipt Scanner")

uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])
store_name = st.text_input("Store Name", "Unknown")

if uploaded_file:
    image_bytes = uploaded_file.read()
    image = vision.Image(content=image_bytes)

    # Use document_text_detection for better structure
    response = client.document_text_detection(image=image)
    ocr_text = response.full_text_annotation.text
    st.text_area("🔍 Raw OCR Output", ocr_text, height=300)

    # === PARSING ===
    lines = ocr_text.splitlines()
    items = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Match next line as price
        if line and i + 1 < len(lines) and re.match(r"\$\d+\.\d{2}", lines[i + 1].strip()):
            price = float(lines[i + 1].strip().replace('$', ''))
            if not any(kw in line.lower() for kw in ["tax", "total", "visa", "balance", "fee", "deposit"]):
                items.append((line, price))
            i += 2
        else:
            i += 1

    # === BUILD TABLE ===
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    day_str = today.strftime("%A")

    df = pd.DataFrame([{
        "Date": date_str,
        "Day": day_str,
        "Store": store_name.strip(),
        "Item": item,
        "Price": price,
        "Category": "Other"
    } for item, price in items])

    # === DISPLAY TABLE ===
    st.header("📝 Review and Edit")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    if st.button("✅ Submit to Google Sheet"):
        values = edited_df.values.tolist()
        worksheet.append_rows(values)
        st.success("✅ Data submitted to Google Sheets!")
