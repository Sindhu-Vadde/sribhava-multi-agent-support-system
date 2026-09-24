import streamlit as st
import requests

st.title("📝 Submit a Support Ticket — Sribhava Retail")

message = st.text_area("Describe your issue:")

if st.button("Submit"):
    if message:
        with st.spinner("Processing your ticket..."):
            response = requests.post("http://localhost:8000/submit_ticket", json={"message": message})
            if response.status_code == 200:
                result = response.json()
                st.success(f"Ticket #{result['ticket_id']} submitted and processed.")
            else:
                st.error("Something went wrong.")
    else:
        st.warning("Please describe your issue first.")