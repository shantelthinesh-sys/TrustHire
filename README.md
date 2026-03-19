# TrustHire Interview Suite

This project includes AI-powered interview quality checks and resume analysis using NLP and Machine Learning.

## Features
- Resume ATS scoring from PDF resumes and job descriptions
- Interview Integrity Check page to estimate if an interview appears proper
- Source Reading Detector page to flag likely reading/copying from external text
- Live Proctored Interview room with webcam eye monitoring and browser policy checks
- Secure role-based users (admin/recruiter/candidate) in SQLite
- One-time interview token issuance by recruiter
- Persistent forensic records: answers, violations, timestamps, risk outputs
- Admin Control Center for user management, token visibility, records explorer, and JSON export
- Recruiter Ops Studio for interview scheduling, token desk, and invite template generation
- Custom visual theme with modern hero sections and dashboard cards

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
- Recruiter Ops Studio

## Live Proctored Interview Flow
1. Recruiter/Admin logs in and unlocks the interview room
2. Recruiter issues a one-time interview token for a candidate
3. Candidate logs in with username, password, and issued token
4. Webcam stream tracks eye direction and face visibility
5. Browser policy checks track tab switching, focus loss, and fullscreen exits
6. Candidate answers are analyzed for possible source reading
7. Session summary is stored automatically in SQLite for admin review

## Recruiter Ops Studio
1. Recruiter/Admin logs in to operations workspace
2. Schedule interviews with date/time, duration, and notes
3. Auto-issue one-time tokens for scheduled candidates
4. Generate ready-to-send invite text with token and join instructions
5. Manage queue status (scheduled, completed, cancelled)

## Default Credentials (Demo)
- Recruiter: recruiter / recruiter123
- Admin: admin / admin123
- Candidate: candidate_demo / demo123

## Persistent Records
- Database file: trusthire.db
- Captures:
	- recruiter, candidate, one-time token, timestamps, and status
	- policy violations and violation log
	- candidate answers and reading scores
	- integrity/risk summary
	- interview schedules and operational notes

## Admin Records Usage
1. Open Admin Interview Records page
2. Login using admin credentials
3. Review dashboard metrics
4. Manage users and reset passwords
5. Inspect tokens and session records
6. Open session details and export JSON evidence

## Important Note
Detection scores are screening signals only, not definitive proof. Use human review for final decisions.
Browser apps cannot hard-block all OS-level background applications; this app provides detection and flagging, not absolute prevention.
