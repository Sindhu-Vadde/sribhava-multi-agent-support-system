import streamlit as st
import sqlite3
import streamlit as st
import sqlite3

st.set_page_config(page_title="Sribhava Retail — Ticket Review", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f1420 0%, #1a2233 50%, #0f1420 100%);
}
h1 {
    color: #60a5fa;
    font-weight: 700;
}
.stExpander {
    background-color: #1a2233;
    border: 1px solid #2d3b52;
    border-radius: 10px;
}
.stExpander summary {
    color: #e0e7ff;
    font-weight: 600;
}
p, .stMarkdown {
    color: #cbd5e1;
}
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    border: none;
    padding: 8px 20px;
}
div[data-testid="column"]:nth-of-type(1) .stButton > button {
    background-color: #16a34a;
    color: white;
}
div[data-testid="column"]:nth-of-type(1) .stButton > button:hover {
    background-color: #22c55e;
}
div[data-testid="column"]:nth-of-type(2) .stButton > button {
    background-color: #dc2626;
    color: white;
}
div[data-testid="column"]:nth-of-type(2) .stButton > button:hover {
    background-color: #ef4444;
}
</style>
""", unsafe_allow_html=True)


st.title("🎫 Sribhava Retail — Ticket Review Dashboard")

conn = sqlite3.connect("tickets.db")
cursor = conn.cursor()

cursor.execute("SELECT id, message, category, intent, status, agent_reasoning FROM tickets WHERE status = 'pending_human_review'")
pending_tickets = cursor.fetchall()

conn.close()

st.write(f"**{len(pending_tickets)} ticket(s) awaiting review**")

for ticket in pending_tickets:
    ticket_id, message, category, intent, status, agent_reasoning = ticket

    with st.expander(f"Ticket #{ticket_id} — {category} / {intent}"):
        st.write("**Customer message:**", message)
        st.write("**Agent reasoning:**", agent_reasoning)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Approve", key=f"approve_{ticket_id}"):
                conn = sqlite3.connect("tickets.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket_id,))
                conn.commit()
                conn.close()
                st.success(f"Ticket #{ticket_id} approved and resolved.")
                st.rerun()

        with col2:
            if st.button("❌ Reject", key=f"reject_{ticket_id}"):
                conn = sqlite3.connect("tickets.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE tickets SET status = 'rejected' WHERE id = ?", (ticket_id,))
                conn.commit()
                conn.close()
                st.warning(f"Ticket #{ticket_id} rejected.")
                st.rerun()