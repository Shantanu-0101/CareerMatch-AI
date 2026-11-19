# Career Match AI

An AI-powered career assistance web app for students, fresh graduates and job seekers.
Analyze resumes, find skill gaps for a target role/company, build ATS-friendly resumes,
discover matching jobs and practise interviews.

Built with **Flask, SQLite (SQLAlchemy), Flask-Login, Chart.js** and an optional LLM
(**Google Gemini** or any OpenAI-compatible API). Everything works without an AI key,
using a clearly labelled rule-based fallback.

---

## Features:

| Module | What it does |
|---|---|
| **Authentication** | Register/login / logout, hashed passwords (Werkzeug), sessions (Flask-Login), CSRF protection, per-user data isolation |
| **Dashboard** | Welcome, stats (resumes, latest score, skills, recommended jobs), Chart.js charts, recent activity, quick actions |
| **Resume Analyzer** | Upload PDF/DOCX, extract text, detect sections and skills, score out of 100 with a transparent rubric, strengths/weaknesses/suggestions, company + role skill-gap report |
| **Resume Builder** | Personal details, summary, education, skills, projects, experience, certifications, achievements, languages; add/remove entries; show/hide sections; live preview; 3 templates; saved to DB; PDF download (ReportLab) |
| **Job Finder** | Search by title, skills, location, experience, job type; compatibility score with breakdown; matched and missing skills; bookmark jobs |
| **Interview Practice** | Python, Java, SQL, ML, Data Science, Web Development and HR; 3 difficulty levels; one question at a time; answer evaluation; suggested answer and explanation; progress tracking and history |
| **Profile** | Personal info, education, skills, interests, preferred roles/locations, experience level. Used by job matching and the analyzer |

### Honest by design
* **The resume score is always rule-based.** It comes from a fixed 100-point rubric, and every check is shown on the report. AI only adds written feedback, which is labelled **"AI-generated"**.
* **Detected skills** (found in your file) are shown separately from **missing skills** (rule-based comparison) and **AI-recommended skills**.
* **Job listings are demonstration data** from fictional companies, labelled "Sample" everywhere. They are not real vacancies.
* Company requirement profiles (TCS, Infosys, Google, ...) are **sample, editable lists** in `app/data/skills.py`, not official hiring criteria.

### Scoring rubric (100 points)

| Category | Points | How it's measured |
|---|---|---|
| Technical skills | 20 | 2 points per detected technical skill (max 10) |
| Role keyword relevance | 10 | Share of the target role's skills found |
| Education | 10 | Section 4 · degree named 3 · CGPA/percentage 3 |
| Projects | 15 | Section 5 · enough detail 5 · technologies named 5 |
| Work experience | 15 | Experience/internship section 7 · action verbs 8 |
| Achievements & impact | 10 | Measurable results 6 · certifications/achievements section 4 |
| Formatting & structure | 20 | Email 4 · phone 3 · LinkedIn/GitHub 3 · length 5 · sections 5 |

Job compatibility = **skills 70 + experience level 15 + location 15**.

---

## Getting started

Requires **Python 3.10+**.

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

Open **http://127.0.0.1:5000**, create an account and start.
The SQLite database (`instance/career_match.db`) is created automatically on first run, together with the
sample jobs and the interview question bank.

Two sample resumes are in `sample_data/` (`sample_resume.pdf`, `sample_resume.docx`) to try the analyzer.

### Optional: a virtual environment

```bash
python -m venv .venv
```
Then activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux) and run the two commands above.

---

## Configuration (.env)

Copy `.env.example` to `.env` and edit it:

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs session cookies. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `AI_PROVIDER` | `gemini` (default) or `openai` (any OpenAI-compatible API) |
| `AI_API_KEY` | Your API key. **Leave empty for rule-based mode** |
| `AI_MODEL` | e.g. `gemini-2.5-flash` |
| `AI_BASE_URL` | Only for `openai` provider, e.g. `https://api.groq.com/openai/v1` or `http://localhost:11434/v1` (Ollama) |
| `AI_TIMEOUT` | Seconds before an AI call is abandoned (falls back to rules) |
| `MAX_UPLOAD_MB` | Upload size limit (default 5) |

### Setting up the AI (free options)

**Google Gemini**
1. Get a free API key at https://aistudio.google.com/apikey
2. In `.env`: `AI_PROVIDER=gemini`, `AI_API_KEY=<your key>`, `AI_MODEL=gemini-2.5-flash`
3. Restart `python run.py`. The sidebar shows **"AI enabled"**.

**Local Ollama (no key, runs offline)**
1. Install Ollama and run `ollama pull llama3.1`
2. In `.env`: `AI_PROVIDER=openai`, `AI_API_KEY=ollama`, `AI_MODEL=llama3.1`, `AI_BASE_URL=http://localhost:11434/v1`

If the AI is missing, slow or returns invalid data, the app automatically uses the rule-based
logic and tells the user (a toast plus a note on the report).

With AI enabled you get:
1. Resume analysis feedback (summary, strengths, weaknesses, suggestions)
2. Skill-gap recommendations
3. Resume improvement suggestions
4. AI-generated interview questions
5. AI evaluation of interview answers

All AI responses are requested as JSON and validated before use.

---

## Running the tests

```bash
python -m unittest discover -s tests -t. -v
```

22 end-to-end tests cover registration/login, access control between users, PDF + DOCX upload and
analysis, invalid file rejection, the resume builder and PDF generation for all 3 templates, job search,
bookmarks, the interview flow, profile updates and AI fallback.

---

## Project structure

```
CMA/
├── app/
│   ├── __init__.py           # app factory, blueprints, error handlers, DB init + seeding
│   ├── extensions.py         # db, login_manager, csrf
│   ├── models.py             # User, UserProfile, Resume, ResumeAnalysis, ResumeBuilderData,
│   │                         # Job, SavedJob, InterviewQuestion, InterviewProgress, Activity
│   ├── seed.py               # seeds sample jobs + question bank when tables are empty
│   ├── data/
│   │   ├── skills.py         # skill dictionary, section headings, role & company requirements
│   │   ├── sample_jobs.py    # demonstration job data
│   │   └── question_bank.py  # curated interview questions
│   ├── services/
│   │   ├── ai_service.py         # Gemini / OpenAI-compatible client, JSON validation
│   │   ├── resume_parser.py      # upload validation, PDF/DOCX text extraction, section + skill detection
│   │   ├── resume_analyzer.py    # rubric scoring + optional AI feedback
│   │   ├── resume_builder.py     # builder data defaults + server-side validation
│   │   ├── pdf_generator.py      # ReportLab PDF templates
│   │   ├── job_matcher.py        # job source + compatibility scoring
│   │   └── interview_service.py  # answer evaluation (AI or keyword based)
│   ├── auth/ dashboard/ resume/ jobs/ interview/ profile/   # blueprints (routes.py)
│   ├── templates/            # Jinja2 templates
│   └── static/ css/ js/ images/
├── tests/                    # unittest suite + sample resume generator
├── sample_data/              # sample resumes for trying the analyzer
├── uploads/                  # uploaded resumes (private, never served publicly)
├── instance/                 # SQLite database (created automatically)
├── config.py
├── run.py
├── requirements.txt
└── .env.example
```

### Plugging in a real job API later
`app/services/job_matcher.py` has a `LocalJobSource` class with a `search(...)` method.
Write another class with the same method (for example one that calls a licensed job API and saves
results with `source="api-name"`), then use it in `app/jobs/routes.py`. The "Sample" badge only
appears for jobs whose `source` is `sample`.

---

## Security notes
* Passwords hashed with Werkzeug (`generate_password_hash`).
* CSRF tokens on every form (Flask-WTF `CSRFProtect`).
* Uploads: only `.pdf` / `.docx`, checked by extension **and** file signature, size-limited, saved with random
  names in `uploads/` (outside `static/`), and downloadable only by their owner.
* Every resume, analysis, builder resume, bookmark and interview record is filtered by the logged-in user.
* Server-side validation of all forms; builder data is whitelisted field by field.
* API keys are read from `.env` only, never hard-coded, never sent to the browser.
* Login `next` redirects are restricted to local paths.

## Troubleshooting
* **"No readable text was found"**: the PDF is a scanned image. Export your resume as a text PDF or DOCX.
* **Logged out after restarting**: set a fixed `SECRET_KEY` in `.env`.
* **Reset all data**: stop the server and delete `instance/career_match.db` (and the files in `uploads/`).
