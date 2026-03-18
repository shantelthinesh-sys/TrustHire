from __future__ import annotations

import time
from datetime import datetime

import av
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer

from integrity_utils import interview_integrity_report, source_reading_report
from proctoring_utils import EyeMovementMonitor, proctoring_risk_level

st.set_page_config(page_title="Live Proctored Interview", page_icon="🎥", layout="wide")

CANDIDATE_CREDENTIALS = {
    "candidate_demo": "demo123",
    "trusthire_test": "pass2026",
}
INTERVIEW_CODE = "TRUSTHIRE2026"
DEFAULT_QUESTIONS = [
    "Tell us about yourself and your recent projects.",
    "Describe a difficult technical problem and how you solved it.",
    "Why are you interested in this role?",
    "Explain one project decision you would change in hindsight.",
]


class ProctorVideoProcessor(VideoProcessorBase):
    def __init__(self) -> None:
        self.monitor = EyeMovementMonitor()
        self.total_frames = 0
        self.look_away_frames = 0
        self.no_face_frames = 0

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        frame_bgr = frame.to_ndarray(format="bgr24")
        annotated, signal = self.monitor.analyze(frame_bgr)

        self.total_frames += 1
        if signal.look_away:
            self.look_away_frames += 1
        if not signal.both_eyes_detected:
            self.no_face_frames += 1

        return av.VideoFrame.from_ndarray(annotated, format="bgr24")


def init_state() -> None:
    defaults = {
        "candidate_logged_in": False,
        "candidate_name": "",
        "interview_active": False,
        "interview_started_at": None,
        "violation_count": 0,
        "violation_log": [],
        "last_state_violation": False,
        "answers": [],
        "reading_alerts": 0,
        "auto_monitor": True,
        "enforce_fullscreen": True,
        "terminated": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def append_violation(reason: str) -> None:
    st.session_state.violation_count += 1
    st.session_state.violation_log.append(
        f"{datetime.now().strftime('%H:%M:%S')} - {reason}"
    )


def monitor_browser_policy() -> dict:
    visibility_state = streamlit_js_eval(
        js_expressions="document.visibilityState",
        key="visibility_state",
    )
    is_focused = streamlit_js_eval(
        js_expressions="document.hasFocus()",
        key="window_focus",
    )
    is_fullscreen = streamlit_js_eval(
        js_expressions="!!document.fullscreenElement",
        key="fullscreen_state",
    )

    visibility = str(visibility_state) if visibility_state is not None else "unknown"
    focused = bool(is_focused) if is_focused is not None else True
    fullscreen = bool(is_fullscreen) if is_fullscreen is not None else False

    return {
        "visibility": visibility,
        "focused": focused,
        "fullscreen": fullscreen,
    }


def login_panel() -> None:
    st.subheader("Candidate Login")
    with st.form("candidate_login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        interview_code = st.text_input("Interview Code")
        login = st.form_submit_button("Login and Start")

    if login:
        valid_user = username in CANDIDATE_CREDENTIALS
        valid_pass = valid_user and CANDIDATE_CREDENTIALS[username] == password
        valid_code = interview_code.strip() == INTERVIEW_CODE

        if valid_user and valid_pass and valid_code:
            st.session_state.candidate_logged_in = True
            st.session_state.candidate_name = username
            st.session_state.interview_active = True
            st.session_state.interview_started_at = time.time()
            st.session_state.terminated = False
            st.success("Login successful. Interview session started.")
            st.rerun()
        else:
            st.error("Invalid login credentials or interview code.")


def interview_panel() -> None:
    st.title("Live Proctored Interview Room")
    st.caption(
        "Meeting-style interview with policy monitoring. This can detect suspicious behavior, "
        "but it cannot hard-block all OS-level background apps from a web browser alone."
    )

    left, right = st.columns([2, 1])

    with right:
        st.write(f"Candidate: {st.session_state.candidate_name}")
        st.session_state.enforce_fullscreen = st.toggle(
            "Require Fullscreen",
            value=st.session_state.enforce_fullscreen,
            help="Counts a violation when fullscreen is exited.",
        )
        st.session_state.auto_monitor = st.toggle(
            "Auto Monitor (2s)",
            value=st.session_state.auto_monitor,
            help="Continuously refresh monitor checks every 2 seconds.",
        )
        max_violations = st.slider("Max Violations", 1, 15, 6)

        if st.button("Logout"):
            st.session_state.candidate_logged_in = False
            st.session_state.interview_active = False
            st.rerun()

    monitor_state = monitor_browser_policy()
    reasons = []

    if monitor_state["visibility"] != "visible":
        reasons.append("Tab hidden or switched")
    if not monitor_state["focused"]:
        reasons.append("Window lost focus")
    if st.session_state.enforce_fullscreen and not monitor_state["fullscreen"]:
        reasons.append("Fullscreen exited")

    is_violation = len(reasons) > 0
    if is_violation and not st.session_state.last_state_violation:
        append_violation("; ".join(reasons))
    st.session_state.last_state_violation = is_violation

    with left:
        st.info(
            "Interview rules: keep this tab visible, keep focus on this window, stay fullscreen, and keep face visible in camera."
        )

        st.write(
            f"Browser state: visibility={monitor_state['visibility']}, "
            f"focused={monitor_state['focused']}, fullscreen={monitor_state['fullscreen']}"
        )

        ctx = webrtc_streamer(
            key="interview-proctor-cam",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"video": True, "audio": False},
            video_processor_factory=ProctorVideoProcessor,
            async_processing=True,
        )

        eye_away_ratio = 0.0
        if ctx and ctx.video_processor:
            vp = ctx.video_processor
            if vp.total_frames > 0:
                eye_away_ratio = vp.look_away_frames / vp.total_frames

            m1, m2, m3 = st.columns(3)
            m1.metric("Frames", vp.total_frames)
            m2.metric("Look-away Frames", vp.look_away_frames)
            m3.metric("No-face Frames", vp.no_face_frames)

    st.divider()
    st.subheader("Question and Response Monitoring")

    question = st.selectbox("Interview Question", DEFAULT_QUESTIONS)
    answer = st.text_area("Candidate Answer", height=160)
    source_text = st.text_area(
        "Optional Reference Source (for reading detection)",
        height=120,
        placeholder="Paste expected notes/script/source text for overlap checking...",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        save_answer = st.button("Save Answer and Analyze", type="primary")
    with col_b:
        end_interview = st.button("End Interview")

    latest_reading_score = 0.0
    if save_answer:
        if not answer.strip():
            st.warning("Please capture an answer first.")
        else:
            reading = source_reading_report(answer, source_text)
            latest_reading_score = reading["suspicion_score"]
            if latest_reading_score >= 65:
                st.session_state.reading_alerts += 1

            st.session_state.answers.append(
                {
                    "question": question,
                    "answer": answer,
                    "reading_score": latest_reading_score,
                    "reading_label": reading["label"],
                }
            )
            st.success("Answer saved and analyzed.")
            st.write(
                f"Reading score: {latest_reading_score}% | Assessment: {reading['label']}"
            )

    if st.session_state.violation_count >= max_violations:
        st.session_state.terminated = True
        st.error("Interview auto-flagged: too many policy violations.")

    transcript = " ".join([item["answer"] for item in st.session_state.answers])
    integrity = interview_integrity_report(transcript, source_text if source_text else "")

    risk = proctoring_risk_level(
        eye_away_ratio=eye_away_ratio,
        violation_count=st.session_state.violation_count,
        reading_suspicion=latest_reading_score,
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Policy Violations", st.session_state.violation_count)
    s2.metric("Reading Alerts", st.session_state.reading_alerts)
    s3.metric("Integrity Score", f"{risk['integrity_score']}%")
    s4.metric("Risk Label", risk["label"])

    if st.session_state.answers:
        st.subheader("Captured Answers")
        for idx, item in enumerate(st.session_state.answers, start=1):
            st.markdown(
                f"**Q{idx}:** {item['question']}  \\\n**Reading Score:** {item['reading_score']}% ({item['reading_label']})"
            )
            st.write(item["answer"])

    if st.session_state.violation_log:
        st.subheader("Violation Log")
        for entry in st.session_state.violation_log[-20:]:
            st.write(f"- {entry}")

    if end_interview:
        st.session_state.interview_active = False
        st.subheader("Final Interview Summary")
        st.write(
            {
                "candidate": st.session_state.candidate_name,
                "answers_count": len(st.session_state.answers),
                "policy_violations": st.session_state.violation_count,
                "reading_alerts": st.session_state.reading_alerts,
                "text_integrity_verdict": integrity["verdict"],
                "proctoring_integrity_score": risk["integrity_score"],
                "terminated": st.session_state.terminated,
            }
        )

    if st.session_state.auto_monitor and st.session_state.interview_active:
        time.sleep(2)
        st.rerun()


init_state()

if not st.session_state.candidate_logged_in:
    st.title("TrustHire Live Interview Access")
    st.caption("Candidate must authenticate before interview can begin.")
    login_panel()
else:
    interview_panel()
