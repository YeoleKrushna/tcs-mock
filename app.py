"""
TCS NQT 2026 – Online Assessment Platform
Flask + PostgreSQL Backend
Made By KRUSHNA YEOLE © 2026
"""

import os
import json
from datetime import datetime
from functools import wraps

import psycopg2
import psycopg2.extras
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tcs-nqt-2026-krushna-yeole-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://auto:InnEb6gzJcghXcAGPlDW07Z5QVYbapGF@dpg-d6hasvrh46gs73e3m2b0-a/auto_ydvo'
)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

EXAM_SECTIONS = [
    {'id': 'verbal',    'name': 'Verbal Ability',                   'questions': 25, 'time': 25},
    {'id': 'reasoning', 'name': 'Reasoning Ability',                'questions': 20, 'time': 25},
    {'id': 'numerical', 'name': 'Numerical Ability',                'questions': 20, 'time': 25},
    {'id': 'advanced',  'name': 'Advanced Quantitative & Reasoning','questions': 15, 'time': 25},
]

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       SERIAL PRIMARY KEY,
            name     TEXT NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            phone    TEXT DEFAULT '',
            college  TEXT DEFAULT '',
            roll_no  TEXT DEFAULT '',
            created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id                  SERIAL PRIMARY KEY,
            section_name        TEXT NOT NULL,
            position            INTEGER DEFAULT 0,
            question_text       TEXT,
            question_image_path TEXT,
            option_a            TEXT,
            option_b            TEXT,
            option_c            TEXT,
            option_d            TEXT,
            correct_answer      TEXT NOT NULL,
            question_type       TEXT DEFAULT 'mcq',
            marks               INTEGER DEFAULT 1,
            created             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id              SERIAL PRIMARY KEY,
            user_id         INTEGER NOT NULL,
            question_id     INTEGER NOT NULL,
            selected_answer TEXT,
            answered_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id              SERIAL PRIMARY KEY,
            user_id         INTEGER NOT NULL UNIQUE,
            violation_count INTEGER DEFAULT 0,
            auto_submitted  INTEGER DEFAULT 0,
            last_violation  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER NOT NULL UNIQUE,
            started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted    INTEGER DEFAULT 0,
            submitted_at TIMESTAMP
        )
    """)
    # Seed admin
    cur.execute("SELECT id FROM users WHERE email=%s", ('admin@tcs.com',))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (name,email,password,is_admin) VALUES (%s,%s,%s,%s)",
            ('Admin', 'admin@tcs.com', generate_password_hash('admin123'), 1)
        )
    # Seed demo candidate
    cur.execute("SELECT id FROM users WHERE email=%s", ('candidate@tcs.com',))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (name,email,password,college,roll_no) VALUES (%s,%s,%s,%s,%s)",
            ('Demo Candidate', 'candidate@tcs.com', generate_password_hash('test123'), 'Demo College', 'TC001')
        )
    _seed_questions(cur)
    conn.commit()
    cur.close(); conn.close()
    print("DB initialized.")

def _seed_questions(cur):
    sample = {
        'verbal': [
            ("Choose the correct synonym of 'ELOQUENT'", ['Articulate','Silent','Confused','Dull'], 'A'),
            ("Identify the correctly spelled word:", ['Accomodate','Accommodate','Acommodate','Acomodate'], 'B'),
            ("Select the antonym of 'BENEVOLENT':", ['Kind','Generous','Malevolent','Charitable'], 'C'),
            ("Fill in the blank: She ___ to the office every day.", ['commutes','commuted','commuting','commute'], 'A'),
            ("Identify the voice: 'The letter was written by him.'", ['Passive','Active','Imperative','Interrogative'], 'A'),
            ("Choose the correct article: He is ___ honest man.", ['a','an','the','no article'], 'B'),
            ("Which sentence is correct?", ["She don't know","She doesn't knows","She doesn't know","She not know"], 'C'),
            ("Synonym of VERBOSE:", ['Concise','Wordy','Silent','Brief'], 'B'),
            ("Antonym of OBSCURE:", ['Dark','Clear','Hidden','Vague'], 'B'),
            ("Error in: 'Each of the boys have done their homework.'", ['Each','boys','have','homework'], 'C'),
            ("Meaning of GREGARIOUS:", ['Unsocial','Sociable','Aggressive','Timid'], 'B'),
            ("Correct passive of 'She wrote a letter':", ['A letter was written by her','A letter is written by her','A letter has been written by her','A letter wrote by her'], 'A'),
            ("Identify the figure of speech: 'The wind whispered through the trees.'", ['Metaphor','Simile','Personification','Alliteration'], 'C'),
            ("Choose correct spelling:", ['Liason','Liaison','Liason','Liazon'], 'B'),
            ("Antonym of BENIGN:", ['Kind','Malignant','Friendly','Gentle'], 'B'),
            ("Rearrange: quickly / He / runs", ['He runs quickly','He quickly runs','Quickly he runs','He quickly run'], 'A'),
            ("One word for 'Fear of water':", ['Claustrophobia','Acrophobia','Hydrophobia','Xenophobia'], 'C'),
            ("'To beat around the bush' means:", ['To garden','To avoid the main topic','To win a fight','To be honest'], 'B'),
            ("Synonym of EPHEMERAL:", ['Permanent','Short-lived','Important','Vast'], 'B'),
            ("Choose the correct sentence:", ['I have went there','I have gone there','I went there yesterday','Both B and C'], 'D'),
            ("Antonym of LUCID:", ['Clear','Obvious','Obscure','Bright'], 'C'),
            ("Identify the conjunction: 'I will go if you come.'", ['will','go','if','come'], 'C'),
            ("Meaning of CONUNDRUM:", ['Solution','Puzzle','Simple task','Agreement'], 'B'),
            ("Synonym of AMELIORATE:", ['Worsen','Improve','Destroy','Neglect'], 'B'),
            ("'Break a leg' means:", ['Get injured','Good luck','Take rest','Run fast'], 'B'),
        ],
        'reasoning': [
            ("If FRIEND is coded as GSJFOE, what is CLIMAX?", ['DMJLBY','DMNBYX','DLIMBX','DMNBXY'], 'B'),
            ("In a row of 40, Ravi is 11th from left. Position from right?", ['28','29','30','31'], 'C'),
            ("Complete: 2, 6, 12, 20, 30, __?", ['38','40','41','42'], 'D'),
            ("A is B's sister, C is B's mother, D is C's father. A is related to D as?", ['Daughter','Grand Daughter','Great Grand Daughter','Sister'], 'B'),
            ("Odd one out: 17, 23, 37, 49, 53", ['17','23','49','53'], 'C'),
            ("Series: 1, 4, 9, 16, 25, __?", ['30','36','42','49'], 'B'),
            ("If + means x, x means ÷, what is 8+4x2?", ['16','1','32','4'], 'A'),
            ("Pointing to photo Ram says 'She is daughter of my grandfather's only son'. She is?", ['Sister','Daughter','Niece','Cousin'], 'A'),
            ("Missing: AZ, BY, CX, D__?", ['W','V','Y','X'], 'A'),
            ("If all roses are flowers and some flowers fade, then:", ['All roses fade','Some roses may fade','No roses fade','All flowers are roses'], 'B'),
            ("Clock shows 3:15. Angle between hands?", ['0','7.5','30','52.5'], 'B'),
            ("Next in series: 3, 7, 13, 21, 31, __?", ['43','41','45','47'], 'A'),
            ("If MOUSE = 72 and CHAIR = 53, then TABLE = ?", ['50','49','51','48'], 'A'),
            ("Dice: opposite of 1 is 6. Opposite of 2 is 5. Opposite of 3 is?", ['4','5','6','2'], 'A'),
            ("How many squares in a 4x4 grid?", ['16','17','20','30'], 'D'),
            ("Water image of 'FRIEND'?", ['FRIEND','DNIEIRF','Mirror of FRIEND','BNIEJB'], 'A'),
            ("A runs faster than B but slower than C. D runs faster than C. Who is slowest?", ['A','B','C','D'], 'B'),
            ("If 6th April 1990 was Friday, what was 3rd March 1990?", ['Tuesday','Wednesday','Thursday','Saturday'], 'C'),
            ("Find the odd pair: (16,4), (25,5), (36,6), (50,7)", ['(16,4)','(25,5)','(36,6)','(50,7)'], 'D'),
            ("Complete analogy: Book : Library :: Painting : ?", ['Museum','Canvas','Artist','Exhibition'], 'A'),
        ],
        'numerical': [
            ("If 20% of a number is 120, what is 35% of the number?", ['180','190','210','220'], 'C'),
            ("A train travels 360km in 4 hours. Speed in m/s?", ['20','25','30','35'], 'B'),
            ("Simple interest on Rs 5000 at 8% p.a. for 3 years?", ['1200','1500','1000','1400'], 'A'),
            ("LCM of 12, 15, 20, 35?", ['360','540','180','420'], 'D'),
            ("If a:b = 3:4 and b:c = 6:7, then a:b:c = ?", ['9:12:15','18:24:28','9:12:14','3:4:7'], 'C'),
            ("A can do work in 10 days, B in 15. Together finish in?", ['6','7','8','9'], 'A'),
            ("15% of 180 + 25% of 120 = ?", ['50','57','60','45'], 'B'),
            ("Speed of boat downstream 20 km/h, upstream 12 km/h. Speed of stream?", ['4','5','6','8'], 'A'),
            ("Compound interest on Rs 1000 at 10% for 2 years?", ['200','210','220','250'], 'B'),
            ("Area of circle of radius 7?", ['154','44','49','77'], 'A'),
            ("Average of first 10 multiples of 7?", ['38.5','38','39','40'], 'A'),
            ("A number when divided by 3 gives remainder 1, divided by 4 gives remainder 2. The number?", ['10','13','22','25'], 'C'),
            ("Profit % when CP=80, SP=100?", ['20','25','15','30'], 'B'),
            ("Sum of digits of (102+11)^2 = ?", ['9','12','16','7'], 'A'),
            ("A pipe fills tank in 6h, another empties in 8h. Both open, tank fills in?", ['24','20','18','16'], 'A'),
            ("If 3x + 4 = 19, x = ?", ['4','5','6','7'], 'B'),
            ("Two numbers ratio 3:5, sum 40. Difference?", ['8','10','12','16'], 'A'),
            ("Volume of cube with side 4?", ['16','32','64','48'], 'C'),
            ("Smallest prime > 50?", ['51','52','53','57'], 'C'),
            ("HCF of 36 and 48?", ['6','12','18','24'], 'B'),
        ],
        'advanced': [
            ("Two pipes fill tank in 12 and 18 hours. Together time?", ['7h 12m','6h','8h','7h'], 'A'),
            ("Shopkeeper sells at 20% profit. Cost Rs 250, selling price?", ['300','280','320','290'], 'A'),
            ("Ages of A and B ratio 3:5. After 5 years ratio 2:3. A's current age?", ['10','12','15','20'], 'C'),
            ("Probability of sum 7 when two dice thrown?", ['1/6','1/4','1/9','1/12'], 'A'),
            ("A works 10 days, B 15 days. Work 3 days together, B leaves. Days for A to finish?", ['4','5','6','7'], 'C'),
            ("Water mixed with milk to make 25% profit by selling at CP?", ['1:4','1:5','1:3','2:5'], 'A'),
            ("Remainder when 2^100 divided by 3?", ['0','1','2','None'], 'B'),
            ("Sum of first 50 odd numbers?", ['2500','2400','2600','2450'], 'A'),
            ("In a class 70% pass in Hindi, 65% in English. 27% fail both. % passing both?", ['62','63','64','65'], 'A'),
            ("A train 100m long crosses pole in 10s. Speed in km/h?", ['36','40','45','50'], 'A'),
            ("Selling price Rs 840 after 16% discount. Marked price?", ['980','1000','960','1020'], 'B'),
            ("Perimeter of rectangle 56m, length twice width. Area?", ['196','200','192','180'], 'A'),
            ("Simple interest doubles in 8 years. Rate percent?", ['10','12.5','15','8'], 'B'),
            ("Three numbers in ratio 1:2:3, sum 108. Largest?", ['54','36','27','72'], 'A'),
            ("In how many ways can 4 boys and 3 girls sit in a row so that no two girls sit together?", ['2880','1440','720','5040'], 'A'),
        ],
    }
    for section, qs in sample.items():
        cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE section_name=%s", (section,))
        count = cur.fetchone()['cnt']
        if count == 0:
            target = next(s['questions'] for s in EXAM_SECTIONS if s['id'] == section)
            for i in range(target):
                if i < len(qs):
                    q = qs[i]
                    cur.execute(
                        """INSERT INTO questions
                           (section_name,position,question_text,option_a,option_b,option_c,option_d,correct_answer,question_type)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (section, i+1, q[0], q[1][0], q[1][1], q[1][2], q[1][3], q[2], 'mcq')
                    )
                else:
                    cur.execute(
                        """INSERT INTO questions
                           (section_name,position,question_text,option_a,option_b,option_c,option_d,correct_answer,question_type)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (section, i+1,
                         f"Sample Question {i+1} for {section.title()} section.",
                         'Option A','Option B','Option C','Option D','A','mcq')
                    )

def login_required(f):
    @wraps(f)
    def deco(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return deco

def admin_required(f):
    @wraps(f)
    def deco(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return deco

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard') if session.get('is_admin') else url_for('instructions'))
    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE LOWER(email)=%s", (email,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id']    = user['id']
            session['user_name']  = user['name']
            session['user_email'] = user['email']
            session['is_admin']   = bool(user['is_admin'])
            return redirect(url_for('admin_dashboard') if user['is_admin'] else url_for('instructions'))
        error = 'Invalid email or password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/instructions')
@login_required
def instructions():
    return render_template('instructions.html', user_name=session['user_name'], sections=EXAM_SECTIONS)

@app.route('/exam')
@login_required
def exam():
    user_id = session['user_id']
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM violations WHERE user_id=%s", (user_id,))
    viol = cur.fetchone()
    cur.close(); conn.close()
    if viol and viol['auto_submitted']:
        return redirect(url_for('result'))
    return render_template('exam.html', user_name=session['user_name'], sections=EXAM_SECTIONS)

@app.route('/api/questions/<section>')
@login_required
def get_questions(section):
    user_id = session['user_id']
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM questions WHERE section_name=%s ORDER BY position, id", (section,))
    questions = cur.fetchall()
    cur.execute("SELECT question_id, selected_answer FROM responses WHERE user_id=%s", (user_id,))
    responses = cur.fetchall()
    cur.close(); conn.close()
    resp_map = {r['question_id']: r['selected_answer'] for r in responses}
    return jsonify([{
        'id': q['id'], 'section_name': q['section_name'],
        'question_text': q['question_text'], 'question_image_path': q['question_image_path'],
        'option_a': q['option_a'], 'option_b': q['option_b'],
        'option_c': q['option_c'], 'option_d': q['option_d'],
        'question_type': q['question_type'], 'marks': q['marks'],
        'saved_answer': resp_map.get(q['id'], '')
    } for q in questions])

@app.route('/api/save_answer', methods=['POST'])
@login_required
def save_answer():
    data = request.get_json()
    user_id = session['user_id']
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        """INSERT INTO responses (user_id,question_id,selected_answer) VALUES (%s,%s,%s)
           ON CONFLICT(user_id,question_id) DO UPDATE SET selected_answer=%s,answered_at=CURRENT_TIMESTAMP""",
        (user_id, data.get('question_id'), data.get('answer',''), data.get('answer',''))
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'saved'})

@app.route('/api/violation', methods=['POST'])
@login_required
def record_violation():
    user_id = session['user_id']
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM violations WHERE user_id=%s", (user_id,))
    viol = cur.fetchone()
    if viol:
        new_count = viol['violation_count'] + 1
        auto_sub  = 1 if new_count >= 8 else 0
        cur.execute("UPDATE violations SET violation_count=%s,auto_submitted=%s,last_violation=CURRENT_TIMESTAMP WHERE user_id=%s",
                    (new_count, auto_sub, user_id))
    else:
        new_count = 1; auto_sub = 0
        cur.execute("INSERT INTO violations (user_id,violation_count,auto_submitted) VALUES (%s,%s,%s)",
                    (user_id, new_count, auto_sub))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'violation_count': new_count, 'auto_submitted': bool(auto_sub)})

@app.route('/api/submit', methods=['POST'])
@login_required
def submit_exam():
    user_id = session['user_id']
    data    = request.get_json() or {}
    conn = get_db(); cur = conn.cursor()
    for q_id, answer in data.get('answers', {}).items():
        cur.execute(
            """INSERT INTO responses (user_id,question_id,selected_answer) VALUES (%s,%s,%s)
               ON CONFLICT(user_id,question_id) DO UPDATE SET selected_answer=%s""",
            (user_id, int(q_id), answer, answer)
        )
    cur.execute(
        """INSERT INTO exam_sessions (user_id,submitted,submitted_at) VALUES (%s,1,CURRENT_TIMESTAMP)
           ON CONFLICT(user_id) DO UPDATE SET submitted=1,submitted_at=CURRENT_TIMESTAMP""",
        (user_id,)
    )
    conn.commit(); cur.close(); conn.close()
    session['exam_submitted'] = True
    return jsonify({'status': 'submitted', 'redirect': url_for('result')})

# @app.route('/result')
# @login_required
# def result():
#     user_id = session['user_id']
#     conn = get_db(); cur = conn.cursor()
#     cur.execute(
#         """SELECT r.selected_answer, q.correct_answer, q.section_name, q.marks
#            FROM responses r JOIN questions q ON r.question_id=q.id WHERE r.user_id=%s""", (user_id,)
#     )
#     responses = cur.fetchall()
#     cur.execute("SELECT * FROM violations WHERE user_id=%s", (user_id,))
#     viol = cur.fetchone()
#     cur.close(); conn.close()
#     total     = len(responses)
#     correct   = sum(1 for r in responses if r['selected_answer'] == r['correct_answer'])
#     attempted = sum(1 for r in responses if r['selected_answer'])
#     section_scores = {}
#     for r in responses:
#         sn = r['section_name']
#         if sn not in section_scores:
#             section_scores[sn] = {'correct':0,'total':0}
#         section_scores[sn]['total'] += 1
#         if r['selected_answer'] == r['correct_answer']:
#             section_scores[sn]['correct'] += 1
#     return render_template('result.html',
#                            user_name=session['user_name'],
#                            total=total, correct=correct, attempted=attempted,
#                            violations=viol['violation_count'] if viol else 0,
#                            auto_submitted=bool(viol['auto_submitted']) if viol else False,
#                            section_scores=section_scores, sections=EXAM_SECTIONS)
@app.route('/result')
@login_required
def result():
    user_id = session['user_id']

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT q.id,
               q.section_name,
               q.question_text,
               q.option_a,
               q.option_b,
               q.option_c,
               q.option_d,
               q.correct_answer,
               r.selected_answer
        FROM questions q
        LEFT JOIN responses r
        ON q.id = r.question_id AND r.user_id = %s
        ORDER BY q.section_name, q.position
    """, (user_id,))

    rows = cur.fetchall()

    cur.execute("SELECT * FROM violations WHERE user_id=%s", (user_id,))
    viol = cur.fetchone()

    cur.close()
    conn.close()

    total = len(rows)
    correct = sum(1 for r in rows if r['selected_answer'] == r['correct_answer'])
    attempted = sum(1 for r in rows if r['selected_answer'])
    violations = viol['violation_count'] if viol else 0
    auto_sub = bool(viol['auto_submitted']) if viol else False

    # Section-wise score for top summary
    section_scores = {}
    for r in rows:
        sec = r['section_name']
        if sec not in section_scores:
            section_scores[sec] = {'correct': 0, 'total': 0}
        section_scores[sec]['total'] += 1
        if r['selected_answer'] == r['correct_answer']:
            section_scores[sec]['correct'] += 1

    # Detailed grouping
    section_details = {}
    for r in rows:
        sec = r['section_name']
        if sec not in section_details:
            section_details[sec] = []
        section_details[sec].append(r)

    return render_template(
        'result.html',
        user_name=session['user_name'],
        total=total,
        correct=correct,
        attempted=attempted,
        violations=violations,
        auto_submitted=auto_sub,
        section_scores=section_scores,
        section_details=section_details,
        sections=EXAM_SECTIONS
    )


# ─── Admin ──────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT u.*, v.violation_count, v.auto_submitted, s.submitted FROM users u LEFT JOIN violations v ON u.id=v.user_id LEFT JOIN exam_sessions s ON u.id=s.user_id WHERE u.is_admin=0 ORDER BY u.created DESC")
    users = cur.fetchall()
    q_count = {}
    for s in EXAM_SECTIONS:
        cur.execute("SELECT COUNT(*) as c FROM questions WHERE section_name=%s", (s['id'],))
        q_count[s['id']] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM violations WHERE auto_submitted=1")
    auto_submitted_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM exam_sessions WHERE submitted=1")
    exams_taken = cur.fetchone()['c']
    cur.close(); conn.close()
    return render_template('admin.html', users=users, sections=EXAM_SECTIONS,
                           q_count=q_count, auto_submitted_count=auto_submitted_count,
                           exams_taken=exams_taken, user_name=session['user_name'])

@app.route('/admin/questions/<section>')
@admin_required
def admin_questions(section):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM questions WHERE section_name=%s ORDER BY position, id", (section,))
    questions = cur.fetchall()
    cur.close(); conn.close()
    sec_info = next((s for s in EXAM_SECTIONS if s['id'] == section), None)
    return render_template('admin_questions.html', questions=questions, section=section,
                           sec_info=sec_info, sections=EXAM_SECTIONS, user_name=session['user_name'])

@app.route('/admin/add_question', methods=['GET', 'POST'])
@admin_required
def add_question():
    if request.method == 'POST':
        section  = request.form.get('section')
        q_text   = request.form.get('question_text', '')
        q_type   = request.form.get('question_type', 'mcq')
        option_a = request.form.get('option_a', '')
        option_b = request.form.get('option_b', '')
        option_c = request.form.get('option_c', '')
        option_d = request.form.get('option_d', '')
        correct  = request.form.get('correct_answer', 'A')
        marks    = int(request.form.get('marks', 1))
        position = request.form.get('position', '').strip()
        img_path = None
        if 'question_image' in request.files:
            file = request.files['question_image']
            if file and file.filename and allowed_file(file.filename):
                fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                img_path = f"uploads/{fname}"
        conn = get_db(); cur = conn.cursor()
        if position and position.isdigit():
            pos = int(position)
            cur.execute("UPDATE questions SET position=position+1 WHERE section_name=%s AND position>=%s", (section, pos))
        else:
            cur.execute("SELECT COALESCE(MAX(position),0)+1 as nxt FROM questions WHERE section_name=%s", (section,))
            pos = cur.fetchone()['nxt']
        if q_type == 'fill':
            correct = request.form.get('correct_answer_fill', correct)
        cur.execute(
            """INSERT INTO questions (section_name,position,question_text,question_image_path,option_a,option_b,option_c,option_d,correct_answer,question_type,marks)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (section, pos, q_text, img_path, option_a, option_b, option_c, option_d, correct, q_type, marks)
        )
        conn.commit(); cur.close(); conn.close()
        flash('✓ Question added successfully!', 'success')
        return redirect(url_for('admin_questions', section=section))
    prefill_section = request.args.get('section', EXAM_SECTIONS[0]['id'])
    conn = get_db(); cur = conn.cursor()
    section_counts = {}
    for s in EXAM_SECTIONS:
        cur.execute("SELECT COUNT(*) as c FROM questions WHERE section_name=%s", (s['id'],))
        section_counts[s['id']] = cur.fetchone()['c']
    cur.close(); conn.close()
    return render_template('add_question.html', sections=EXAM_SECTIONS,
                           prefill_section=prefill_section, section_counts=section_counts,
                           user_name=session['user_name'])

@app.route('/admin/edit_question/<int:qid>', methods=['GET', 'POST'])
@admin_required
def edit_question(qid):
    conn = get_db(); cur = conn.cursor()
    if request.method == 'POST':
        section  = request.form.get('section')
        q_text   = request.form.get('question_text', '')
        q_type   = request.form.get('question_type', 'mcq')
        option_a = request.form.get('option_a', '')
        option_b = request.form.get('option_b', '')
        option_c = request.form.get('option_c', '')
        option_d = request.form.get('option_d', '')
        correct  = request.form.get('correct_answer', 'A')
        marks    = int(request.form.get('marks', 1))
        position = request.form.get('position', '')
        img_path = request.form.get('existing_image') or None
        if 'question_image' in request.files:
            file = request.files['question_image']
            if file and file.filename and allowed_file(file.filename):
                fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                img_path = f"uploads/{fname}"
        if q_type == 'fill':
            correct = request.form.get('correct_answer_fill', correct)
        if position and position.isdigit():
            cur.execute("UPDATE questions SET position=%s WHERE id=%s", (int(position), qid))
        cur.execute(
            """UPDATE questions SET question_text=%s,question_image_path=%s,option_a=%s,option_b=%s,
               option_c=%s,option_d=%s,correct_answer=%s,question_type=%s,marks=%s,section_name=%s WHERE id=%s""",
            (q_text, img_path, option_a, option_b, option_c, option_d, correct, q_type, marks, section, qid)
        )
        conn.commit(); cur.close(); conn.close()
        flash('✓ Question updated!', 'success')
        return redirect(url_for('admin_questions', section=section))
    cur.execute("SELECT * FROM questions WHERE id=%s", (qid,))
    q = cur.fetchone()
    cur.close(); conn.close()
    return render_template('edit_question.html', q=q, sections=EXAM_SECTIONS, user_name=session['user_name'])

@app.route('/admin/delete_question/<int:qid>', methods=['POST'])
@admin_required
def delete_question(qid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT section_name FROM questions WHERE id=%s", (qid,))
    row = cur.fetchone()
    section = row['section_name'] if row else 'verbal'
    cur.execute("DELETE FROM questions WHERE id=%s", (qid,))
    conn.commit(); cur.close(); conn.close()
    flash('✓ Question deleted.', 'success')
    return redirect(url_for('admin_questions', section=section))

@app.route('/admin/reorder_question', methods=['POST'])
@admin_required
def reorder_question():
    data = request.get_json()
    qid = data.get('question_id'); new_pos = data.get('new_position'); section = data.get('section')
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT position FROM questions WHERE id=%s", (qid,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close(); return jsonify({'error':'Not found'}), 404
    old_pos = row['position']
    if new_pos < old_pos:
        cur.execute("UPDATE questions SET position=position+1 WHERE section_name=%s AND position>=%s AND position<%s AND id!=%s", (section, new_pos, old_pos, qid))
    else:
        cur.execute("UPDATE questions SET position=position-1 WHERE section_name=%s AND position>%s AND position<=%s AND id!=%s", (section, old_pos, new_pos, qid))
    cur.execute("UPDATE questions SET position=%s WHERE id=%s", (new_pos, qid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'ok'})

@app.route('/admin/create_user', methods=['POST'])
@admin_required
def create_user():
    name = request.form.get('name','').strip()
    email = request.form.get('email','').strip().lower()
    password = request.form.get('password','tcs@123')
    phone = request.form.get('phone','')
    college = request.form.get('college','')
    roll_no = request.form.get('roll_no','')
    is_admin = 1 if request.form.get('is_admin') else 0
    if not name or not email:
        flash('Name and email are required.', 'error')
        return redirect(url_for('admin_dashboard'))
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (name,email,password,phone,college,roll_no,is_admin) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (name, email, generate_password_hash(password), phone, college, roll_no, is_admin))
        conn.commit()
        flash(f'✓ User "{name}" created! Password: {password}', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash(f'✗ Email "{email}" already exists.', 'error')
    finally:
        cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_user/<int:uid>', methods=['GET', 'POST'])
@admin_required
def edit_user(uid):
    conn = get_db(); cur = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        phone = request.form.get('phone','')
        college = request.form.get('college','')
        roll_no = request.form.get('roll_no','')
        new_pw = request.form.get('new_password','').strip()
        if new_pw:
            cur.execute("UPDATE users SET name=%s,email=%s,phone=%s,college=%s,roll_no=%s,password=%s WHERE id=%s",
                        (name, email, phone, college, roll_no, generate_password_hash(new_pw), uid))
        else:
            cur.execute("UPDATE users SET name=%s,email=%s,phone=%s,college=%s,roll_no=%s WHERE id=%s",
                        (name, email, phone, college, roll_no, uid))
        conn.commit(); cur.close(); conn.close()
        flash('✓ User updated!', 'success')
        return redirect(url_for('admin_dashboard'))
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()
    cur.close(); conn.close()
    return render_template('edit_user.html', user=user, user_name=session['user_name'])

@app.route('/admin/delete_user/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM responses WHERE user_id=%s", (uid,))
    cur.execute("DELETE FROM violations WHERE user_id=%s", (uid,))
    cur.execute("DELETE FROM exam_sessions WHERE user_id=%s", (uid,))
    cur.execute("DELETE FROM users WHERE id=%s AND is_admin=0", (uid,))
    conn.commit(); cur.close(); conn.close()
    flash('✓ User deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_exam/<int:uid>', methods=['POST'])
@admin_required
def reset_exam(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM responses WHERE user_id=%s", (uid,))
    cur.execute("DELETE FROM violations WHERE user_id=%s", (uid,))
    cur.execute("DELETE FROM exam_sessions WHERE user_id=%s", (uid,))
    conn.commit(); cur.close(); conn.close()
    flash('✓ Exam reset. User can retake now.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/view_result/<int:uid>')
@admin_required
def admin_view_result(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()
    cur.execute("""SELECT r.selected_answer, q.correct_answer, q.section_name, q.marks, q.question_text
                   FROM responses r JOIN questions q ON r.question_id=q.id
                   WHERE r.user_id=%s ORDER BY q.section_name, q.position""", (uid,))
    responses = cur.fetchall()
    cur.execute("SELECT * FROM violations WHERE user_id=%s", (uid,))
    viol = cur.fetchone()
    cur.execute("SELECT * FROM exam_sessions WHERE user_id=%s", (uid,))
    sess = cur.fetchone()
    cur.close(); conn.close()
    total = len(responses)
    correct = sum(1 for r in responses if r['selected_answer'] == r['correct_answer'])
    attempted = sum(1 for r in responses if r['selected_answer'])
    section_scores = {}
    for r in responses:
        sn = r['section_name']
        if sn not in section_scores:
            section_scores[sn] = {'correct':0,'total':0}
        section_scores[sn]['total'] += 1
        if r['selected_answer'] == r['correct_answer']:
            section_scores[sn]['correct'] += 1
    return render_template('admin_result_view.html',
                           candidate=user, responses=responses,
                           total=total, correct=correct, attempted=attempted,
                           viol=viol, sess=sess, section_scores=section_scores,
                           sections=EXAM_SECTIONS, user_name=session['user_name'])

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

# ── Auto-init DB when loaded by gunicorn ──
try:
    init_db()
except Exception as _e:
    print(f"[Startup] DB init note: {_e}")
