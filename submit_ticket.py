import os

import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = os.environ.get("SRIBHAVA_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "")

st.title("📝 Submit a Support Ticket — Sribhava Retail")

message = st.text_area("Describe your issue:")

if st.button("Submit"):
    if message:
        with st.spinner("Processing your ticket..."):
            try:
                response = requests.post(
                    f"{API_URL}/submit_ticket",
                    json={"message": message},
                    headers={"X-API-Key": API_KEY},
                    timeout=300,
                )
            except requests.exceptions.RequestException:
                st.error("Could not reach the support system. Please try again in a moment.")
            else:
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Ticket #{result['ticket_id']} submitted and processed.")
                elif response.status_code == 401:
                    st.error("The form is not authorised to talk to the support system (API key problem).")
                else:
                    st.error("Something went wrong. A person will look at your ticket if it was saved.")
    else:
        st.warning("Please describe your issue first.")