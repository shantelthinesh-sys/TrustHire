# TrustHire Interview Suite

This project includes AI-powered interview quality checks and resume analysis using NLP and Machine Learning.

## Features
- Resume ATS scoring from PDF resumes and job descriptions
- Interview Integrity Check page to estimate if an interview appears proper
- Source Reading Detector page to flag likely reading/copying from external text
- Live Proctored Interview page with candidate login, webcam eye monitoring, and browser policy checks
- Recruiter/Admin login gate before candidate interview starts
- Persistent SQLite storage for interview sessions, answers, and violation logs
- Admin Interview Records page to review and export stored sessions

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
- Admin Interview Records

## Live Proctored Interview Flow
1. Recruiter/Admin logs in and unlocks the interview room
2. Recruiter can rotate/generate a new interview access code
3. Candidate logs in with username, password, and interview code
4. Webcam stream tracks eye direction and face visibility
5. Browser policy checks track tab switching, focus loss, and fullscreen exits
6. Candidate answers are analyzed for possible source reading
7. Session summary is stored automatically in SQLite for admin review

## Default Credentials (Demo)
- Recruiter: recruiter / recruiter123
- Admin: admin / admin123
- Candidate: candidate_demo / demo123

## Persistent Records
- Database file: trusthire.db
- Captures:
	- session timestamps and status
	- policy violations and violation log
	- candidate answers and reading scores
	- integrity/risk summary

## Admin Records Usage
1. Open Admin Interview Records page
2. Login using admin credentials
3. View recent sessions in table format
4. Open session details and export JSON evidence

## Important Note
Detection scores are screening signals only, not definitive proof. Use human review for final decisions.
Browser apps cannot hard-block all OS-level background applications; this app provides detection and flagging, not absolute prevention.
