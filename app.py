import streamlit as st
import json
from main import sync_and_analyze_emails
from database import init_db, get_history, get_latest_email_record

# --- Initialize ---
init_db()

st.set_page_config(page_title="AI Email Agent", page_icon="✉️", layout="wide")

# Injection of custom CSS for layout and metrics
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        white-space: normal !important;
        word-break: break-word !important;
    }
    .analysis-card {
        background-color: #15171C;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        padding: 24px;
        color: #E5E7EB;
        margin-bottom: 20px;
    }
    .card-zone {
        padding: 12px 0;
        border-bottom: 0.5px solid rgba(255, 255, 255, 0.08);
    }
    .card-zone:last-child { border-bottom: none; }
    .field-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #9CA3AF;
        margin-bottom: 4px;
    }
    .pill-badge {
        display: inline-flex;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 500;
    }
    .badge-info { background-color: rgba(59, 130, 246, 0.15); color: #60A5FA; }
    .badge-amber { background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; }
    .badge-neutral { background-color: rgba(156, 163, 175, 0.15); color: #9CA3AF; }
    .left-accent-strip {
        background-color: rgba(255, 255, 255, 0.02);
        border-left: 3px solid #34D399;
        padding: 10px 14px;
        border-radius: 0 4px 4px 0;
        font-size: 13px;
    }
    .progress-container { background: rgba(255,255,255,0.1); border-radius: 10px; height: 4px; margin-top: 6px; }
    .progress-bar { background: #34D399; height: 4px; border-radius: 10px; }
    .entity-chip {
        display: inline-block;
        background: rgba(255,255,255,0.05);
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        margin: 2px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
</style>
""", unsafe_allow_html=True)

# --- Helper Function to Render Analysis ---
def render_analysis_card(record):
    """Renders a single high-fidelity analysis card from a database record."""
    raw_category = record.get("category", "Uncategorized")
    clean_category = str(raw_category).replace("_", " ").replace(".", "").strip().title()
    
    priority_level = record.get("priority", "low").lower()
    priority_reason = record.get("priority_reason", "No reason provided.")
    sentiment_val = record.get("sentiment", "neutral").capitalize()
    actionability_val = str(record.get('actionability', '')).replace("_", " ").title()
    
    confidence = float(record.get('confidence', 0.5))
    
    p_badge = "badge-info"
    if priority_level == "high": p_badge = "badge-amber"
    elif priority_level == "medium": p_badge = "badge-neutral"

    # HTML Construction
    html = f'<div class="analysis-card">'
    
    # Zone 1
    html += f'<div class="card-zone grid-3">'
    html += f'<div><div class="field-label">Category</div><div class="pill-badge badge-info">{clean_category}</div></div>'
    html += f'<div><div class="field-label">Priority</div><div class="pill-badge {p_badge}">{priority_level.upper()}</div></div>'
    html += f'<div><div class="field-label">Sentiment</div><div class="pill-badge badge-info">{sentiment_val}</div></div>'
    html += f'</div>'

    # Zone 2
    html += f'<div class="card-zone"><div class="left-accent-strip"><strong>Reason:</strong> {priority_reason}</div></div>'

    # Zone 3
    html += f'<div class="card-zone grid-2">'
    html += f'<div><div class="field-label">AI Confidence ({confidence:.0%})</div><div class="progress-container"><div class="progress-bar" style="width:{confidence*100}%"></div></div></div>'
    html += f'<div><div class="field-label">Actionability</div><div class="pill-badge badge-amber">{actionability_val}</div></div>'
    html += f'</div>'

    # Zone 4
    deadline = record.get("deadline") or "None"
    html += f'<div class="card-zone grid-3">'
    html += f'<div><div class="field-label">Requires Reply</div><div style="font-size:14px">{"Yes" if record.get("requires_response") else "No"}</div></div>'
    html += f'<div><div class="field-label">Follow Up</div><div style="font-size:14px">{"Yes" if record.get("follow_up_needed") else "No"}</div></div>'
    html += f'<div><div class="field-label">Deadline</div><div style="font-size:14px; color:#60A5FA">{deadline}</div></div>'
    html += f'</div>'

    # Zone 5
    html += f'<div class="card-zone"><div class="field-label">Summary</div><div style="font-size:13px; line-height:1.4">{record.get("summary")}</div></div>'

    # Zone 6
    html += f'<div class="card-zone"><div class="field-label">Action Items</div>'
    actions = record.get("actions", [])
    if isinstance(actions, list) and actions:
        for i, act in enumerate(actions, 1):
            html += f'<div style="font-size:13px; margin-bottom:4px"><span style="color:#60A5FA">{i}.</span> {act}</div>'
    else:
        html += '<div style="font-size:12px; color:#6B7280; font-style:italic">None identified</div>'
    html += f'</div>'

    # Zone 7
    html += f'<div class="card-zone grid-3">'
    entities = record.get("entities", {})
    for key, label in [("people", "People"), ("companies", "Companies"), ("dates", "Dates")]:
        html += f'<div><div class="field-label">{label}</div>'
        items = entities.get(key, []) if isinstance(entities, dict) else []
        if items:
            for it in items: html += f'<span class="entity-chip">{it}</span>'
        else:
            html += '<div style="font-size:11px; color:#6B7280">None</div>'
        html += '</div>'
    html += f'</div></div>'
    
    st.markdown(html, unsafe_allow_html=True)

# --- App UI ---
st.title("AI Email Agent")
tab_sync, tab_history = st.tabs(["📥 Inbox Sync", "📜 History Log"])

with tab_sync:
    st.subheader("Fetch & Analyze")
    max_emails = st.number_input("Emails to fetch:", 1, 10, 3)

    if st.button("Sync Inbox", type="primary"):
        try:
            with st.spinner("Analyzing..."):
                stats = sync_and_analyze_emails(limit=max_emails)
            
            if stats["new"] > 0:
                st.success(f"Analyzed {stats['new']} new email(s).")
            else:
                st.info("No new emails found.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    
    # LOGIKA PRO ZOBRAZENÍ VŠECH NOVÝCH BLOKŮ
    st.subheader("Recent Session Results")
    # Získáme historii a omezíme ji na počet právě stažených e-mailů (nebo posledních 5)
    recent_records = get_history(limit=max_emails)
    
    if recent_records:
        for record in recent_records:
            with st.container():
                st.caption(f"📧 From: {record.get('gmail_id')} | Processed at: {record.get('timestamp')}")
                render_analysis_card(record)
    else:
        st.info("No data in database yet.")

with tab_history:
    st.subheader("All Database Records")
    all_history = get_history(limit=50) # Zobrazíme až 50 posledních logů
    
    if not all_history:
        st.info("History is empty.")
    else:
        for record in all_history:
            # Použijeme expander, aby historie nebyla kilometr dlouhá, 
            # ale uvnitř bude ta stejná krásná karta.
            exp_label = f"[{record['priority'].upper()}] {record['summary'][:60]}... ({record['timestamp']})"
            with st.expander(exp_label):
                render_analysis_card(record)