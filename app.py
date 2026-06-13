import sqlite3
import os
import random
import pdfplumber
import docx
from PIL import Image
import pytesseract

from flask import Flask, render_template, request, session, redirect

app = Flask(__name__)
app.secret_key = "smart_interview_secret"

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- AI QUESTIONS ----------------
def generate_ai_questions(skill):
    return [
        f"What is {skill}?",
        f"Explain {skill} with example",
        f"Where is {skill} used in real world?"
    ]

# ---------------- AI SUGGESTIONS ----------------
def ai_suggestions(text, ats_score):
    text = text.lower()
    suggestions = []

    if "project" not in text:
        suggestions.append("Add projects to improve your resume strength.")

    if "experience" not in text:
        suggestions.append("Add internship or work experience section.")

    if len(text.split()) < 150:
        suggestions.append("Resume is too short. Add more details.")

    if ats_score < 40:
        suggestions.append("Low ATS score. Improve structure and skills.")
    elif ats_score < 70:
        suggestions.append("Moderate ATS score. Improve projects and skills.")
    else:
        suggestions.append("Good resume. Add advanced projects for better ranking.")

    return suggestions

# ---------------- HOME ----------------
@app.route('/')
def home():
    return "Smart Interview Assistant is working!"

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (request.form['name'], request.form['email'], request.form['password'])
        )
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (request.form['email'], request.form['password'])
        ).fetchone()
        conn.close()

        if user:
            session['user'] = user['name']
            return redirect('/dashboard')
        else:
            return "Invalid Login"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template("dashboard.html", name=session['user'])
    return redirect('/login')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------------- UPLOAD ----------------
#upload
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        os.makedirs("uploads", exist_ok=True)

        file = request.files['resume']
        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)

        text = ""

        if file.filename.endswith(".pdf"):
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

        elif file.filename.endswith(".docx"):
            doc = docx.Document(filepath)
            for p in doc.paragraphs:
                text += p.text + " "

        elif file.filename.endswith((".png", ".jpg", ".jpeg")):
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)

        skills = ["python", "java", "sql", "html", "css", "javascript"]

        detected = []
        questions = []

        for s in skills:
            if s in text.lower():
                detected.append(s)
                questions.extend(generate_ai_questions(s))

        # ATS SCORE
        keywords = ["python", "java", "sql", "html", "css"]
        match = sum(1 for k in keywords if k in text.lower())
        ats_score = int((match / len(keywords)) * 100)

        # AI suggestions
        suggestions = ai_suggestions(text, ats_score)

        session['questions'] = questions

        return render_template(
            "test.html",
            skills=detected,
            questions=questions,
            ats_score=ats_score,
            suggestions=suggestions
        )

    return render_template("upload.html")
# ---------------- EVALUATION ----------------
@app.route('/evaluate', methods=['POST'])
def evaluate():
    answers = request.form
    questions = session.get('questions', [])

    score = 0

    for i, answer in enumerate(answers.values()):
        if i < len(questions):
            if len(answer.split()) > 3:
                score += 1

    final_score = int((score / len(questions)) * 100) if questions else 0

    return f"""
    <h1>AI Interview Result 🤖</h1>
    <h2>Score: {final_score}%</h2>
    <a href='/dashboard'>Back</a>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)