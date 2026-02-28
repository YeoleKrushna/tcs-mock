# TCS NQT 2026 – Proctored Online Examination Platform

> **Made By KRUSHNA YEOLE © 2026**

A full-stack Python/Flask exam platform with PostgreSQL (Render), modelled after TCS iON NQT.

---

## 🚀 Quick Deploy on Render

1. **Push to GitHub** (see below)
2. **Connect repo to Render** → New Web Service
3. Set **Environment Variable**: `DATABASE_URL` = your PostgreSQL connection string
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

The database tables & seed data are created **automatically on first start**.

---

## 🖥️ Push to GitHub

```bash
cd tcs_nqt_exam
git init
git add .
git commit -m "TCS NQT 2026 - Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/tcs-nqt-2026.git
git push -u origin main
```

---

## 🔑 Demo Credentials

| Role      | Email                 | Password  |
|-----------|-----------------------|-----------|
| Candidate | candidate@tcs.com     | test123   |
| Admin     | admin@tcs.com         | admin123  |

---

## 📁 Project Structure

```
tcs_nqt_exam/
├── app.py                      # Flask app + PostgreSQL backend
├── requirements.txt            # psycopg2-binary, flask, gunicorn
├── Procfile                    # For Render / Heroku
├── render.yaml                 # Render deployment config
├── .gitignore
├── templates/
│   ├── login.html              # Candidate & admin login
│   ├── instructions.html       # Rules + camera permission
│   ├── exam.html               # Main exam interface
│   ├── result.html             # Score + section breakdown
│   ├── admin.html              # Full admin dashboard
│   ├── admin_questions.html    # Per-section question manager
│   ├── add_question.html       # Add question (text + image + position)
│   ├── edit_question.html      # Edit any question
│   ├── edit_user.html          # Edit candidate details
│   └── admin_result_view.html  # Admin view of any candidate result
├── static/
│   ├── css/style.css           # Exam UI stylesheet
│   ├── js/exam.js              # Timer + security + navigation
│   └── uploads/                # Question images
```

---

## 🎯 Features

### Exam
- 4 sections: Verbal (25Q), Reasoning (20Q), Numerical (20Q), Advanced (15Q)
- Per-section timers with localStorage persistence
- Auto-advance to next section when time ends
- Auto-submit on last section timeout

### Security / Proctoring
- Live camera feed in exam header (display only)
- Tab switch detection → 2-strike auto-submit
- Fullscreen enforcement
- Right-click, copy/paste, F12 all disabled
- Violations logged to PostgreSQL

### Admin Panel
- **Dashboard**: stats, question bank overview, candidate list
- **Question Manager**: view/edit/delete per section with position control
- **Add Question**: set position number (shifts existing questions)
- **Edit Question**: change text, options, correct answer, image, marks, position
- **Create User**: name, email, password, phone, college, roll number
- **Edit User**: update all fields, reset password
- **Reset Exam**: clear responses so candidate can retake
- **View Result**: full section-wise breakdown for any candidate
- **Delete User**: remove all associated data

---

© 2026 TCS NQT Online Assessment Platform · Made By **KRUSHNA YEOLE**
