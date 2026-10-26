import re
import os
import json
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load .env for API keys

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
except ImportError:
    pass

# ======================= GEMINI AI SETUP =======================

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
_gemini_model = None

def get_gemini_model():
    """Initialize and return Gemini model (singleton pattern)."""
    global _gemini_model
    if _gemini_model is None and GEMINI_AVAILABLE and GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            _gemini_model = genai.GenerativeModel('gemini-3.5-flash-lite')
        except Exception as e:
            print(f"[Resume Radar] Gemini init failed: {e}")
            _gemini_model = None
    return _gemini_model

def call_gemini(prompt, max_retries=2):
    """Call Gemini API with retry logic. Returns response text or None on failure."""
    model = get_gemini_model()
    if not model:
        return None
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"[Resume Radar] Gemini API error (attempt {attempt + 1}): {e}")
    return None

def parse_gemini_json(text):
    """Extract JSON from Gemini response (handles markdown code blocks)."""
    if not text:
        return None
    try:
        # Try direct parse
        return json.loads(text)
    except:
        pass
    try:
        # Try extracting from markdown code block
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
    except:
        pass
    try:
        # Try finding first [ or { 
        for i, ch in enumerate(text):
            if ch in '[{':
                # Find matching closing bracket
                depth = 0
                for j in range(i, len(text)):
                    if text[j] == ch:
                        depth += 1
                    elif text[j] == (']' if ch == '[' else '}'):
                        depth -= 1
                    if depth == 0:
                        return json.loads(text[i:j+1])
                break
    except:
        pass
    return None

# ======================= RESUME PARSING =======================

def parse_resume(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    text = ""

    if ext == 'pdf' and PyPDF2:
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            text = f"Error reading PDF: {str(e)}"

    elif ext == 'docx' and docx:
        try:
            document = docx.Document(filepath)
            for para in document.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            text = f"Error reading DOCX: {str(e)}"

    elif ext == 'txt':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    text = f.read()
            except Exception as e:
                text = f"Error reading TXT: {str(e)}"

    return text.lower()

# ======================= SKILL EXTRACTION =======================

TECH_SKILLS = [
    'python', 'java', 'javascript', 'js', 'typescript', 'ts', 'c++', 'c#', 'c', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin',
    'html', 'html5', 'css', 'css3', 'sass', 'scss', 'less',
    'react', 'react.js', 'angular', 'vue', 'vue.js', 'next.js', 'nuxt.js', 'svelte',
    'django', 'flask', 'fastapi', 'spring', 'spring boot', 'express', 'express.js', 'node.js', 'nodejs', 'laravel', 'rails',
    'sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'mongodb', 'redis', 'cassandra', 'dynamodb', 'firebase',
    'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'docker', 'kubernetes', 'k8s', 'jenkins', 'git', 'github', 'gitlab',
    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'opencv', 'nlp',
    'machine learning', 'deep learning', 'data science', 'artificial intelligence', 'ai', 'ml',
    'neural network', 'cnn', 'rnn', 'lstm', 'transformer', 'bert', 'gpt', 'gan', 'autoencoder',
    'regression', 'classification', 'clustering', 'reinforcement learning', 'supervised learning', 'unsupervised learning',
    'natural language processing', 'computer vision', 'image processing', 'object detection', 'yolo',
    'xgboost', 'lightgbm', 'catboost', 'random forest', 'decision tree', 'gradient boosting', 'svm',
    'feature engineering', 'feature selection', 'cross-validation', 'hyperparameter tuning',
    'hugging face', 'spacy', 'nltk', 'gensim', 'word2vec', 'fasttext',
    'mlflow', 'wandb', 'dvc', 'mlops', 'model deployment', 'model monitoring',
    'data visualization', 'data analysis', 'data mining', 'data preprocessing', 'eda',
    'pca', 'dimensionality reduction', 'anomaly detection', 'time series', 'forecasting',
    'jupyter', 'colab', 'kaggle', 'streamlit', 'gradio',
    'linux', 'ubuntu', 'bash', 'shell', 'powershell', 'nginx', 'apache', 'tomcat',
    'rest api', 'graphql', 'soap', 'microservices', 'websocket', 'grpc',
    'bootstrap', 'tailwind', 'material ui', 'mui', 'jquery', 'ajax',
    'android', 'ios', 'flutter', 'react native', 'xamarin',
    'blockchain', 'solidity', 'ethereum', 'smart contracts', 'web3',
    'tableau', 'power bi', 'excel', 'spss', 'r', 'matlab',
    'selenium', 'cypress', 'jest', 'junit', 'pytest', 'postman', 'cucumber',
    'terraform', 'ansible', 'puppet', 'chef', 'vagrant',
    'elasticsearch', 'kafka', 'rabbitmq', 'celery', 'airflow',
    'figma', 'adobe xd', 'sketch', 'invision', 'photoshop', 'illustrator',
    'oauth', 'jwt', 'sso', 'ldap', 'active directory',
    'cuda', 'opencl', 'mpi', 'openmp',
    'hadoop', 'spark', 'hive', 'pig', 'hbase',
    'unity', 'unreal engine', 'godot', 'blender',
    'maya', '3ds max', 'cinema 4d', 'after effects', 'premiere pro'
]

SOFT_SKILLS = [
    'communication', 'leadership', 'teamwork', 'problem solving', 'critical thinking',
    'time management', 'adaptability', 'creativity', 'collaboration', 'negotiation',
    'presentation', 'public speaking', 'mentoring', 'coaching', 'conflict resolution',
    'decision making', 'analytical thinking', 'attention to detail', 'multitasking',
    'stress management', 'interpersonal skills', 'emotional intelligence', 'empathy',
    'project management', 'agile', 'scrum', 'kanban', 'jira', 'confluence',
    'stakeholder management', 'client management', 'vendor management', 'budgeting'
]

def _extract_skills_keyword(text):
    """Fallback: Extract skills using keyword matching (original method)."""
    if not text:
        return []

    found_skills = set()
    text_lower = text.lower()
    text_clean = re.sub(r'[^\w\s]', ' ', text_lower)

    for skill in TECH_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_clean):
            found_skills.add(skill)

    for skill in SOFT_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_clean):
            found_skills.add(skill)

    return sorted(list(found_skills))

def extract_skills(text):
    """AI-Powered: Extract skills from resume text using Gemini, with keyword fallback."""
    if not text:
        return []

    # Try AI extraction
    prompt = f"""You are an expert resume analyzer. Extract all technical and soft skills from the following resume text.

Resume Text:
{text[:3000]}

Return ONLY a JSON array of skill strings. Example: ["python", "react", "machine learning", "leadership"]

Rules:
- Include programming languages, frameworks, tools, databases, cloud platforms, methodologies
- Include soft skills like leadership, communication, teamwork
- Use lowercase for all skills
- Be thorough — extract every skill mentioned
- Do NOT include job titles, company names, or degrees as skills
- Return ONLY the JSON array, nothing else"""

    response = call_gemini(prompt)
    if response:
        skills = parse_gemini_json(response)
        if skills and isinstance(skills, list) and len(skills) > 0:
            # Validate: ensure all items are strings
            valid_skills = [s.lower().strip() for s in skills if isinstance(s, str) and s.strip()]
            if valid_skills:
                print(f"[Resume Radar] AI extracted {len(valid_skills)} skills")
                return sorted(valid_skills)

    # Fallback to keyword matching
    print("[Resume Radar] Using keyword fallback for skill extraction")
    return _extract_skills_keyword(text)

# ======================= SCORING ENGINE =======================

def _calculate_match_score_keyword(candidate_skills_json, candidate_exp, candidate_edu, job_skills_text, min_exp,
                                    weight_skills=50, weight_experience=30, weight_education=20):
    """Fallback: Calculate match score using keyword matching (original method)."""
    total_weight = weight_skills + weight_experience + weight_education
    if total_weight == 0:
        total_weight = 100

    w_skills = (weight_skills / total_weight) * 100
    w_exp = (weight_experience / total_weight) * 100
    w_edu = (weight_education / total_weight) * 100

    candidate_skills = set()
    if candidate_skills_json:
        try:
            if isinstance(candidate_skills_json, str):
                candidate_skills = set(json.loads(candidate_skills_json))
            elif isinstance(candidate_skills_json, list):
                candidate_skills = set(candidate_skills_json)
        except:
            candidate_skills = set()

    job_skills = set()
    if job_skills_text:
        job_skills = set([s.strip().lower() for s in job_skills_text.split(',') if s.strip()])

    matched_skills = candidate_skills.intersection(job_skills)
    missing_skills = job_skills - candidate_skills

    skill_score = 0
    if job_skills:
        skill_score = (len(matched_skills) / len(job_skills)) * 100

    try:
        candidate_exp = float(candidate_exp) if candidate_exp else 0
    except:
        candidate_exp = 0

    try:
        min_exp = float(min_exp) if min_exp else 0
    except:
        min_exp = 0

    if min_exp == 0:
        exp_score = 100
    elif candidate_exp >= min_exp:
        exp_score = 100
    else:
        exp_score = (candidate_exp / min_exp) * 100

    edu_score = 100
    if candidate_edu:
        edu_lower = str(candidate_edu).lower()
        if 'phd' in edu_lower or 'doctorate' in edu_lower:
            edu_score = 100
        elif 'master' in edu_lower or 'm.tech' in edu_lower or 'mba' in edu_lower:
            edu_score = 95
        elif 'b.tech' in edu_lower or 'bachelor' in edu_lower or 'be' in edu_lower:
            edu_score = 90
        elif 'diploma' in edu_lower:
            edu_score = 70
    else:
        edu_score = 50

    total_score = (skill_score * w_skills / 100) + (exp_score * w_exp / 100) + (edu_score * w_edu / 100)

    return {
        'total_score': round(total_score, 1),
        'skill_score': round(skill_score, 1),
        'exp_score': round(exp_score, 1),
        'edu_score': round(edu_score, 1),
        'matched_skills': sorted(list(matched_skills)),
        'missing_skills': sorted(list(missing_skills)),
        'weight_skills': round(w_skills, 1),
        'weight_experience': round(w_exp, 1),
        'weight_education': round(w_edu, 1)
    }

def calculate_match_score(candidate_skills_json, candidate_exp, candidate_edu, job_skills_text, min_exp,
                          weight_skills=50, weight_experience=30, weight_education=20):
    """Calculate match score using fast keyword matching.
    Uses keyword method for speed since this runs on every dashboard page load.
    AI is reserved for one-time actions (skill extraction, question gen, answer scoring).
    """
    return _calculate_match_score_keyword(candidate_skills_json, candidate_exp, candidate_edu,
                                           job_skills_text, min_exp, weight_skills, weight_experience, weight_education)

# ======================= INTERVIEW QUESTIONS =======================

# Keep question bank as fallback
QUESTION_BANK = [
    # ===== EASY (1-15) =====
    {"question": "What is the difference between HTML and HTML5?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["semantic", "multimedia", "canvas", "local storage", "new tags", "audio", "video"], "max_score": 10},
    {"question": "What does CSS stand for and what is it used for?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["cascading", "style", "layout", "design", "presentation", "responsive"], "max_score": 10},
    {"question": "What is a variable in programming?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["storage", "value", "data", "name", "memory", "container"], "max_score": 10},
    {"question": "What is the difference between == and === in JavaScript?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["equality", "strict", "type", "comparison", "value", "datatype"], "max_score": 10},
    {"question": "What is the purpose of a database?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["store", "data", "retrieve", "organize", "query", "structured"], "max_score": 10},
    {"question": "What is Git used for?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["version control", "track", "collaboration", "commit", "branch", "history"], "max_score": 10},
    {"question": "What is the difference between frontend and backend development?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["client", "server", "user interface", "database", "browser", "api"], "max_score": 10},
    {"question": "What is an API?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["application", "interface", "communication", "data", "request", "response"], "max_score": 10},
    {"question": "What is responsive web design?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["mobile", "screen size", "adapt", "css", "media queries", "flexible"], "max_score": 10},
    {"question": "What is the purpose of testing in software development?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["bug", "quality", "verify", "automated", "manual", "reliable"], "max_score": 10},
    {"question": "What is cloud computing?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["internet", "server", "storage", "scalable", "aws", "azure"], "max_score": 10},
    {"question": "What is a function in programming?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["reusable", "block", "code", "parameter", "return", "call"], "max_score": 10},
    {"question": "What is an array or list?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["collection", "index", "elements", "ordered", "iterate", "store"], "max_score": 10},
    {"question": "What is a bug in software?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["error", "defect", "unexpected", "fix", "debug", "issue"], "max_score": 10},
    {"question": "What is a URL?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["uniform", "locator", "address", "web", "domain", "http"], "max_score": 10},

    # ===== MEDIUM (16-35) =====
    {"question": "Explain the difference between REST and GraphQL APIs.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["rest", "graphql", "api", "endpoint", "query", "http", "json"], "max_score": 10},
    {"question": "What is the difference between SQL and NoSQL databases?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["sql", "nosql", "relational", "document", "schema", "scalability", "mongodb", "postgresql"], "max_score": 10},
    {"question": "Explain how Docker containers differ from virtual machines.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["docker", "container", "virtual machine", "vm", "hypervisor", "os", "image", "lightweight"], "max_score": 10},
    {"question": "What are the key principles of Object-Oriented Programming?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["encapsulation", "inheritance", "polymorphism", "abstraction", "class", "object", "oop"], "max_score": 10},
    {"question": "Explain the concept of microservices architecture.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["microservices", "monolith", "api gateway", "service", "independent", "scalable", "deployment"], "max_score": 10},
    {"question": "What is the difference between Python lists and tuples?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["mutable", "immutable", "list", "tuple", "modify", "performance", "hashable"], "max_score": 10},
    {"question": "Explain how JWT authentication works.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["jwt", "json web token", "authentication", "header", "payload", "signature", "token", "stateless"], "max_score": 10},
    {"question": "What is the purpose of CI/CD pipelines?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["ci/cd", "continuous integration", "continuous deployment", "automation", "testing", "jenkins", "github actions"], "max_score": 10},
    {"question": "Describe the Agile software development methodology.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["agile", "scrum", "sprint", "iterative", "backlog", "daily standup", "user story"], "max_score": 10},
    {"question": "What is the difference between synchronous and asynchronous programming?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["synchronous", "asynchronous", "blocking", "non-blocking", "callback", "promise", "async", "await"], "max_score": 10},
    {"question": "Describe a challenging project you worked on and how you overcame obstacles.", "category": "Behavioral", "difficulty": "Medium", "expected_keywords": ["challenge", "problem", "solution", "team", "communication", "leadership", "result"], "max_score": 10},
    {"question": "How do you handle tight deadlines and multiple priorities?", "category": "Behavioral", "difficulty": "Medium", "expected_keywords": ["priority", "deadline", "time management", "organization", "planning", "stress", "efficiency"], "max_score": 10},
    {"question": "Tell me about a time you had a conflict with a team member.", "category": "Behavioral", "difficulty": "Medium", "expected_keywords": ["conflict", "resolution", "communication", "understanding", "compromise", "teamwork", "professional"], "max_score": 10},
    {"question": "How do you stay updated with the latest technology trends?", "category": "Behavioral", "difficulty": "Medium", "expected_keywords": ["learning", "course", "documentation", "community", "blog", "conference", "practice"], "max_score": 10},
    {"question": "Describe a situation where you had to learn a new technology quickly.", "category": "Behavioral", "difficulty": "Medium", "expected_keywords": ["learn", "quick", "adapt", "resource", "documentation", "tutorial", "project"], "max_score": 10},
    {"question": "How would you optimize a slow-running database query?", "category": "Problem Solving", "difficulty": "Medium", "expected_keywords": ["index", "query optimization", "explain", "normalization", "caching", "partition", "denormalization"], "max_score": 10},
    {"question": "Design a URL shortening service like bit.ly.", "category": "Problem Solving", "difficulty": "Medium", "expected_keywords": ["hash", "database", "scalable", "redis", "collision", "base62", "encoding"], "max_score": 10},
    {"question": "How would you handle a production system outage?", "category": "Problem Solving", "difficulty": "Medium", "expected_keywords": ["monitoring", "rollback", "debug", "log", "incident", "communication", "postmortem"], "max_score": 10},
    {"question": "Explain how you would implement a caching strategy for a high-traffic website.", "category": "Problem Solving", "difficulty": "Medium", "expected_keywords": ["cache", "redis", "cdn", "ttl", "invalidation", "memcached", "performance"], "max_score": 10},
    {"question": "How would you design a secure user authentication system?", "category": "Problem Solving", "difficulty": "Medium", "expected_keywords": ["hash", "salt", "jwt", "oauth", "encryption", "https", "mfa", "session"], "max_score": 10},

    # ===== HARD (36-50) =====
    {"question": "Design a distributed messaging system like Kafka. What are the key components and trade-offs?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["producer", "consumer", "topic", "partition", "broker", "zookeeper", "scalability", "fault tolerance", "throughput"], "max_score": 10},
    {"question": "How would you design a rate limiter for an API handling millions of requests per second?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["token bucket", "sliding window", "redis", "throttle", "algorithm", "distributed", "counter"], "max_score": 10},
    {"question": "Explain how you would design YouTube's video streaming architecture.", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["cdn", "storage", "encoding", "transcoding", "metadata", "recommendation", "bandwidth", "adaptive bitrate"], "max_score": 10},
    {"question": "Design a ride-sharing service like Uber. How do you match drivers to riders in real-time?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["geohash", "matching", "real-time", "gps", "dispatch", "pricing", "surge", "microservices"], "max_score": 10},
    {"question": "How would you handle 1 million concurrent users on a web application?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["load balancer", "auto scaling", "caching", "database", "sharding", "cdn", "queue", "stateless"], "max_score": 10},
    {"question": "Design a simplified search engine like Google. What are the core components?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["crawler", "indexer", "ranking", "pagerank", "inverted index", "query", "relevance", "scalable"], "max_score": 10},
    {"question": "Explain database sharding strategies. When would you use each approach?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["horizontal", "vertical", "range", "hash", "directory", "shard key", "rebalancing", "cross-shard"], "max_score": 10},
    {"question": "Explain the CAP theorem with real-world examples where you must make trade-offs.", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["consistency", "availability", "partition tolerance", "cp", "ap", "network", "trade-off", "distributed"], "max_score": 10},
    {"question": "How would you design a payment gateway system that handles transactions securely?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["idempotency", "encryption", "pci dss", "fraud detection", "settlement", "reconciliation", "retry", "atomicity"], "max_score": 10},
    {"question": "Compare synchronous vs asynchronous communication patterns in microservices. When to use which?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["rest", "grpc", "message queue", "event driven", "saga", "coupling", "latency", "reliability"], "max_score": 10},
    {"question": "Design an event-driven architecture for an e-commerce platform.", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["event bus", "kafka", "pub sub", "event sourcing", "cqrs", "async", "decoupled", "workflow"], "max_score": 10},
    {"question": "How would you build a recommendation system like Netflix or Amazon?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["collaborative filtering", "content based", "matrix factorization", "deep learning", "embedding", "cold start", "a/b testing"], "max_score": 10},
    {"question": "How do you ensure data consistency across distributed microservices?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["saga pattern", "two phase commit", "eventual consistency", "compensating transaction", "outbox", "idempotency"], "max_score": 10},
    {"question": "Describe zero-downtime deployment strategies for a large-scale application.", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["blue green", "canary", "rolling", "feature toggle", "database migration", "rollback", "health check"], "max_score": 10},
    {"question": "Design a real-time collaborative editor like Google Docs. How do you handle concurrent edits?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["operational transformation", "crdt", "websocket", "conflict resolution", "sync", "latency", "merge"], "max_score": 10},

    # ===== MACHINE LEARNING / AI / DATA SCIENCE - EASY =====
    {"question": "What is Machine Learning? How is it different from traditional programming?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["machine learning", "data", "pattern", "training", "prediction", "algorithm", "learn"], "max_score": 10},
    {"question": "What is the difference between Supervised and Unsupervised Learning?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["supervised", "unsupervised", "labeled", "unlabeled", "classification", "clustering", "regression"], "max_score": 10},
    {"question": "What is the difference between Classification and Regression?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["classification", "regression", "categorical", "continuous", "label", "predict", "output"], "max_score": 10},
    {"question": "What is overfitting in machine learning and how can you prevent it?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["overfitting", "training", "generalization", "regularization", "validation", "dropout", "cross-validation"], "max_score": 10},
    {"question": "What is a Neural Network? Explain its basic structure.", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["neural network", "neuron", "layer", "input", "output", "hidden", "weights", "activation"], "max_score": 10},
    {"question": "What is the purpose of a training set, validation set, and test set?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["training", "validation", "test", "split", "evaluation", "generalization", "data"], "max_score": 10},
    {"question": "What are common Python libraries used in Data Science and Machine Learning?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["pandas", "numpy", "scikit-learn", "matplotlib", "tensorflow", "pytorch", "seaborn", "keras"], "max_score": 10},
    {"question": "What is a confusion matrix? What metrics can you derive from it?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["confusion matrix", "true positive", "false positive", "precision", "recall", "accuracy", "f1"], "max_score": 10},
    {"question": "What is Feature Engineering? Why is it important?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["feature", "engineering", "transform", "create", "model", "performance", "variable", "input"], "max_score": 10},
    {"question": "What is Exploratory Data Analysis (EDA)?", "category": "Technical", "difficulty": "Easy", "expected_keywords": ["eda", "visualization", "statistics", "distribution", "correlation", "missing values", "outliers", "patterns"], "max_score": 10},

    # ===== MACHINE LEARNING / AI / DATA SCIENCE - MEDIUM =====
    {"question": "Explain the Bias-Variance Tradeoff in machine learning.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["bias", "variance", "tradeoff", "underfitting", "overfitting", "complexity", "generalization", "error"], "max_score": 10},
    {"question": "How does Gradient Descent work? What are its variants?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["gradient descent", "learning rate", "loss function", "sgd", "batch", "mini-batch", "convergence", "optimization"], "max_score": 10},
    {"question": "What is the difference between Decision Trees, Random Forest, and Gradient Boosting?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["decision tree", "random forest", "gradient boosting", "ensemble", "bagging", "boosting", "xgboost", "overfitting"], "max_score": 10},
    {"question": "Explain Precision, Recall, F1-Score, and when to use each.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["precision", "recall", "f1", "accuracy", "imbalanced", "threshold", "true positive", "false negative"], "max_score": 10},
    {"question": "What is Cross-Validation? Why is K-Fold Cross-Validation preferred?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["cross-validation", "k-fold", "training", "validation", "overfitting", "robust", "evaluation", "split"], "max_score": 10},
    {"question": "Explain the difference between L1 (Lasso) and L2 (Ridge) Regularization.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["l1", "l2", "lasso", "ridge", "regularization", "penalty", "feature selection", "overfitting", "sparsity"], "max_score": 10},
    {"question": "What is a Convolutional Neural Network (CNN)? Where is it used?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["cnn", "convolutional", "filter", "kernel", "pooling", "image", "feature map", "classification", "deep learning"], "max_score": 10},
    {"question": "What is a Recurrent Neural Network (RNN)? How does LSTM solve the vanishing gradient problem?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["rnn", "recurrent", "sequence", "lstm", "vanishing gradient", "memory", "time series", "gates"], "max_score": 10},
    {"question": "What is Natural Language Processing (NLP)? Name some common NLP tasks.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["nlp", "tokenization", "sentiment analysis", "named entity", "text classification", "embedding", "word2vec", "language model"], "max_score": 10},
    {"question": "How do you handle missing data and outliers in a dataset?", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["missing", "imputation", "mean", "median", "outlier", "iqr", "z-score", "drop", "interpolation"], "max_score": 10},
    {"question": "What is Dimensionality Reduction? Explain PCA.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["dimensionality reduction", "pca", "principal component", "variance", "eigenvalue", "curse of dimensionality", "feature reduction"], "max_score": 10},
    {"question": "Explain the difference between Batch Normalization and Dropout in deep learning.", "category": "Technical", "difficulty": "Medium", "expected_keywords": ["batch normalization", "dropout", "regularization", "training", "overfitting", "normalization", "layer", "deep learning"], "max_score": 10},

    # ===== MACHINE LEARNING / AI / DATA SCIENCE - HARD =====
    {"question": "Explain the Transformer architecture and how Self-Attention works.", "category": "Technical", "difficulty": "Hard", "expected_keywords": ["transformer", "self-attention", "query", "key", "value", "positional encoding", "multi-head", "encoder", "decoder"], "max_score": 10},
    {"question": "What are Generative Adversarial Networks (GANs)? Explain the generator-discriminator dynamic.", "category": "Technical", "difficulty": "Hard", "expected_keywords": ["gan", "generator", "discriminator", "adversarial", "training", "loss", "fake", "real", "nash equilibrium"], "max_score": 10},
    {"question": "Design an end-to-end ML pipeline for a production fraud detection system.", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["pipeline", "feature engineering", "model training", "deployment", "monitoring", "imbalanced data", "real-time", "a/b testing"], "max_score": 10},
    {"question": "Explain Reinforcement Learning. What are the key components (Agent, Environment, Reward)?", "category": "Technical", "difficulty": "Hard", "expected_keywords": ["reinforcement learning", "agent", "environment", "reward", "policy", "q-learning", "exploration", "exploitation", "state"], "max_score": 10},
    {"question": "How would you deploy and monitor a machine learning model in production (MLOps)?", "category": "System Design", "difficulty": "Hard", "expected_keywords": ["mlops", "deployment", "monitoring", "drift", "retraining", "ci/cd", "docker", "api", "versioning", "logging"], "max_score": 10},
    {"question": "Explain Transfer Learning. How do pre-trained models like BERT and ResNet work?", "category": "Technical", "difficulty": "Hard", "expected_keywords": ["transfer learning", "pre-trained", "fine-tuning", "bert", "resnet", "feature extraction", "domain", "layers"], "max_score": 10},
    {"question": "How do you handle severe class imbalance in a classification problem?", "category": "Problem Solving", "difficulty": "Hard", "expected_keywords": ["imbalance", "oversampling", "smote", "undersampling", "class weight", "auc-roc", "precision-recall", "threshold", "f1"], "max_score": 10},
    {"question": "Compare different model interpretability techniques (SHAP, LIME, Feature Importance).", "category": "Technical", "difficulty": "Hard", "expected_keywords": ["interpretability", "shap", "lime", "feature importance", "explainability", "black box", "local", "global"], "max_score": 10},
]

def _generate_questions_bank(job_skills_text, candidate_skills_text, num_questions=5):
    """Fallback: Generate questions from fixed bank (original method)."""
    job_skills = set()
    if job_skills_text:
        job_skills = set([s.strip().lower() for s in job_skills_text.split(',') if s.strip()])

    candidate_skills = set()
    if candidate_skills_text:
        candidate_skills = set([s.strip().lower() for s in candidate_skills_text.split(',') if s.strip()])

    scored_questions = []
    for q in QUESTION_BANK:
        score = 0
        keywords = q.get('expected_keywords', [])
        for kw in keywords:
            if kw.lower() in job_skills:
                score += 2
            if kw.lower() in candidate_skills:
                score += 1
        scored_questions.append((score, q))

    scored_questions.sort(key=lambda x: x[0], reverse=True)

    selected = []
    categories = set()
    difficulties = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    target_diff = {'Easy': 2, 'Medium': 2, 'Hard': 1}

    for score, q in scored_questions:
        if len(selected) >= num_questions:
            break
        diff = q.get('difficulty', 'Medium')
        if difficulties[diff] < target_diff.get(diff, 1):
            selected.append(q)
            categories.add(q.get('category', 'Technical'))
            difficulties[diff] += 1

    for score, q in scored_questions:
        if len(selected) >= num_questions:
            break
        if q not in selected:
            selected.append(q)
            categories.add(q.get('category', 'Technical'))

    while len(selected) < num_questions:
        q = random.choice([x[1] for x in scored_questions if x[1] not in selected])
        if q not in selected:
            selected.append(q)

    random.shuffle(selected)
    return selected[:num_questions]

def generate_interview_questions(job_skills_text, candidate_skills_text, num_questions=5):
    """AI-Powered: Generate interview questions using Gemini, with question bank fallback."""
    
    # Calculate difficulty distribution
    if num_questions <= 3:
        easy, medium, hard = 1, 1, 1
    elif num_questions <= 5:
        easy, medium, hard = 2, 2, 1
    else:
        easy = num_questions // 3
        medium = num_questions // 3
        hard = num_questions - easy - medium

    prompt = f"""You are an expert technical interviewer. Generate exactly {num_questions} UNIQUE interview questions.

Job Required Skills: {job_skills_text}
Candidate's Skills: {candidate_skills_text}

Difficulty Mix: {easy} Easy, {medium} Medium, {hard} Hard

Return ONLY a JSON array with exactly {num_questions} objects. Each question must have this format:
[
    {{
        "question": "Your question text here?",
        "category": "Technical",
        "difficulty": "Easy",
        "expected_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6"],
        "max_score": 10
    }}
]

CRITICAL RULES:
- Generate EXACTLY {num_questions} questions, no more, no less
- Every question MUST be completely DIFFERENT from each other — NO duplicate or similar questions
- Each question should cover a DIFFERENT topic or skill
- Categories to mix: "Technical", "Behavioral", "Problem Solving", "System Design"
- expected_keywords: 5-8 keywords that a good answer should contain (lowercase)
- max_score is always 10
- Make questions specific to the skills mentioned, not generic
- Return ONLY the JSON array, nothing else"""

    response = call_gemini(prompt)
    if response:
        questions = parse_gemini_json(response)
        if questions and isinstance(questions, list) and len(questions) >= num_questions:
            # Validate each question has required fields
            valid_questions = []
            seen_questions = set()  # Track unique questions
            for q in questions:
                if isinstance(q, dict) and 'question' in q:
                    q_text = q.get('question', '').strip()
                    # Skip duplicates
                    if q_text.lower() in seen_questions:
                        continue
                    seen_questions.add(q_text.lower())
                    
                    validated = {
                        'question': q_text,
                        'category': q.get('category', 'Technical'),
                        'difficulty': q.get('difficulty', 'Medium'),
                        'expected_keywords': q.get('expected_keywords', []),
                        'max_score': 10
                    }
                    # Ensure expected_keywords is a list of strings
                    if not isinstance(validated['expected_keywords'], list):
                        validated['expected_keywords'] = []
                    validated['expected_keywords'] = [str(kw).lower() for kw in validated['expected_keywords']]
                    valid_questions.append(validated)

            if len(valid_questions) >= num_questions:
                print(f"[Resume Radar] AI generated {len(valid_questions)} unique questions")
                return valid_questions[:num_questions]

    # Fallback to question bank
    print("[Resume Radar] Using question bank fallback for question generation")
    return _generate_questions_bank(job_skills_text, candidate_skills_text, num_questions)

# ======================= AI FOLLOW-UP QUESTIONS =======================

def generate_follow_up(question, answer):
    """AI-Powered: Generate a follow-up question based on the candidate's answer."""
    
    prompt = f"""You are an expert technical interviewer conducting a live interview. 
The candidate just answered a question. Based on their answer, ask ONE smart follow-up question.

Original Question: {question}
Candidate's Answer: {answer}

Rules:
- If the answer is vague/shallow, dig deeper into the topic
- If the answer is wrong, gently challenge it with a clarifying question
- If the answer is good, ask a harder related question to test depth
- Keep it conversational and natural, like a real interviewer
- Return ONLY the follow-up question text, nothing else
- Keep it under 2 sentences
- Make it specific to what they actually said"""

    response = call_gemini(prompt)
    if response:
        # Clean up the response
        follow_up = response.strip().strip('"').strip("'")
        if follow_up and len(follow_up) > 10:
            print(f"[Resume Radar] AI generated follow-up question")
            return follow_up
    
    # Smart fallback based on answer length
    if len(answer.strip()) < 50:
        return f"Can you elaborate more on your answer? What specific examples or details can you provide about this topic?"
    else:
        return f"That's a good start. Can you explain how you would apply this knowledge in a real-world project or production environment?"

# ======================= AI RESUME TIPS =======================

def generate_resume_tips(resume_text, extracted_skills):
    """AI-Powered: Analyze resume and give improvement tips."""
    
    skills_str = extracted_skills if extracted_skills else "None detected"
    # Truncate resume to avoid token limits
    resume_snippet = resume_text[:3000] if resume_text else "No resume text"
    
    prompt = f"""You are an expert career coach and resume reviewer. Analyze this resume and give exactly 5 specific improvement tips.

Resume Text (snippet): {resume_snippet}

Detected Skills: {skills_str}

Return EXACTLY this JSON format (no markdown, no extra text):
{{
    "score": 72,
    "tips": [
        {{"icon": "skill", "title": "Add In-Demand Skills", "detail": "Your resume lacks cloud skills like AWS, Docker, Kubernetes which are highly demanded."}},
        {{"icon": "format", "title": "Tip title here", "detail": "Specific actionable advice here"}},
        {{"icon": "achievement", "title": "Tip title here", "detail": "Specific actionable advice here"}},
        {{"icon": "keyword", "title": "Tip title here", "detail": "Specific actionable advice here"}},
        {{"icon": "section", "title": "Tip title here", "detail": "Specific actionable advice here"}}
    ]
}}

Rules:
- score: overall resume strength 0-100
- icon must be one of: skill, format, achievement, keyword, section, experience, project
- Each tip must be specific to THIS resume, not generic
- Focus on: missing trending skills, weak sections, lack of metrics/numbers, ATS optimization, project descriptions
- Keep each detail under 30 words"""

    response = call_gemini(prompt)
    if response:
        try:
            # Clean response
            clean = response.strip()
            if clean.startswith('```'): 
                clean = clean.split('\n', 1)[1] if '\n' in clean else clean[3:]
            if clean.endswith('```'): clean = clean[:-3]
            clean = clean.strip()
            
            data = json.loads(clean)
            if 'tips' in data and 'score' in data:
                print(f"[Resume Radar] AI generated {len(data['tips'])} resume tips, score: {data['score']}")
                return data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Resume Radar] Resume tips JSON parse error: {e}")
    
    # Fallback tips
    skills_list = [s.strip() for s in skills_str.split(',') if s.strip()] if skills_str != "None detected" else []
    return {
        "score": 55,
        "tips": [
            {"icon": "skill", "title": "Add More Technical Skills", "detail": f"You have {len(skills_list)} skills listed. Top resumes have 10-15 relevant technical skills."},
            {"icon": "achievement", "title": "Add Quantifiable Achievements", "detail": "Use numbers: 'Improved performance by 40%' instead of 'Improved performance'."},
            {"icon": "project", "title": "Describe Projects Better", "detail": "For each project, mention: tech stack used, your role, and measurable impact."},
            {"icon": "keyword", "title": "Optimize for ATS", "detail": "Include exact keywords from job descriptions. ATS systems scan for keyword matches."},
            {"icon": "format", "title": "Keep it Concise", "detail": "Ideal resume length is 1-2 pages. Remove outdated or irrelevant information."}
        ]
    }

# ======================= ANSWER SCORING =======================

def _score_answer_keyword(answer_text, expected_keywords):
    """Fallback: Score answer using keyword matching (original method)."""
    if not answer_text or not answer_text.strip():
        return {
            'score': 0,
            'max_score': 10,
            'keywords_matched': [],
            'feedback': 'No answer provided. Please attempt the question.'
        }

    answer_lower = answer_text.lower()
    answer_words = set(re.findall(r'\b\w+\b', answer_lower))

    matched = []
    for kw in expected_keywords:
        kw_lower = kw.lower()
        if kw_lower in answer_lower or any(kw_lower in word for word in answer_words):
            matched.append(kw)

    coverage = len(matched) / len(expected_keywords) if expected_keywords else 0

    if coverage >= 0.8:
        score = 10
    elif coverage >= 0.6:
        score = 8
    elif coverage >= 0.4:
        score = 6
    elif coverage >= 0.2:
        score = 4
    else:
        score = 2

    missing = [kw for kw in expected_keywords if kw not in matched]

    if score >= 8:
        feedback = f"Excellent answer! You covered most key concepts. Well done!"
    elif score >= 6:
        feedback = f"Good answer. You covered some important points. Consider adding more depth on: {', '.join(missing[:3])}"
    elif score >= 4:
        feedback = f"Fair attempt. You missed several key concepts: {', '.join(missing[:5])}. Please review these topics."
    else:
        feedback = f"Needs improvement. Key concepts missing: {', '.join(missing)}. We recommend studying these areas before retrying."

    return {
        'score': score,
        'max_score': 10,
        'keywords_matched': matched,
        'feedback': feedback
    }

def score_answer(answer_text, expected_keywords):
    """AI-Powered: Score answer using Gemini for intelligent evaluation, with keyword fallback."""
    if not answer_text or not answer_text.strip():
        return {
            'score': 0,
            'max_score': 10,
            'keywords_matched': [],
            'feedback': 'No answer provided. Please attempt the question.'
        }

    prompt = f"""You are an expert interview evaluator. Score the following answer.

Expected Topics/Keywords: {json.dumps(expected_keywords)}
Candidate's Answer: {answer_text}

Evaluate the answer based on:
1. Relevance — Does it address the question?
2. Depth — Does it show real understanding?
3. Accuracy — Are the concepts correct?
4. Clarity — Is it well-explained?

Return ONLY a JSON object with exactly these keys:
{{
    "score": 7,
    "max_score": 10,
    "keywords_matched": ["keyword1", "keyword2"],
    "feedback": "Your detailed feedback here explaining what was good and what can be improved."
}}

Rules:
- score must be an integer from 0 to 10
- max_score is always 10
- keywords_matched: list of expected keywords that the answer actually covers (even if not exact words, but the concept is covered)
- feedback: 2-3 sentences — mention what was good, what was missing, and how to improve
- Be fair but strict — don't give high scores for vague or generic answers
- An answer that just lists keywords without explanation should get 4-5, not 8-10
- Return ONLY the JSON object, nothing else"""

    response = call_gemini(prompt)
    if response:
        result = parse_gemini_json(response)
        if result and isinstance(result, dict) and 'score' in result:
            try:
                score = int(result.get('score', 0))
                score = max(0, min(10, score))  # Clamp between 0-10
                
                keywords_matched = result.get('keywords_matched', [])
                if not isinstance(keywords_matched, list):
                    keywords_matched = []
                keywords_matched = [str(kw) for kw in keywords_matched]
                
                feedback = str(result.get('feedback', ''))
                if not feedback:
                    feedback = 'Answer evaluated by AI.'

                print(f"[Resume Radar] AI scored answer: {score}/10")
                return {
                    'score': score,
                    'max_score': 10,
                    'keywords_matched': keywords_matched,
                    'feedback': feedback
                }
            except (ValueError, TypeError):
                pass

    # Fallback to keyword matching
    print("[Resume Radar] Using keyword fallback for answer scoring")
    return _score_answer_keyword(answer_text, expected_keywords)

# ======================= BATCH ANSWER SCORING (FASTER) =======================

def batch_score_answers(questions_and_answers):
    """AI-Powered: Score ALL answers in a single API call for speed.
    
    Args:
        questions_and_answers: list of dicts with 'question', 'answer', 'expected_keywords'
    
    Returns:
        list of score results (same format as score_answer)
    """
    if not questions_and_answers:
        return []

    # Build batch prompt
    qa_text = ""
    for i, qa in enumerate(questions_and_answers):
        answer = qa.get('answer', '').strip()
        if not answer:
            answer = "(No answer provided)"
        qa_text += f"""
Q{i+1}: {qa.get('question', '')}
Expected Keywords: {json.dumps(qa.get('expected_keywords', []))}
Answer: {answer}
---
"""

    prompt = f"""You are an expert interview evaluator. Score ALL the following answers.

{qa_text}

Return ONLY a JSON array with exactly {len(questions_and_answers)} objects, one per question in order.
Each object must have:
{{
    "score": 7,
    "max_score": 10,
    "keywords_matched": ["keyword1", "keyword2"],
    "feedback": "2-3 sentence feedback."
}}

Rules:
- score: integer 0 to 10
- max_score: always 10
- keywords_matched: expected keywords the answer actually covers
- feedback: what was good, what was missing, how to improve
- No answer = score 0
- Just listing keywords without explanation = score 4-5
- Be fair but strict
- Return ONLY the JSON array"""

    response = call_gemini(prompt)
    if response:
        results = parse_gemini_json(response)
        if results and isinstance(results, list) and len(results) >= len(questions_and_answers):
            scored = []
            for i, r in enumerate(results[:len(questions_and_answers)]):
                if isinstance(r, dict) and 'score' in r:
                    try:
                        score = max(0, min(10, int(r.get('score', 0))))
                        keywords_matched = r.get('keywords_matched', [])
                        if not isinstance(keywords_matched, list):
                            keywords_matched = []
                        feedback = str(r.get('feedback', 'Answer evaluated by AI.'))
                        scored.append({
                            'score': score,
                            'max_score': 10,
                            'keywords_matched': [str(kw) for kw in keywords_matched],
                            'feedback': feedback
                        })
                    except:
                        scored.append(_score_answer_keyword(
                            questions_and_answers[i].get('answer', ''),
                            questions_and_answers[i].get('expected_keywords', [])
                        ))
                else:
                    scored.append(_score_answer_keyword(
                        questions_and_answers[i].get('answer', ''),
                        questions_and_answers[i].get('expected_keywords', [])
                    ))
            
            print(f"[Resume Radar] AI batch scored {len(scored)} answers in one call")
            return scored

    # Fallback: score individually with keyword method
    print("[Resume Radar] Using keyword fallback for batch scoring")
    return [_score_answer_keyword(qa.get('answer', ''), qa.get('expected_keywords', [])) for qa in questions_and_answers]

# ======================= PDF REPORT GENERATION =======================

def generate_pdf_report(interview, responses, candidate, job, report_folder):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"interview_report_{interview.id}_{timestamp}.pdf"
    filepath = os.path.join(report_folder, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#16213e'),
        spaceAfter=12,
        spaceBefore=12
    )

    normal_style = styles["BodyText"]
    normal_style.fontSize = 10

    story = []

    story.append(Paragraph("RESUME RADAR - AI INTERVIEW REPORT", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("CANDIDATE INFORMATION", heading_style))
    info_data = [
        ['Name:', candidate.full_name or 'N/A'],
        ['Email:', candidate.email or 'N/A'],
        ['Phone:', candidate.phone or 'N/A'],
        ['Job Position:', job.title if job else 'N/A'],
        ['Interview Date:', interview.completed_at.strftime("%B %d, %Y") if interview.completed_at else 'N/A'],
    ]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    total = interview.total_score or 0
    max_total = interview.max_possible_score or 1
    percentage = (total / max_total * 100) if max_total > 0 else 0

    story.append(Paragraph("OVERALL PERFORMANCE", heading_style))
    score_data = [
        ['Total Score:', f"{total:.1f} / {max_total:.1f}"],
        ['Percentage:', f"{percentage:.1f}%"],
        ['Status:', 'PASSED' if percentage >= 60 else 'NEEDS IMPROVEMENT'],
    ]
    score_table = Table(score_data, colWidths=[2*inch, 4*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))

    # Anti-cheat info
    if interview.tab_switches or interview.copy_paste_attempts:
        story.append(Paragraph("PROCTORING LOG", heading_style))
        cheat_data = [
            ['Tab Switches:', str(interview.tab_switches or 0)],
            ['Copy/Paste Attempts:', str(interview.copy_paste_attempts or 0)],
        ]
        cheat_table = Table(cheat_data, colWidths=[2*inch, 4*inch])
        cheat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fff3cd')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(cheat_table)
        story.append(Spacer(1, 20))

    story.append(Paragraph("DETAILED RESPONSES", heading_style))

    for i, resp in enumerate(responses):
        q_num = i + 1
        story.append(Paragraph(f"<b>Question {q_num}:</b> {resp.question_text}", normal_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Answer:</b> {resp.answer_text or 'No answer provided'}", normal_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Score:</b> {resp.score:.1f} / {resp.max_score:.1f}", normal_style))

        kw_text = ""
        if resp.keywords_matched:
            try:
                kws = json.loads(resp.keywords_matched)
                kw_text = ", ".join(kws) if kws else "None"
            except:
                kw_text = str(resp.keywords_matched)
        story.append(Paragraph(f"<b>Keywords Matched:</b> {kw_text}", normal_style))

        if resp.feedback:
            story.append(Paragraph(f"<b>AI Feedback:</b> <i>{resp.feedback}</i>", normal_style))

        story.append(Spacer(1, 12))

    # AI-powered hiring recommendation
    story.append(Paragraph("AI HIRING RECOMMENDATION", heading_style))

    # Try AI recommendation
    rec = None
    try:
        rec_prompt = f"""You are an expert HR consultant. Based on the interview results, provide a brief hiring recommendation.

Candidate: {candidate.full_name}
Job Position: {job.title if job else 'N/A'}
Score: {percentage:.1f}%
Tab Switches (possible cheating): {interview.tab_switches or 0}
Copy/Paste Attempts: {interview.copy_paste_attempts or 0}

Provide a 2-3 sentence hiring recommendation. Be professional and concise.
Consider the score percentage, and any proctoring flags.
Return ONLY the recommendation text, no JSON."""

        ai_rec = call_gemini(rec_prompt)
        if ai_rec and len(ai_rec.strip()) > 20:
            rec = ai_rec.strip()
    except:
        pass

    # Fallback recommendation
    if not rec:
        if percentage >= 80:
            rec = "STRONG HIRE - Candidate demonstrated excellent technical knowledge and communication skills."
        elif percentage >= 60:
            rec = "HIRE - Candidate meets most requirements with satisfactory performance."
        elif percentage >= 40:
            rec = "CONDITIONAL - Candidate shows potential but needs improvement in key areas. Consider follow-up interview."
        else:
            rec = "NO HIRE - Candidate does not meet the required skill level for this position."

    story.append(Paragraph(rec, normal_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<i>This report was auto-generated by Resume Radar AI Screening System powered by Google Gemini.</i>", 
                          ParagraphStyle('Footer', parent=normal_style, alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    return filepath
