import streamlit as st

from integrity_utils import source_reading_report
from ui_theme import apply_theme, card, hero

st.set_page_config(page_title="Source Reading Detector", page_icon="📄", layout="wide")
apply_theme()

hero(
    "Source Reading Detector",
    "Detect likely reading or copying behavior by comparing candidate responses against known source text.",
)
card("Use this page during or after interviews to quantify overlap risk and prioritize manual review.")

candidate_answer = st.text_area(
    "Candidate Answer",
    height=220,
    placeholder="Paste the candidate's spoken/written answer...",
)

reference_source = st.text_area(
    "Reference Source Text",
    height=220,
    placeholder="Paste suspected source text (web page, notes, script, etc.)...",
)

if st.button("Detect Source Reading", type="primary"):
    if not candidate_answer.strip() or not reference_source.strip():
        st.warning("Please provide both candidate answer and source text.")
    else:
        report = source_reading_report(candidate_answer, reference_source)
        metrics = report["metrics"]

        c1, c2 = st.columns(2)
        c1.metric("Suspicion Score", f"{report['suspicion_score']}%")
        c2.metric("Assessment", report["label"])

        st.subheader("Similarity Breakdown")
        s1, s2, s3 = st.columns(3)
        s1.metric("Cosine Similarity", metrics["cosine_similarity"])
        s2.metric("Sequence Similarity", metrics["sequence_similarity"])
        s3.metric("Exact Sentence Match", metrics["exact_sentence_match_ratio"])

        if report["suspicion_score"] >= 75:
            st.error("High overlap detected. Candidate may be reading from source.")
        elif report["suspicion_score"] >= 45:
            st.warning("Moderate overlap detected. Recommend manual verification.")
        else:
            st.success("Low overlap detected with provided source text.")
