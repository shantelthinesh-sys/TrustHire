from __future__ import annotations

import json

import streamlit as st

from db_utils import authenticate_admin, get_interview_session, list_interview_sessions, seed_default_admin

st.set_page_config(page_title="Admin Interview Records", page_icon="🗂️", layout="wide")


def init_state() -> None:
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
        st.session_state.admin_user = ""


def login_panel() -> None:
    st.subheader("Admin Login")
    with st.form("admin_login_form", clear_on_submit=False):
        username = st.text_input("Admin Username")
        password = st.text_input("Admin Password", type="password")
        login = st.form_submit_button("Login")

    if login:
        if authenticate_admin(username, password):
            st.session_state.admin_logged_in = True
            st.session_state.admin_user = username
            st.success("Admin login successful.")
            st.rerun()
        else:
            st.error("Invalid admin credentials.")

    st.info("Default admin credentials: admin / admin123 (change this for production).")


def records_panel() -> None:
    st.title("Admin Interview Records")
    st.caption("Review stored interview sessions, risk signals, and evidence logs.")

    top_left, top_right = st.columns([3, 1])
    with top_right:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.admin_user = ""
            st.rerun()

    limit = st.slider("Records to load", min_value=10, max_value=500, value=100, step=10)
    records = list_interview_sessions(limit=limit)

    if not records:
        st.warning("No interview records found yet.")
        return

    st.subheader("Session Table")
    st.dataframe(records, use_container_width=True)

    session_ids = [int(item["id"]) for item in records]
    selected_id = st.selectbox("Select Session ID", options=session_ids)
    item = get_interview_session(int(selected_id))

    if not item:
        st.error("Could not load the selected session.")
        return

    st.subheader("Selected Session Details")

    summary = {
        "id": item.get("id"),
        "candidate": item.get("candidate_username"),
        "status": item.get("status"),
        "started_at": item.get("started_at"),
        "ended_at": item.get("ended_at"),
        "policy_violations": item.get("policy_violations"),
        "reading_alerts": item.get("reading_alerts"),
        "text_integrity_verdict": item.get("text_integrity_verdict"),
        "proctoring_integrity_score": item.get("proctoring_integrity_score"),
        "risk_label": item.get("risk_label"),
        "terminated": bool(item.get("terminated")),
        "eye_away_ratio": item.get("eye_away_ratio"),
    }
    st.json(summary)

    st.subheader("Answers")
    answers = item.get("answers_json") or []
    if not answers:
        st.write("No captured answers.")
    else:
        for idx, ans in enumerate(answers, start=1):
            st.markdown(f"**Q{idx}**: {ans.get('question', '')}")
            st.write(ans.get("answer", ""))
            st.write(
                f"Reading Score: {ans.get('reading_score', 0)} | Label: {ans.get('reading_label', '')}"
            )
            st.divider()

    st.subheader("Violation Log")
    violations = item.get("violations_json") or []
    if not violations:
        st.write("No policy violations logged.")
    else:
        for entry in violations:
            st.write(f"- {entry}")

    export_blob = {
        "summary": summary,
        "answers": answers,
        "violations": violations,
    }
    st.download_button(
        label="Download Session JSON",
        data=json.dumps(export_blob, indent=2),
        file_name=f"session_{selected_id}.json",
        mime="application/json",
    )


init_state()
seed_default_admin()

if not st.session_state.admin_logged_in:
    login_panel()
else:
    records_panel()
