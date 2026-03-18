import streamlit as st

from integrity_utils import interview_integrity_report
from ui_theme import apply_theme, card, hero

st.set_page_config(page_title="Interview Integrity Check", page_icon="🕵️", layout="wide")
apply_theme()

hero(
    "Interview Integrity Check",
    "Assess interview authenticity from transcript behavior and source overlap signals.",
)

card("This is a screening assistant, not final proof. Combine this with human review, live proctoring, and policy controls.")

transcript = st.text_area(
    "Interview Transcript",
    height=260,
    placeholder="Paste candidate responses or full interview transcript...",
)

source_text = st.text_area(
    "Optional: Suspected External Source",
    height=200,
    placeholder="Paste website text, prep script, or answer key to compare against...",
)

if st.button("Run Integrity Analysis", type="primary"):
    if not transcript.strip():
        st.warning("Please provide the transcript first.")
    else:
        report = interview_integrity_report(transcript, source_text)
        metrics = report["metrics"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Integrity Score", f"{report['integrity_score']}%")
        col2.metric("Risk Score", f"{report['risk_score']}%")
        col3.metric("Verdict", report["verdict"])

        st.subheader("Behavior Metrics")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Lexical Diversity", metrics["lexical_diversity"])
        m2.metric("Repetition Ratio", metrics["repetition_ratio"])
        m3.metric("Avg Sentence Len", metrics["avg_sentence_length"])
        m4.metric("Disfluency Rate", metrics["disfluency_rate"])
        m5.metric("Source Similarity", metrics["source_similarity"])

        if report["integrity_score"] >= 70:
            st.success("Result: Interview appears proper based on current signals.")
        elif report["integrity_score"] >= 45:
            st.warning("Result: Some suspicious signals found. Recommend manual review.")
        else:
            st.error("Result: Strong suspicious signals found. Escalate for investigation.")
