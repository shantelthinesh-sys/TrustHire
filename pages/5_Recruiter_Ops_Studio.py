from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from db_utils import (
    attach_token_to_schedule,
    authenticate_user,
    create_interview_token,
    create_schedule,
    list_schedules,
    list_users,
    seed_default_users,
    set_schedule_status,
)
from ui_theme import apply_theme, card, hero

st.set_page_config(page_title="Recruiter Ops Studio", page_icon="🧭", layout="wide")
apply_theme()


def init_state() -> None:
    defaults = {
        "ops_logged_in": False,
        "ops_user": "",
        "last_generated_token": "",
        "invite_preview": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_panel() -> None:
    hero("Recruiter Ops Studio", "Schedule interviews, issue tokens, and prepare ready-to-send invite briefs.")
    with st.form("ops_login_form", clear_on_submit=False):
        username = st.text_input("Recruiter/Admin Username")
        password = st.text_input("Password", type="password")
        login = st.form_submit_button("Enter Ops Studio")

    if login:
        ok = authenticate_user(username.strip().lower(), password, allowed_roles={"recruiter", "admin"})
        if ok:
            st.session_state.ops_logged_in = True
            st.session_state.ops_user = username.strip().lower()
            st.success("Authenticated.")
            st.rerun()
        else:
            st.error("Invalid credentials.")


def compose_invite(candidate: str, token: str, scheduled_for: str, duration: int, notes: str) -> str:
    return (
        f"TrustHire Interview Invite\\n"
        f"Candidate: {candidate}\\n"
        f"Scheduled (UTC): {scheduled_for}\\n"
        f"Duration: {duration} minutes\\n"
        f"One-Time Token: {token}\\n\\n"
        "Join Instructions:\\n"
        "1) Open TrustHire app and go to Live Proctored Interview page.\\n"
        "2) Login with your candidate username/password.\\n"
        "3) Enter the one-time token above in Interview Code field.\\n"
        "4) Keep camera on, remain fullscreen, and do not switch tabs.\\n\\n"
        f"Notes: {notes or 'N/A'}"
    )


def ops_shell() -> None:
    hero("Recruiter Ops Studio", "Plan and launch interviews with one-time token security.")

    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.write(f"Logged in as: {st.session_state.ops_user}")
    with top_r:
        if st.button("Logout"):
            st.session_state.ops_logged_in = False
            st.session_state.ops_user = ""
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["Schedule", "Token Desk", "Queue"])

    candidates = [u["username"] for u in list_users("candidate")]

    with tab1:
        st.subheader("Schedule Interview")
        if not candidates:
            st.warning("No candidate users found. Add candidates from Admin Control Center first.")
        else:
            with st.form("schedule_form", clear_on_submit=False):
                candidate = st.selectbox("Candidate", candidates)
                scheduled_date = st.date_input("Interview Date", value=datetime.utcnow().date() + timedelta(days=1))
                scheduled_time = st.time_input("Interview Time (UTC)", value=datetime.utcnow().time().replace(second=0, microsecond=0))
                duration = st.slider("Duration (minutes)", 15, 120, 30, 5)
                notes = st.text_area("Notes", height=90, placeholder="Role focus, rubric notes, interviewer tips...")
                auto_issue_token = st.toggle("Issue one-time token now", value=True)
                submit = st.form_submit_button("Create Schedule")

            if submit:
                scheduled_dt = datetime.combine(scheduled_date, scheduled_time)
                token = None
                if auto_issue_token:
                    ok, msg, token = create_interview_token(candidate, st.session_state.ops_user, valid_minutes=120)
                    if not ok:
                        st.error(msg)
                        token = None

                ok, msg, schedule_id = create_schedule(
                    candidate_username=candidate,
                    recruiter_username=st.session_state.ops_user,
                    scheduled_for_iso=scheduled_dt.isoformat(),
                    duration_minutes=duration,
                    notes=notes,
                    token=token,
                )
                if ok:
                    st.success(f"Schedule #{schedule_id} created.")
                    if token:
                        st.session_state.last_generated_token = token
                        st.session_state.invite_preview = compose_invite(
                            candidate,
                            token,
                            scheduled_dt.isoformat(),
                            duration,
                            notes,
                        )
                        st.text_area("Invite Preview", st.session_state.invite_preview, height=220)
                else:
                    st.error(msg)

    with tab2:
        st.subheader("Token Desk")
        if not candidates:
            st.warning("No candidate users found.")
        else:
            c1, c2 = st.columns([3, 1])
            candidate_for_token = c1.selectbox("Candidate for token", candidates, key="token_candidate")
            mins = c2.number_input("Valid for (mins)", min_value=5, max_value=360, value=60, step=5)

            if st.button("Generate Token"):
                ok, msg, token = create_interview_token(
                    candidate_username=candidate_for_token,
                    recruiter_username=st.session_state.ops_user,
                    valid_minutes=int(mins),
                )
                if ok:
                    st.session_state.last_generated_token = token
                    st.success(f"Token generated: {token}")
                else:
                    st.error(msg)

            if st.session_state.last_generated_token:
                card(f"Latest token: <b>{st.session_state.last_generated_token}</b>")

    with tab3:
        st.subheader("Interview Queue")
        queue = list_schedules(limit=300)
        if not queue:
            st.info("No schedules yet.")
        else:
            st.dataframe(queue, use_container_width=True)
            ids = [int(item["id"]) for item in queue]
            selected = st.selectbox("Select Schedule", ids)
            selected_item = next((x for x in queue if int(x["id"]) == int(selected)), None)

            if selected_item:
                st.write(selected_item)
                if not selected_item.get("token"):
                    if st.button("Issue and Attach Token"):
                        ok, msg, token = create_interview_token(
                            candidate_username=selected_item["candidate_username"],
                            recruiter_username=st.session_state.ops_user,
                            valid_minutes=120,
                        )
                        if ok and attach_token_to_schedule(int(selected), token):
                            st.success(f"Token attached: {token}")
                            st.rerun()
                        elif not ok:
                            st.error(msg)

                col_a, col_b = st.columns(2)
                if col_a.button("Mark Completed"):
                    if set_schedule_status(int(selected), "completed"):
                        st.success("Schedule marked completed.")
                        st.rerun()
                if col_b.button("Mark Cancelled"):
                    if set_schedule_status(int(selected), "cancelled"):
                        st.success("Schedule marked cancelled.")
                        st.rerun()


init_state()
seed_default_users()

if not st.session_state.ops_logged_in:
    login_panel()
else:
    ops_shell()
