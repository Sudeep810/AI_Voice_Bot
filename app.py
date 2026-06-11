from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
from gtts import gTTS
import json, datetime, os, re, uuid, csv, io
import pdfplumber
import pandas as pd
from docx import Document
from collections import Counter
from functools import wraps
from dotenv import load_dotenv
import os
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(app)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

model = SentenceTransformer('all-mpnet-base-v2')                                                                                                                                                                    

os.makedirs('static/audio', exist_ok=True)

# ─── FAQ Helpers ─────────────────────────────────────────────

def parse_faq_text(text):
    faqs = []
    pattern = re.compile(
        r'(?:Q\s*[:：]\s*|Question\s*[:：]\s*)(.+?)\n\s*(?:A\s*[:：]\s*|Answer\s*[:：]\s*)(.+?)(?=\n\s*(?:Q\s*[:：]|Question\s*[:：])|$)',
        re.IGNORECASE | re.DOTALL
    )
    for match in pattern.finditer(text):
        q = match.group(1).strip()
        a = match.group(2).strip()
        if q and a:
            faqs.append({'question': q, 'answer': a})
    return faqs

def load_faq(fp):
    try:
        text = open(fp, encoding='utf-8').read()
        return parse_faq_text(text)
    except FileNotFoundError:
        return []

def save_faq(faqs):
    with open('faq.txt', 'w', encoding='utf-8') as f:
        for item in faqs:
            f.write(f"Q: {item['question']}\nA: {item['answer']}\n\n")

def build_embeddings(faqs):
    if not faqs:
        return None
    return model.encode(
        [f['question'] + ' ' + f['answer'] for f in faqs],
        convert_to_tensor=True
    )

def get_logs():
    try:
        return json.load(open('logs.json', encoding='utf-8'))
    except:
        return []

def save_logs(logs):
    json.dump(logs, open('logs.json', 'w', encoding='utf-8'), indent=2)

# ─── Load on startup ─────────────────────────────────────────

faqs = load_faq('faq.txt')
embeddings = build_embeddings(faqs)

# ─── Admin Auth ──────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        error = 'Wrong password. Try: peoplexm123'
    return f'''
    <!DOCTYPE html>
    <html><head><title>Admin Login</title>
    <style>
      body{{font-family:system-ui,sans-serif;background:#f4f4f8;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
      .box{{background:#fff;border:1px solid #e5e5e5;border-radius:14px;padding:32px;width:320px;text-align:center}}
      h2{{font-size:18px;font-weight:600;margin-bottom:6px}}
      p{{font-size:13px;color:#888;margin-bottom:20px}}
      input{{width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px;margin-bottom:12px;box-sizing:border-box}}
      button{{width:100%;padding:11px;background:#534AB7;color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer;font-weight:500}}
      .err{{color:#791F1F;font-size:13px;margin-bottom:10px}}
    </style></head>
    <body><div class="box">
      <h2>Admin Access</h2>
      <p>PeopleXM Voice Bot</p>
      {"<div class='err'>"+error+"</div>" if error else ""}
      <form method="POST">
        <input type="password" name="password" placeholder="Enter admin password" autofocus>
        <button type="submit">Login</button>
      </form>
    </div></body></html>
    '''

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

# ─── Main Routes ─────────────────────────────────────────────

@app.route('/')
def home():
    sample_questions = [f['question'] for f in faqs[:4]] if faqs else []
    faq_count = len(faqs)
    return render_template('index.html',
        sample_questions=sample_questions,
        faq_count=faq_count)

@app.route('/ask', methods=['POST'])
def ask():
    global faqs, embeddings

    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({'error': 'empty query'}), 400

    if not faqs or embeddings is None:
        return jsonify({
            'answer': 'No FAQ loaded yet. Please ask the admin to upload the FAQ file.',
            'confidence': 0,
            'not_found': True
        })

    q_emb = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(q_emb, embeddings)[0]
    idx = int(scores.argmax())
    confidence = round(float(scores[idx]), 2)
    matched_question = faqs[idx]['question']
    answer = faqs[idx]['answer']

    logs = get_logs()

    if confidence < 0.30:
        logs.append({
            'query': query,
            'answer': None,
            'confidence': confidence,
            'not_found': True,
            'timestamp': datetime.datetime.now().isoformat()
        })
        save_logs(logs)
        return jsonify({
            'answer': "I couldn't find a relevant answer. Please contact HR directly or rephrase your question.",
            'confidence': confidence,
            'matched_question': None,
            'not_found': True
        })

    warning = None
    if confidence < 0.50:
        warning = 'Low confidence match — please verify this answer with HR.'

    logs.append({
        'query': query,
        'answer': answer,
        'confidence': confidence,
        'not_found': False,
        'timestamp': datetime.datetime.now().isoformat()
    })
    save_logs(logs)

    return jsonify({
        'answer': answer,
        'confidence': confidence,
        'matched_question': matched_question,
        'warning': warning
    })

@app.route('/speak', methods=['POST'])
def speak():
    text = request.json.get('text', '').strip()
    if not text:
        return jsonify({'error': 'no text provided'}), 400
    try:
        filename = f'static/audio/{uuid.uuid4().hex}.mp3'
        gTTS(text=text, lang='en').save(filename)
        return send_file(filename, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── Upload ──────────────────────────────────────────────────

@app.route('/upload', methods=['POST'])
def upload_faq():
    global faqs, embeddings

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    text = ''
    fname = f.filename.lower()

    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + '\n'

        elif fname.endswith('.txt'):
            text = f.read().decode('utf-8')

        elif fname.endswith('.docx'):
            doc = Document(f)
            text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])

        elif fname.endswith('.csv'):
            df = pd.read_csv(f)
            df.columns = [c.lower().strip() for c in df.columns]
            if 'question' in df.columns and 'answer' in df.columns:
                for _, row in df.iterrows():
                    text += f"Q: {str(row['question']).strip()}\nA: {str(row['answer']).strip()}\n\n"
            else:
                return jsonify({'error': 'CSV must have columns named "question" and "answer"'}), 400
        else:
            return jsonify({'error': 'Supported: PDF, TXT, DOCX, CSV'}), 400

    except Exception as e:
        return jsonify({'error': f'File read failed: {str(e)}'}), 500

    if not text.strip():
        return jsonify({'error': 'File appears empty or unreadable'}), 400

    with open('faq.txt', 'w', encoding='utf-8') as out:
        out.write(text)

    faqs = load_faq('faq.txt')
    embeddings = build_embeddings(faqs)

    return jsonify({'message': f'FAQ updated. {len(faqs)} Q&As loaded.'})

# ─── FAQ Management (password protected) ─────────────────────

@app.route('/manage-faq')
@admin_required
def manage_faq():
    return render_template('manage_faq.html')

@app.route('/faq-list', methods=['GET'])
@admin_required
def faq_list():
    return jsonify(faqs)

@app.route('/faq-add', methods=['POST'])
@admin_required
def faq_add():
    global faqs, embeddings
    data = request.json
    q = data.get('question', '').strip()
    a = data.get('answer', '').strip()
    if not q or not a:
        return jsonify({'error': 'Question and answer required'}), 400
    faqs.append({'question': q, 'answer': a})
    save_faq(faqs)
    embeddings = build_embeddings(faqs)
    return jsonify({'message': 'FAQ added.', 'total': len(faqs)})

@app.route('/faq-edit', methods=['POST'])
@admin_required
def faq_edit():
    global faqs, embeddings
    data = request.json
    idx = data.get('index')
    q = data.get('question', '').strip()
    a = data.get('answer', '').strip()
    if idx is None or not q or not a:
        return jsonify({'error': 'Index, question and answer required'}), 400
    if idx < 0 or idx >= len(faqs):
        return jsonify({'error': 'Invalid index'}), 400
    faqs[idx] = {'question': q, 'answer': a}
    save_faq(faqs)
    embeddings = build_embeddings(faqs)
    return jsonify({'message': 'FAQ updated.'})

@app.route('/faq-delete', methods=['POST'])
@admin_required
def faq_delete():
    global faqs, embeddings
    idx = request.json.get('index')
    if idx is None or idx < 0 or idx >= len(faqs):
        return jsonify({'error': 'Invalid index'}), 400
    removed = faqs.pop(idx)
    save_faq(faqs)
    embeddings = build_embeddings(faqs)
    return jsonify({'message': f'Deleted: {removed["question"]}'})

# ─── Analytics ───────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin():
    logs = get_logs()
    total = len(logs)
    answered = [l for l in logs if not l.get('not_found')]
    failed = [l for l in logs if l.get('not_found')]
    avg_conf = round(sum(l['confidence'] for l in answered) / len(answered) * 100, 1) if answered else 0
    high_conf = sum(1 for l in answered if l['confidence'] >= 0.60)
    top_queries = Counter(l['query'] for l in logs).most_common(5)
    failed_queries = Counter(l['query'] for l in failed).most_common(5)
    recent = logs[-6:][::-1]
    return render_template('admin.html',
        total=total,
        answered=len(answered),
        failed=len(failed),
        avg_conf=avg_conf,
        high_conf=high_conf,
        top_queries=top_queries,
        failed_queries=failed_queries,
        recent=recent,
        faq_count=len(faqs))

@app.route('/export-logs')
@admin_required
def export_logs():
    logs = get_logs()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'query', 'answer', 'confidence', 'not_found'])
    writer.writeheader()
    for log in logs:
        writer.writerow({
            'timestamp': log.get('timestamp', ''),
            'query': log.get('query', ''),
            'answer': log.get('answer', '') or 'NOT FOUND',
            'confidence': log.get('confidence', ''),
            'not_found': log.get('not_found', False)
        })
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'peoplexm_logs_{datetime.date.today()}.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)