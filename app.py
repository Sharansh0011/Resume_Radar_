from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import random
import datetime
from dotenv import load_dotenv

load_dotenv()  # Load .env file

from utils import (
    parse_resume, extract_skills, calculate_match_score,
    generate_interview_questions, score_answer, generate_pdf_report,
    batch_score_answers, generate_follow_up, generate_resume_tips
)

app = Flask(__name__)

# ======================= DEPLOYMENT CONFIG =======================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')

# Database: PostgreSQL on Render/PythonAnywhere, SQLite fallback locally
database_url = os.environ.get('DATABASE_URL', 'sqlite:///resume_radar.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Absolute paths for uploads/reports (PythonAnywhere compatible)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['REPORT_FOLDER'] = os.path.join(BASE_DIR, 'static', 'reports')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create tables on startup (needed for gunicorn/Render deployment)
with app.app_context():
    db.create_all()

@app.template_filter('fromjson')
def fromjson_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        if isinstance(value, str):
            return [s.strip() for s in value.split(',') if s.strip()]
        return []

# ======================= DARK MODE CONTEXT PROCESSOR =======================
@app.context_processor
def inject_dark_mode():
    dark_mode = False
    if current_user.is_authenticated:
        us = UserSettings.query.filter_by(user_id=current_user.id).first()
        if us:
            dark_mode = us.dark_mode
    return dict(dark_mode=dark_mode)

# ======================= DATABASE MODELS =======================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    resume_path = db.Column(db.String(255))
    extracted_skills = db.Column(db.Text)
    experience_years = db.Column(db.Float, default=0)
    education = db.Column(db.Text)
    company_name = db.Column(db.String(100))
    interviews_created = db.relationship('Interview', foreign_keys='Interview.hr_id', backref='hr', lazy=True)
    interviews_assigned = db.relationship('Interview', foreign_keys='Interview.candidate_id', backref='candidate', lazy=True)
    interview_responses = db.relationship('InterviewResponse', backref='candidate_user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False)
    practice_sessions = db.relationship('PracticeSession', backref='candidate', lazy=True)

class JobDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hr_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description_text = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text)
    min_experience = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    interviews = db.relationship('Interview', backref='job', lazy=True)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hr_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_description.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    questions = db.Column(db.Text, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default='pending')
    total_score = db.Column(db.Float, default=0)
    max_possible_score = db.Column(db.Float, default=0)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    report_path = db.Column(db.String(255))
    tab_switches = db.Column(db.Integer, default=0)
    copy_paste_attempts = db.Column(db.Integer, default=0)
    responses = db.relationship('InterviewResponse', backref='interview', lazy=True, cascade='all, delete-orphan')

class InterviewResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_index = db.Column(db.Integer, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text)
    score = db.Column(db.Float, default=0)
    max_score = db.Column(db.Float, default=0)
    keywords_matched = db.Column(db.Text)
    time_taken_seconds = db.Column(db.Integer, default=0)
    feedback = db.Column(db.Text)
    answered_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class PracticeSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    questions = db.Column(db.Text, nullable=False)
    responses = db.Column(db.Text)
    total_score = db.Column(db.Float, default=0)
    max_score = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False)
    weight_skills = db.Column(db.Float, default=50)
    weight_experience = db.Column(db.Float, default=30)
    weight_education = db.Column(db.Float, default=20)

# ======================= AUTH ROUTES =======================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        phone = request.form.get('phone')
        company_name = request.form.get('company_name')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            role=role,
            phone=phone,
            company_name=company_name
        )
        db.session.add(user)
        db.session.commit()

        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role == 'hr':
                return redirect(url_for('hr_dashboard'))
            else:
                return redirect(url_for('candidate_dashboard'))
        flash('Invalid email or password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

# ======================= HR ROUTES =======================

@app.route('/hr/dashboard')
@login_required
def hr_dashboard():
    if current_user.role != 'hr':
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))

    jobs = JobDescription.query.filter_by(hr_id=current_user.id).all()
    candidates = User.query.filter_by(role='candidate').all()
    interviews = Interview.query.filter_by(hr_id=current_user.id).all()

    total_candidates = len(candidates)
    total_jobs = len(jobs)
    total_interviews = len(interviews)
    avg_score = 0
    if interviews:
        completed = [i for i in interviews if i.status == 'completed']
        if completed:
            avg_score = sum(i.total_score for i in completed) / len(completed)

    # Chart data
    score_distribution = {"0-20":0, "21-40":0, "41-60":0, "61-80":0, "81-100":0}
    for i in interviews:
        if i.status == 'completed' and i.max_possible_score > 0:
            pct = (i.total_score / i.max_possible_score) * 100
            if pct <= 20: score_distribution["0-20"] += 1
            elif pct <= 40: score_distribution["21-40"] += 1
            elif pct <= 60: score_distribution["41-60"] += 1
            elif pct <= 80: score_distribution["61-80"] += 1
            else: score_distribution["81-100"] += 1

    job_stats = []
    for job in jobs:
        job_interviews = [i for i in interviews if i.job_id == job.id]
        completed_job = [i for i in job_interviews if i.status == 'completed']
        avg = 0
        if completed_job:
            avg = sum(i.total_score for i in completed_job) / len(completed_job)
        job_stats.append({"title": job.title, "count": len(job_interviews), "avg": round(avg,1)})

    return render_template('hr/dashboard.html', jobs=jobs, candidates=candidates,
                         interviews=interviews, total_candidates=total_candidates,
                         total_jobs=total_jobs, total_interviews=total_interviews,
                         avg_score=round(avg_score, 1),
                         score_distribution=score_distribution,
                         job_stats=job_stats)

@app.route('/hr/create_job', methods=['GET', 'POST'])
@login_required
def create_job():
    if current_user.role != 'hr':
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        skills = request.form.get('required_skills')
        min_exp = float(request.form.get('min_experience', 0))

        job = JobDescription(
            hr_id=current_user.id,
            title=title,
            description_text=description,
            required_skills=skills,
            min_experience=min_exp
        )
        db.session.add(job)
        db.session.commit()
        flash('Job created successfully!', 'success')
        return redirect(url_for('hr_dashboard'))

    return render_template('create_job.html')

@app.route('/hr/view_candidate')
@login_required
def view_candidate():
    if current_user.role != 'hr':
        return redirect(url_for('index'))

    candidates = User.query.filter_by(role='candidate').all()
    jobs = JobDescription.query.filter_by(hr_id=current_user.id).all()

    candidate_scores = []
    for candidate in candidates:
        scores = []
        if candidate.extracted_skills:
            for job in jobs:
                score_data = calculate_match_score(
                    candidate.extracted_skills,
                    candidate.experience_years or 0,
                    candidate.education or '',
                    job.required_skills or '',
                    job.min_experience or 0
                )
                scores.append({'job': job.title, 'score': score_data['total_score']})
        candidate_scores.append({'candidate': candidate, 'scores': scores})

    return render_template('hr/view_candidate.html', candidate_scores=candidate_scores, jobs=jobs)

@app.route('/hr/create_interview', methods=['POST'])
@login_required
def create_interview():
    if current_user.role != 'hr':
        return redirect(url_for('index'))

    candidate_id = request.form.get('candidate_id')
    job_id = request.form.get('job_id')
    duration = int(request.form.get('duration', 30))

    candidate = User.query.get(candidate_id)
    job = JobDescription.query.get(job_id)

    if not candidate or not job:
        flash('Invalid candidate or job!', 'danger')
        return redirect(url_for('hr_dashboard'))

    questions = generate_interview_questions(
        job.required_skills or '',
        candidate.extracted_skills or '',
        num_questions=5
    )

    interview = Interview(
        hr_id=current_user.id,
        candidate_id=candidate_id,
        job_id=job_id,
        title=f"Interview for {job.title}",
        questions=json.dumps(questions),
        duration_minutes=duration,
        status='pending'
    )
    db.session.add(interview)
    db.session.commit()

    flash('Interview assigned successfully!', 'success')
    return redirect(url_for('hr_dashboard'))

@app.route('/hr/view_interview/<int:interview_id>')
@login_required
def view_interview(interview_id):
    if current_user.role != 'hr':
        return redirect(url_for('index'))

    interview = Interview.query.get_or_404(interview_id)
    if interview.hr_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('hr_dashboard'))

    responses = InterviewResponse.query.filter_by(interview_id=interview_id).order_by(InterviewResponse.question_index).all()
    return render_template('hr/view_interview.html', interview=interview, responses=responses)

@app.route('/hr/download_report/<int:interview_id>')
@login_required
def download_report(interview_id):
    if current_user.role != 'hr':
        return redirect(url_for('index'))

    interview = Interview.query.get_or_404(interview_id)
    if interview.hr_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('hr_dashboard'))

    if interview.report_path and os.path.exists(interview.report_path):
        return send_file(interview.report_path, as_attachment=True)

    responses = InterviewResponse.query.filter_by(interview_id=interview_id).order_by(InterviewResponse.question_index).all()
    candidate = User.query.get(interview.candidate_id)
    job = JobDescription.query.get(interview.job_id)

    report_path = generate_pdf_report(interview, responses, candidate, job, app.config['REPORT_FOLDER'])
    interview.report_path = report_path
    db.session.commit()

    return send_file(report_path, as_attachment=True)

# ======================= CANDIDATE ROUTES =======================

@app.route('/candidate/dashboard')
@login_required
def candidate_dashboard():
    if current_user.role != 'candidate':
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))

    jobs = JobDescription.query.all()
    matches = []

    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()

    skills = []
    if current_user.extracted_skills:
        skills = json.loads(current_user.extracted_skills)

    if current_user.extracted_skills:
        for job in jobs:
            score_data = calculate_match_score(
                current_user.extracted_skills,
                current_user.experience_years or 0,
                current_user.education or '',
                job.required_skills or '',
                job.min_experience or 0,
                weight_skills=settings.weight_skills,
                weight_experience=settings.weight_experience,
                weight_education=settings.weight_education
            )
            matches.append({'job': job, 'score': score_data})

    interviews = Interview.query.filter_by(candidate_id=current_user.id).all()
    completed_interviews = [i for i in interviews if i.status == 'completed']
    pending_interviews = [i for i in interviews if i.status == 'pending']

    return render_template('candidate/dashboard.html', matches=matches,
                         completed_interviews=completed_interviews,
                         pending_interviews=pending_interviews,
                         settings=settings, skills=skills)

@app.route('/candidate/upload_resume', methods=['POST'])
@login_required
def upload_resume():
    if current_user.role != 'candidate':
        return redirect(url_for('index'))

    if 'resume' not in request.files:
        flash('No file selected!', 'danger')
        return redirect(url_for('candidate_dashboard'))

    file = request.files['resume']
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('candidate_dashboard'))

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        resume_text = parse_resume(filepath)
        skills = extract_skills(resume_text)

        current_user.resume_path = filepath
        current_user.extracted_skills = json.dumps(skills)
        current_user.experience_years = 2.0
        current_user.education = 'B.Tech'
        db.session.commit()

        flash(f'Resume uploaded successfully! Detected {len(skills)} skills.', 'success')
    else:
        flash('Invalid file format! Please upload PDF, DOCX, or TXT.', 'danger')

    return redirect(url_for('candidate_dashboard'))

@app.route('/candidate/interview/<int:interview_id>')
@login_required
def take_interview(interview_id):
    if current_user.role != 'candidate':
        return redirect(url_for('index'))

    interview = Interview.query.get_or_404(interview_id)
    if interview.candidate_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('candidate_dashboard'))

    if interview.status == 'completed':
        flash('Interview already completed!', 'info')
        return redirect(url_for('candidate_results', interview_id=interview_id))

    questions = json.loads(interview.questions)
    interview.status = 'in_progress'
    interview.started_at = datetime.datetime.utcnow()
    db.session.commit()

    return render_template('candidate/take_interview.html', interview=interview, questions=questions,
                         duration=interview.duration_minutes)

@app.route('/candidate/interview/<int:interview_id>/submit', methods=['POST'])
@login_required
def submit_interview(interview_id):
    if current_user.role != 'candidate':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    interview = Interview.query.get_or_404(interview_id)
    if interview.candidate_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    answers = data.get('answers', [])
    questions = json.loads(interview.questions)

    # Anti-cheat data
    interview.tab_switches = data.get('tab_switches', 0)
    interview.copy_paste_attempts = data.get('copy_paste_attempts', 0)

    total_score = 0
    max_score = 0

    # Batch score all answers in one AI call (faster)
    qa_pairs = []
    for i, ans_data in enumerate(answers):
        if i < len(questions):
            q = questions[i]
            qa_pairs.append({
                'question': q.get('question', ''),
                'answer': ans_data.get('answer', ''),
                'expected_keywords': q.get('expected_keywords', []),
                'time_taken': ans_data.get('time_taken', 0)
            })

    score_results = batch_score_answers(qa_pairs)

    for i, score_result in enumerate(score_results):
        if i < len(questions):
            q = questions[i]
            response = InterviewResponse(
                interview_id=interview_id,
                candidate_id=current_user.id,
                question_index=i,
                question_text=q.get('question', ''),
                answer_text=qa_pairs[i].get('answer', ''),
                score=score_result['score'],
                max_score=score_result['max_score'],
                keywords_matched=json.dumps(score_result.get('keywords_matched', [])),
                time_taken_seconds=qa_pairs[i].get('time_taken', 0),
                feedback=score_result.get('feedback', '')
            )
            db.session.add(response)
            total_score += score_result['score']
            max_score += score_result['max_score']

    interview.status = 'completed'
    interview.total_score = total_score
    interview.max_possible_score = max_score
    interview.completed_at = datetime.datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'redirect': url_for('candidate_results', interview_id=interview_id)})

@app.route('/candidate/results/<int:interview_id>')
@login_required
def candidate_results(interview_id):
    if current_user.role != 'candidate':
        return redirect(url_for('index'))

    interview = Interview.query.get_or_404(interview_id)
    if interview.candidate_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('candidate_dashboard'))

    responses = InterviewResponse.query.filter_by(interview_id=interview_id).order_by(InterviewResponse.question_index).all()
    job = JobDescription.query.get(interview.job_id)

    return render_template('candidate/interview_results.html', interview=interview, responses=responses, job=job)

# ======================= PRACTICE TOPICS =======================
PRACTICE_TOPICS = [
    {'id': 'web_dev', 'name': 'Web Development', 'emoji': '🌐', 'desc': 'HTML, CSS, JS, React, Node.js', 'skills': 'html, css, javascript, react, node.js, frontend, backend, api, rest, web'},
    {'id': 'python', 'name': 'Python Developer', 'emoji': '🐍', 'desc': 'Python, Django, Flask, OOP', 'skills': 'python, django, flask, oop, data structures, algorithm, list, tuple, function'},
    {'id': 'java', 'name': 'Java Developer', 'emoji': '☕', 'desc': 'Java, Spring, OOP, DSA', 'skills': 'java, spring, oop, data structures, algorithm, jvm, multithreading, collections'},
    {'id': 'ml_ai', 'name': 'ML / AI Engineer', 'emoji': '🤖', 'desc': 'Machine Learning, Deep Learning, NLP', 'skills': 'machine learning, deep learning, neural network, nlp, tensorflow, pytorch, classification, regression, cnn, rnn'},
    {'id': 'data_science', 'name': 'Data Science', 'emoji': '📊', 'desc': 'Pandas, Statistics, Visualization', 'skills': 'pandas, numpy, statistics, eda, visualization, data analysis, matplotlib, feature engineering, correlation'},
    {'id': 'devops', 'name': 'DevOps / Cloud', 'emoji': '☁️', 'desc': 'Docker, CI/CD, AWS, Kubernetes', 'skills': 'docker, ci/cd, aws, kubernetes, cloud, deployment, monitoring, pipeline, jenkins'},
    {'id': 'system_design', 'name': 'System Design', 'emoji': '🏗️', 'desc': 'Scalability, Architecture, Distributed', 'skills': 'system design, scalability, load balancer, caching, database, sharding, microservices, distributed'},
    {'id': 'behavioral', 'name': 'Behavioral / HR', 'emoji': '🤝', 'desc': 'Teamwork, Leadership, Communication', 'skills': 'teamwork, leadership, communication, conflict, deadline, challenge, project management'},
    {'id': 'all', 'name': 'All Topics (Mixed)', 'emoji': '🎲', 'desc': 'Random mix of all categories', 'skills': ''},
]

@app.route('/candidate/practice_select')
@login_required
def practice_select():
    if current_user.role != 'candidate':
        return redirect(url_for('index'))
    from utils import QUESTION_BANK
    # Count questions per topic by matching skills
    topics_with_count = []
    for topic in PRACTICE_TOPICS:
        if topic['id'] == 'all':
            count = len(QUESTION_BANK)
        else:
            topic_skills = set([s.strip().lower() for s in topic['skills'].split(',') if s.strip()])
            count = 0
            for q in QUESTION_BANK:
                keywords = [kw.lower() for kw in q.get('expected_keywords', [])]
                if any(ts in ' '.join(keywords) for ts in topic_skills):
                    count += 1
            count = max(count, 5)  # AI will generate if bank is short
        topics_with_count.append({**topic, 'count': count})
    return render_template('candidate/practice_select.html', topics=topics_with_count)

@app.route('/candidate/practice_interview', methods=['GET', 'POST'])
@login_required
def practice_interview():
    if current_user.role != 'candidate':
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.get_json()
        answers = data.get('answers', [])
        questions = json.loads(session.get('practice_questions', '[]'))

        total_score = 0
        max_score = 0
        responses = []

        # Batch score all answers in one AI call (faster)
        qa_pairs = []
        for i, ans_data in enumerate(answers):
            if i < len(questions):
                q = questions[i]
                qa_pairs.append({
                    'question': q.get('question', ''),
                    'answer': ans_data.get('answer', ''),
                    'expected_keywords': q.get('expected_keywords', [])
                })

        score_results = batch_score_answers(qa_pairs)

        for i, score_result in enumerate(score_results):
            if i < len(questions):
                q = questions[i]
                responses.append({
                    'question': q.get('question', ''),
                    'answer': qa_pairs[i].get('answer', ''),
                    'score': score_result['score'],
                    'max_score': score_result['max_score'],
                    'feedback': score_result.get('feedback', ''),
                    'keywords_matched': score_result.get('keywords_matched', [])
                })
                total_score += score_result['score']
                max_score += score_result['max_score']

        practice = PracticeSession(
            candidate_id=current_user.id,
            questions=json.dumps(questions),
            responses=json.dumps(responses),
            total_score=total_score,
            max_score=max_score
        )
        db.session.add(practice)
        db.session.commit()

        return jsonify({'success': True, 'score': total_score, 'max_score': max_score})

    # Get selected topic
    topic_id = request.args.get('topic', 'all')
    selected_topic = next((t for t in PRACTICE_TOPICS if t['id'] == topic_id), PRACTICE_TOPICS[-1])

    # Use topic skills for question generation
    if topic_id == 'all':
        skills = []
        if current_user.extracted_skills:
            skills = json.loads(current_user.extracted_skills)
        skill_text = ', '.join(skills) if skills else 'general programming'
    else:
        skill_text = selected_topic['skills']

    questions = generate_interview_questions(
        skill_text,
        skill_text,
        num_questions=5
    )
    session['practice_questions'] = json.dumps(questions)
    session['practice_topic'] = selected_topic['name']

    return render_template('candidate/practice_session.html', questions=questions, duration=20, topic=selected_topic['name'])

@app.route('/candidate/start_practice', methods=['GET', 'POST'])
@login_required
def start_practice():
    return practice_interview()

@app.route('/candidate/practice_results')
@login_required
def practice_results():
    if current_user.role != 'candidate':
        return redirect(url_for('index'))

    practice = PracticeSession.query.filter_by(candidate_id=current_user.id).order_by(PracticeSession.created_at.desc()).first()
    return render_template('candidate/practice_results.html', session=practice)

# ======================= SETTINGS ROUTES =======================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()

    if request.method == 'POST':
        user_settings.dark_mode = request.form.get('dark_mode') == 'on'
        user_settings.weight_skills = float(request.form.get('weight_skills', 50))
        user_settings.weight_experience = float(request.form.get('weight_experience', 30))
        user_settings.weight_education = float(request.form.get('weight_education', 20))
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', settings=user_settings)

@app.route('/api/toggle_dark_mode', methods=['POST'])
@login_required
def toggle_dark_mode():
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)

    user_settings.dark_mode = not user_settings.dark_mode
    db.session.commit()
    return jsonify({'dark_mode': user_settings.dark_mode})

@app.route('/api/theme')
def api_theme():
    if current_user.is_authenticated:
        us = UserSettings.query.filter_by(user_id=current_user.id).first()
        if us:
            return jsonify({'dark_mode': us.dark_mode})
    return jsonify({'dark_mode': False})

# ======================= API ROUTES =======================

@app.route('/api/candidate_score/<int:candidate_id>/<int:job_id>')
@login_required
def api_candidate_score(candidate_id, job_id):
    if current_user.role != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    candidate = User.query.get_or_404(candidate_id)
    job = JobDescription.query.get_or_404(job_id)

    score_data = calculate_match_score(
        candidate.extracted_skills or '',
        candidate.experience_years or 0,
        candidate.education or '',
        job.required_skills or '',
        job.min_experience or 0
    )
    return jsonify(score_data)

@app.route('/api/follow_up', methods=['POST'])
@login_required
def api_follow_up():
    """AI-powered follow-up question based on candidate's answer."""
    data = request.get_json()
    question = data.get('question', '')
    answer = data.get('answer', '')
    
    if not question or not answer.strip():
        return jsonify({'error': 'Answer is empty', 'follow_up': None}), 400
    
    follow_up = generate_follow_up(question, answer)
    if follow_up:
        return jsonify({'follow_up': follow_up})
    return jsonify({'error': 'Could not generate follow-up', 'follow_up': None}), 500

@app.route('/api/resume_tips', methods=['GET'])
@login_required
def api_resume_tips():
    """AI-powered resume improvement tips."""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Only candidates can get resume tips'}), 403
    
    if not current_user.resume_path:
        return jsonify({'error': 'Upload your resume first'}), 400
    
    # Parse resume to get text
    resume_text = parse_resume(current_user.resume_path)
    if not resume_text:
        return jsonify({'error': 'Could not read resume file'}), 400
    
    tips_data = generate_resume_tips(
        resume_text,
        current_user.extracted_skills
    )
    return jsonify(tips_data)

# ======================= DELETE ROUTES =======================

@app.route('/hr/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    """HR: Delete a job and all its interviews."""
    if current_user.role != 'hr':
        flash('Unauthorized', 'error')
        return redirect(url_for('index'))
    job = JobDescription.query.get_or_404(job_id)
    if job.hr_id != current_user.id:
        flash('You can only delete your own jobs', 'error')
        return redirect(url_for('hr_dashboard'))
    # Delete all interviews for this job
    interviews = Interview.query.filter_by(job_id=job.id).all()
    for interview in interviews:
        db.session.delete(interview)
    db.session.delete(job)
    db.session.commit()
    flash(f'Job "{job.title}" and its interviews deleted successfully', 'success')
    return redirect(url_for('hr_dashboard'))

@app.route('/hr/delete_interview/<int:interview_id>', methods=['POST'])
@login_required
def delete_interview(interview_id):
    """HR: Delete an interview."""
    if current_user.role != 'hr':
        flash('Unauthorized', 'error')
        return redirect(url_for('index'))
    interview = Interview.query.get_or_404(interview_id)
    if interview.hr_id != current_user.id:
        flash('You can only delete your own interviews', 'error')
        return redirect(url_for('hr_dashboard'))
    title = interview.title
    db.session.delete(interview)
    db.session.commit()
    flash(f'Interview "{title}" deleted successfully', 'success')
    return redirect(url_for('hr_dashboard'))

@app.route('/candidate/delete_resume', methods=['POST'])
@login_required
def delete_resume():
    """Candidate: Delete uploaded resume."""
    if current_user.role != 'candidate':
        flash('Unauthorized', 'error')
        return redirect(url_for('index'))
    if current_user.resume_path:
        # Delete file from disk
        if os.path.exists(current_user.resume_path):
            os.remove(current_user.resume_path)
        current_user.resume_path = None
        current_user.extracted_skills = None
        current_user.experience_years = None
        current_user.education = None
        db.session.commit()
        flash('Resume deleted successfully', 'success')
    else:
        flash('No resume to delete', 'warning')
    return redirect(url_for('candidate_dashboard'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data."""
    user_id = current_user.id
    user_role = current_user.role
    
    if user_role == 'hr':
        # Delete all jobs and interviews created by this HR
        jobs = JobDescription.query.filter_by(hr_id=user_id).all()
        for job in jobs:
            interviews = Interview.query.filter_by(job_id=job.id).all()
            for interview in interviews:
                db.session.delete(interview)
            db.session.delete(job)
        # Delete interviews assigned by this HR
        remaining = Interview.query.filter_by(hr_id=user_id).all()
        for interview in remaining:
            db.session.delete(interview)
    else:
        # Delete candidate's interviews and responses
        interviews = Interview.query.filter_by(candidate_id=user_id).all()
        for interview in interviews:
            db.session.delete(interview)
        responses = InterviewResponse.query.filter_by(candidate_id=user_id).all()
        for resp in responses:
            db.session.delete(resp)
        # Delete resume file
        if current_user.resume_path and os.path.exists(current_user.resume_path):
            os.remove(current_user.resume_path)
    
    logout_user()
    user = db.session.get(User, user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Account deleted successfully', 'success')
    return redirect(url_for('index'))

# ======================= MAIN =======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true')
