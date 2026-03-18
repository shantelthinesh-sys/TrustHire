import streamlit as st
import pdfplumber
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ui_theme import apply_theme, card, hero

st.set_page_config(page_title="TrustHire Interview Suite", page_icon="🛡️", layout="wide")
apply_theme()

nlp = spacy.load("en_core_web_sm")

skills_db = [
    "python", "machine learning", "data analysis", "sql",
    "java", "deep learning", "c++", "communication", "teamwork"
]

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text()
    return text

def preprocess(text):
    doc = nlp(text.lower())
    tokens = [token.text for token in doc if not token.is_stop and token.is_alpha]
    return " ".join(tokens)

def extract_skills(text):
    return [skill for skill in skills_db if skill in text]

def calculate_ats(resume, job_desc):
    cv = CountVectorizer()
    matrix = cv.fit_transform([resume, job_desc])
    score = cosine_similarity(matrix)[0][1]
    return round(score * 100, 2)

def missing_skills(resume_skills, job_skills):
    return list(set(job_skills) - set(resume_skills))

# UI
hero(
    "TrustHire Interview Suite",
    "AI-first interview integrity platform with proctoring, evidence logs, and ATS resume analysis.",
)
card("Use the left sidebar to open Interview Integrity Check, Source Reading Detector, Live Proctored Interview, and Admin Interview Records.")
st.subheader("Resume Analyzer")

resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
job_desc = st.text_area("Paste Job Description")

if resume_file and job_desc:
    resume_text = extract_text_from_pdf(resume_file)

    clean_resume = preprocess(resume_text)
    clean_job = preprocess(job_desc)

    res_skills = extract_skills(clean_resume)
    job_skills = extract_skills(clean_job)

    score = calculate_ats(clean_resume, clean_job)
    missing = missing_skills(res_skills, job_skills)

    st.subheader(f"ATS Score: {score}%")
    left, right = st.columns(2)
    left.write("✅ Skills Found:", res_skills)
    right.write("❌ Missing Skills:", missing)
