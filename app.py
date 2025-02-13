from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import hashlib

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
                    student_id TEXT UNIQUE,
                    is_other_univ TEXT,
                    registration_semester TEXT
                )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    password TEXT
                )''')
    
    # 관리자 비밀번호 설정 (초기 한 번만 실행)
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
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
    
    return render_template('manage.html', students=students)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)