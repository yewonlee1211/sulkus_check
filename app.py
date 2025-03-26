from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import hashlib
import csv
import io

app = Flask(__name__)
app.secret_key = 'sulkus'  # 세션 관리를 위한 키

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 데이터베이스 초기화
with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    student_id TEXT,
                    is_other_univ TEXT,
                    registration_semester TEXT
                )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    password TEXT
                )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS semesters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year TEXT,
                    term TEXT,
                    label TEXT UNIQUE
                )''')
    default_password = hashlib.sha256("admin1234".encode()).hexdigest()
    cur.execute("SELECT * FROM admin")
    if not cur.fetchone():
        cur.execute("INSERT INTO admin (password) VALUES (?)", (default_password,))
    conn.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        student_id = request.form['student_id']
        is_other_univ = request.form['is_other_univ']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT registration_semester FROM students WHERE name=? AND student_id=? AND is_other_univ=?", 
                    (name, student_id, is_other_univ))
        student = cur.fetchone()
        conn.close()
        
        if student:
            return f"등록 학기: {student['registration_semester']}"
        else:
            return "등록된 정보가 없습니다."
    
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE password = ?", (hashed_password,))
        admin = cur.fetchone()
        conn.close()
        
        if admin:
            session['admin'] = True
            return redirect(url_for('manage'))
        else:
            return "비밀번호가 틀렸습니다."
    
    return render_template('admin.html')

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM semesters")
    semesters = cur.fetchall()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
    
    return render_template('manage.html', students=students, semesters=semesters)

@app.route('/add_student', methods=['POST']) # 전체 명부에서 학생 추가
def add_student():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    name = request.form['name']
    student_id = request.form['student_id']
    is_other_univ = request.form['is_other_univ']
    registration_semester = request.form['registration_semester']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO students (name, student_id, is_other_univ, registration_semester) VALUES (?, ?, ?, ?)",
                (name, student_id, is_other_univ, registration_semester))
    conn.commit()
    conn.close()

    return redirect(url_for('manage'))

@app.route('/add_semester', methods=['POST']) # 학기 추가
def add_semester():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    year = request.form['year']
    term = request.form['term']
    label = f"{year}년 {term}학기"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO semesters (year, term, label) VALUES (?, ?, ?)", (year, term, label))
    conn.commit()
    conn.close()

    return redirect(url_for('manage'))

@app.route('/semester/<label>') # 학기별 확인
def view_semester(label):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE registration_semester = ?", (label,))
    students = cur.fetchall()
    conn.close()

    return render_template('semester.html', students=students, label=label)

@app.route('/add_student_to_semester/<label>', methods=['POST']) #학기별 추가
def add_student_to_semester(label):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    name = request.form['name']
    student_id = request.form['student_id']
    is_other_univ = request.form['is_other_univ']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO students (name, student_id, is_other_univ, registration_semester) VALUES (?, ?, ?, ?)",
                (name, student_id, is_other_univ, label))
    conn.commit()
    conn.close()

    return redirect(url_for('view_semester', label=label))

# 엑셀(csv) 파일 업로드를 통한 학기별 학생 일괄 추가
@app.route('/upload_csv/<label>', methods=['POST'])
def upload_csv(label):
    if 'file' not in request.files:
        return "파일이 업로드되지 않았습니다."
    file = request.files['file']
    if file.filename == '':
        return "선택된 파일이 없습니다."
    if not file.filename.endswith('.csv'):
        return "CSV 파일만 업로드 가능합니다."

    # CSV 파싱 후 삽입
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)

    conn = get_db_connection()
    cur = conn.cursor()
    for row in csv_input:
        if len(row) >= 3:
            name, student_id, is_other_univ = row[0], row[1], row[2]
            cur.execute("INSERT INTO students (name, student_id, is_other_univ, registration_semester) VALUES (?, ?, ?, ?)",
                        (name.strip(), student_id.strip(), is_other_univ.strip(), label))
    conn.commit()
    conn.close()

    return redirect(url_for('view_semester', label=label))

@app.route('/delete/<int:id>') # 
def delete_student(id):
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage'))

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)