# INTERVIEWR

<div align="center">

  <img alt="INTERVIEWR" src="https://img.shields.io/badge/INTERVIEWR-AI%20Interview%20Platform-111827?style=for-the-badge&labelColor=2563eb&color=0f172a" />
  <img alt="React" src="https://img.shields.io/badge/Frontend-React%2018-0f172a?style=for-the-badge&logo=react&logoColor=61dafb" />
  <img alt="FastAPI" src="https://img.shields.io/badge/Backend-FastAPI-0f172a?style=for-the-badge&logo=fastapi&logoColor=22c55e" />
  <img alt="MongoDB" src="https://img.shields.io/badge/Database-MongoDB-0f172a?style=for-the-badge&logo=mongodb&logoColor=22c55e" />
  <img alt="AI" src="https://img.shields.io/badge/AI-Gemini%20%2B%20Ollama-0f172a?style=for-the-badge" />

  <br />
  <br />

  <h3>A layered AI interview platform for technical, HR, resume-based, voice, aptitude, and coding preparation.</h3>

  <p>
    Practice like a real candidate. Get evaluated like a real round. Improve with report-driven feedback.
  </p>

  <p>
    <a href="YOUR_DEPLOYED_WEBSITE_URL_HERE"><strong>Live Website</strong></a> |
    <a href="#overview"><strong>Overview</strong></a> |
    <a href="#how-it-works"><strong>How It Works</strong></a> |
    <a href="#feature-architecture"><strong>Architecture</strong></a> |
    <a href="#local-development"><strong>Run Locally</strong></a>
  </p>

</div>

---

## Overview

INTERVIEWR is a full-stack AI interview preparation platform that combines multiple preparation flows inside one system:

- technical interview practice
- HR and behavioral interview simulation
- resume-based adaptive interview rounds
- aptitude and mock test experience
- coding challenge generation and evaluation
- report-based progress review

Instead of behaving like a plain quiz website, INTERVIEWR acts more like a complete interview workspace. It starts from user setup, adapts the flow based on context, evaluates performance, and ends with a structured report that helps the user understand what to improve next.

---

## Visual Product View

```text
                          INTERVIEWR EXPERIENCE STACK

         +-----------------------------------------------------------+
         |                      REPORT LAYER                         |
         |  scores | radar graph | strengths | gaps | retry flow    |
         +-------------------------------+---------------------------+
                                         |
         +-------------------------------v---------------------------+
         |                    INTERVIEW ENGINE                       |
         |  HR | Technical | Resume | Voice | Aptitude | Coding     |
         +-------------------------------+---------------------------+
                                         |
         +-------------------------------v---------------------------+
         |                     INTELLIGENCE LAYER                    |
         |     Gemini | Ollama | adaptive prompts | evaluation      |
         +-------------------------------+---------------------------+
                                         |
         +-------------------------------v---------------------------+
         |                    APPLICATION CORE                       |
         | React UI | FastAPI APIs | MongoDB | Auth | Session Data   |
         +-----------------------------------------------------------+
```

This is the best way to think about the project: not as one page, but as stacked layers working together.

---

## What The Project Does

INTERVIEWR helps a user move through a realistic preparation cycle:

1. create an account or sign in
2. choose the interview mode
3. optionally upload a resume
4. start a live interview, aptitude exam, or coding round
5. answer through text, voice, or code
6. get AI-backed evaluation
7. review a structured report and practice again

That end-to-end loop is the heart of the project.

---

## How It Works

## 1. User Entry

The user enters through authentication, then lands on a dashboard where they can start different preparation flows.

Supported flows include:

- HR interview
- technical interview
- mock interview
- voice interview
- resume interview
- aptitude exam
- coding round

## 2. Context Building

Before the session begins, INTERVIEWR collects useful context such as:

- selected role
- selected language or subject
- experience level
- interview category
- resume signals, when resume mode is used

This context is then used to shape the next questions and the evaluation style.

## 3. AI-driven Session Flow

The backend creates interview sessions dynamically. Questions are generated or selected according to the mode:

- HR mode focuses on communication, confidence, behavioral thinking, and readiness
- technical mode focuses on concepts, logic, practical thinking, and depth
- resume mode uses extracted resume skills to guide adaptive questioning
- aptitude mode creates section-based question sets
- coding mode generates coding challenges, test cases, and solution review

## 4. Evaluation Layer

Once the user responds:

- interview answers are evaluated by the AI layer
- coding answers are checked against public and hidden test cases
- aptitude responses are scored directly
- session data is normalized into saved report-friendly structures

## 5. Report Layer

The final report is where the platform becomes genuinely useful.

It summarizes:

- overall performance
- question-wise score
- strengths
- mistakes and gaps
- spider-web / radar graph
- skill breakdown
- suggested next direction

---

## Key Features

### Interview System

- multi-mode interview setup
- realistic HR and technical rounds
- adaptive interview generation
- natural conversational flow
- follow-up style evaluation
- report-ready session persistence

### Resume Intelligence

- PDF resume upload
- extracted resume text
- structured resume signals
- skill-based adaptive interview path
- analyzed resume flow before interview start

### Voice Experience

- microphone-based answering flow
- camera + microphone permissions
- speech synthesis support
- speech recognition aware interaction
- fullscreen-focused interview experience

### Aptitude Engine

- aptitude practice
- advanced quantitative ability
- reasoning questions
- verbal questions
- computer fundamentals
- mock aptitude distribution
- timed exam behavior

### Coding Engine

- AI-generated coding challenges
- difficulty-based question generation
- code execution against test cases
- public + hidden case checking
- code review summary
- reference solution generation
- coding answers shown in report format

### Reports and Review

- saved report pages
- per-question analysis
- strengths and gap display
- radar / spider-web graph
- score trend blocks
- retry / practice again flow

### Account and Access

- email/password authentication
- Google sign-in
- email verification
- password reset flow
- saved user progress

---

## Feature Architecture

```text
Frontend Layer
  |
  |-- Auth and account pages
  |-- Dashboard and navigation
  |-- Interview setup and interview screens
  |-- Resume analyzer and resume interview pages
  |-- Aptitude and coding pages
  `-- Reports and review pages

Backend Layer
  |
  |-- Authentication APIs
  |-- Interview session APIs
  |-- Resume extraction APIs
  |-- Coding challenge and code execution APIs
  |-- Aptitude generation APIs
  `-- Report persistence and retrieval APIs

AI Layer
  |
  |-- Gemini provider
  |-- Ollama fallback
  |-- Interview question generation
  |-- Answer evaluation
  |-- Coding review and reference solution generation
  `-- Summary and report assistance

Data Layer
  |
  `-- MongoDB collections for users, sessions, and ratings
```

---

## Product Modules

| Module | Purpose |
|---|---|
| Auth | Sign up, sign in, Google login, email verification, password reset |
| Dashboard | Entry point for practice flows and saved progress |
| HR Interview | Communication, confidence, behavior, readiness evaluation |
| Technical Interview | Role/language-focused practical interview flow |
| Resume Interview | Resume-aware adaptive questioning |
| Voice Interview | Spoken interview interaction with camera/mic support |
| Aptitude Test | Timed objective preparation across multiple categories |
| Coding Round | Coding challenge solving, submission, evaluation, reference answer |
| Reports | Final performance review with graph and analysis |

---

## Tech Stack

### Frontend

- React 18
- React Router DOM
- Axios
- Lucide React
- React Webcam
- React Easy Crop

### Backend

- FastAPI
- Pydantic
- Motor
- MongoDB
- Python execution utilities
- JWT-based auth flow

### AI and Evaluation

- Google Gemini
- Ollama
- adaptive prompt-based generation
- answer scoring and summarization
- coding reference solution generation

---

## Database and Storage

The backend uses MongoDB through Motor and stores major platform data such as:

- users
- interview sessions
- report ratings

This allows the platform to preserve session history, saved reports, and user-specific progress over time.

---

## Why INTERVIEWR Feels Different

Many interview prep projects stop at question generation. INTERVIEWR goes further:

- it creates a flow, not just a prompt
- it supports multiple interview categories in one system
- it connects resume analysis with adaptive questioning
- it includes coding execution, not only text feedback
- it keeps reports grounded in captured session data
- it supports repeated practice using saved outcomes

That makes it feel more like a preparation platform and less like a simple AI demo.

---

## Project Structure

```text
MAJOR_PROJECT/
|-- backend/
|   |-- main.py
|   |-- interview_ai.py
|   |-- coding_ai.py
|   |-- database.py
|   |-- auth_utils.py
|   |-- config.py
|   |-- uploads/
|   |-- face_db/
|   `-- .env
|-- frontend/
|   `-- ai-interview-ui/
|       |-- src/
|       |-- public/
|       `-- package.json
|-- CHANGELOG.md
`-- README.md
```

---

## Deployment Space

Keep this section for your production launch.

- **Website URL:** `YOUR_DEPLOYED_WEBSITE_URL_HERE`
- **Frontend URL:** `YOUR_FRONTEND_URL_HERE`
- **Backend API URL:** `YOUR_BACKEND_URL_HERE`
- **Demo / access note:** `ADD_IF_NEEDED`

---

## Suggested README Add-ons Later

To make this README even stronger after deployment, you can add:

- homepage screenshot
- dashboard screenshot
- interview page screenshot
- report page screenshot
- short demo GIF
- architecture image

---

## Local Development

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd MAJOR_PROJECT
```

### 2. Frontend setup

```bash
cd frontend/ai-interview-ui
npm install
```

Create a frontend `.env` file if needed:

```env
REACT_APP_API_URL=http://127.0.0.1:8000
REACT_APP_API_BASE=http://127.0.0.1:8000
REACT_APP_GOOGLE_CLIENT_ID=your_google_client_id
```

Run the frontend:

```bash
npm start
```

### 3. Backend setup

Open a new terminal:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn motor pymongo python-dotenv python-jose passlib bcrypt google-auth numpy python-multipart
```

Configure `backend/.env`:

```env
MONGO_URL=your_mongodb_connection_string
SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GEMINI_API_KEY=your_gemini_api_key
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
REACT_APP_FRONTEND_BASE=http://localhost:3000
RESET_EMAIL_FROM=your_email
RESET_EMAIL_SMTP_HOST=your_smtp_host
RESET_EMAIL_SMTP_PORT=587
RESET_EMAIL_SMTP_USER=your_smtp_user
RESET_EMAIL_SMTP_PASS=your_smtp_password
RESET_EMAIL_BASE_URL=http://localhost:3000
```

Run the backend:

```bash
uvicorn main:app --reload
```

### 4. Open the application

- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`

---

<div align="center">
  <strong>INTERVIEWR</strong><br />
  Built to make interview preparation feel structured, realistic, and measurable.
</div>
