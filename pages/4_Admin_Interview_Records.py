from __future__ import annotations

import json

import streamlit as st

from db_utils import (
    authenticate_admin,
    change_user_password,
    create_user,
    dashboard_stats,
    get_interview_session,
    list_interview_sessions,
    list_interview_tokens,
    list_users,
    seed_default_users,
)
from ui_theme import apply_theme, card, hero

st.set_page_config(page_title="Admin Interview Records", page_icon="🗂️", layout="wide")
apply_theme()


def init_state() -> None:
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
        st.session_state.admin_user = ""


def login_panel() -> None:
    hero("Admin Control Center", "Manage users, interview tokens, and forensic session evidence.")
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

    card("Default admin credentials: admin / admin123. Change this immediately for production.")


def users_panel() -> None:
    st.subheader("User Management")
    users = list_users()
    st.dataframe(users, use_container_width=True)

    with st.form("create_user_form", clear_on_submit=True):
        st.markdown("**Create User**")
        username = st.text_input("Username", key="create_username")
        password = st.text_input("Temporary Password", type="password", key="create_password")
        role = st.selectbox("Role", ["candidate", "recruiter", "admin"], key="create_role")
        force_change = st.toggle("Require password reset on first login", value=True)
        submit = st.form_submit_button("Create User")

    if submit:
        ok, msg = create_user(username, password, role, must_change_password=force_change)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("**Reset Password**")
    names = [u["username"] for u in users]
    if names:
        reset_user = st.selectbox("User", names)
        reset_pwd = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            if not reset_pwd:
                st.warning("Password cannot be empty.")
            elif change_user_password(reset_user, reset_pwd, must_change_password=True):
                st.success("Password reset complete.")
            else:
                st.error("User not found.")


def tokens_panel() -> None:
    st.subheader("Interview Tokens")
    tokens = list_interview_tokens(limit=300)
    if not tokens:
        st.info("No interview tokens issued yet.")
        return
    st.dataframe(tokens, use_container_width=True)


def records_panel() -> None:
    st.subheader("Interview Session Records")
    limit = st.slider("Records to load", min_value=10, max_value=500, value=100, step=10)
    records = list_interview_sessions(limit=limit)

    if not records:
        st.warning("No interview records found yet.")
        return

    st.dataframe(records, use_container_width=True)

    session_ids = [int(item["id"]) for item in records]
    selected_id = st.selectbox("Select Session ID", options=session_ids)
    item = get_interview_session(int(selected_id))

    if not item:
        st.error("Could not load the selected session.")
        return

    summary = {
        "id": item.get("id"),
        "candidate": item.get("candidate_username"),
        "recruiter": item.get("recruiter_username"),
        "interview_token": item.get("interview_token"),
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

    st.subheader("Selected Session")
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


def dashboard_panel() -> None:
    stats = dashboard_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Candidates", stats["active_candidates"])
    c2.metric("Recruiters", stats["active_recruiters"])
    c3.metric("Sessions", stats["sessions"])
    c4.metric("Flagged", stats["flagged_sessions"])
    c5.metric("Active Tokens", stats["active_tokens"])
    card("Use the tabs below to manage users, inspect tokens, and review interview evidence records.")


def admin_shell() -> None:
    hero("Admin Control Center", "Operational cockpit for interview governance and evidence review.")
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.write(f"Logged in as: {st.session_state.admin_user}")
    with top_right:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.admin_user = ""
            st.rerun()

    t1, t2, t3, t4 = st.tabs(["Overview", "Users", "Tokens", "Records"])
    with t1:
        dashboard_panel()
    with t2:
        users_panel()
    with t3:
        tokens_panel()
    with t4:
        records_panel()


init_state()
seed_default_users()

if not st.session_state.admin_logged_in:
    login_panel()
else:
    admin_shell()
