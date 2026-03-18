# TrustHire Interview Suite

This project includes AI-powered interview quality checks and resume analysis using NLP and Machine Learning.

## Features
- Resume ATS scoring from PDF resumes and job descriptions
- Interview Integrity Check page to estimate if an interview appears proper
- Source Reading Detector page to flag likely reading/copying from external text
- Live Proctored Interview page with candidate login, webcam eye monitoring, and browser policy checks

## Tech Stack
- Python
- spaCy
- scikit-learn
- Streamlit

## Run Project
1. Activate environment
	- Windows: venv\Scripts\activate
2. Start app
	- streamlit run app.py

## Pages
- Home: Resume Analyzer
- Interview Integrity Check
- Source Reading Detector
- Live Proctored Interview

## Live Proctored Interview Flow
1. Candidate logs in with username, password, and interview code
2. Webcam stream tracks eye direction and face visibility
3. Browser policy checks track tab switching, focus loss, and fullscreen exits
4. Candidate answers are analyzed for possible source reading
5. Session summary reports violations, reading alerts, and final risk status

## Important Note
Detection scores are screening signals only, not definitive proof. Use human review for final decisions.
Browser apps cannot hard-block all OS-level background applications; this app provides detection and flagging, not absolute prevention.
