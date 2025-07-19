import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
DATABASE = os.path.join(app.root_path, 'site.db')
# —— 数据库相关 —— #
def get_db():
    if 'db' not in g:
        connection = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db
@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS note (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT    NOT NULL,
            content  TEXT    NOT NULL,
            user_id  INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )
    ''')
    db.commit()
# —— LCS 算法 —— #
def lcs(a, b):
    m = len(a)
    n = len(b)
    dp = []
    for _ in range(m + 1):
        dp.append([0] * (n + 1))
    for i in range(m):
        for j in range(n):
            if a[i] == b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                if dp[i][j + 1] >= dp[i + 1][j]:
                    dp[i + 1][j + 1] = dp[i][j + 1]
                else:
                    dp[i + 1][j + 1] = dp[i + 1][j]
    return dp[m][n]
# —— 路由 —— #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if len(username) < 4 or len(password) < 4:
            flash('用户名和密码至少 4 个字符', 'danger')
        else:
            db = get_db()
            hashed_password = generate_password_hash(password)
            try:
                db.execute(
                    'INSERT INTO user (username, password) VALUES (?, ?)',
                    (username, hashed_password)
                )
                db.commit()
                flash('注册成功，请登录', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('用户名已存在', 'danger')

    return render_template_string(HTML_REGISTER)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db.execute(
            'SELECT * FROM user WHERE username = ?',
            (username,)
        ).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template_string(HTML_LOGIN)
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if not title or not content:
            flash('标题和内容都不能为空', 'warning')
        else:
            db.execute(
                'INSERT INTO note (title, content, user_id) VALUES (?, ?, ?)',
                (title, content, session['user_id'])
            )
            db.commit()
            return redirect(url_for('index'))
    notes_rows = db.execute(
        'SELECT * FROM note WHERE user_id = ? ORDER BY id DESC',
        (session['user_id'],)
    ).fetchall()
    notes = []
    for row in notes_rows:
        note = {
            'id': row['id'],
            'title': row['title'],
            'content': row['content']
        }
        notes.append(note)
    return render_template_string(HTML_INDEX, notes=notes)
@app.route('/edit/<int:note_id>', methods=['GET', 'POST'])
def edit(note_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    row = db.execute(
        'SELECT * FROM note WHERE id = ?',
        (note_id,)
    ).fetchone()
    if row is None or row['user_id'] != session['user_id']:
        return redirect(url_for('index'))
    note = {'id': row['id'], 'title': row['title'], 'content': row['content']}
    if request.method == 'POST':
        new_title = request.form.get('title', '').strip()
        new_content = request.form.get('content', '').strip()
        if not new_title or not new_content:
            flash('标题和内容都不能为空', 'warning')
        else:
            db.execute(
                'UPDATE note SET title = ?, content = ? WHERE id = ?',
                (new_title, new_content, note_id)
            )
            db.commit()
            return redirect(url_for('index'))
    return render_template_string(HTML_EDIT, note=note)
@app.route('/delete/<int:note_id>')
def delete(note_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    row = db.execute(
        'SELECT * FROM note WHERE id = ?',
        (note_id,)
    ).fetchone()
    if row and row['user_id'] == session['user_id']:
        db.execute('DELETE FROM note WHERE id = ?', (note_id,))
        db.commit()
    return redirect(url_for('index'))
@app.route('/search')
def search_notes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    query = request.args.get('query', '').strip()
    db = get_db()
    rows = db.execute(
        'SELECT * FROM note WHERE user_id = ?',
        (session['user_id'],)
    ).fetchall()
    filtered = []
    for row in rows:
        score = lcs(row['title'], query)
        if score > 0:
            filtered.append((row, score))
    # 根据 score 降序排序
    for i in range(len(filtered)):
        for j in range(i + 1, len(filtered)):
            if filtered[j][1] > filtered[i][1]:
                temp = filtered[i]
                filtered[i] = filtered[j]
                filtered[j] = temp
    results = []
    for item in filtered:
        r = item[0]
        note = {'id': r['id'], 'title': r['title'], 'content': r['content']}
        results.append(note)
    return render_template_string(HTML_SEARCH_RESULTS, notes=results, query=query)
# —— HTML 模板 —— #
HTML_REGISTER = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>注册</title>
  <link rel="stylesheet" 
        href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
  <h1 class="mt-5">注册</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="alert alert-{{cat}}">{{msg}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  <form method="POST">
    <div class="form-group">
      <label>用户名</label>
      <input name="username" class="form-control">
    </div>
    <div class="form-group">
      <label>密码</label>
      <input name="password" type="password" class="form-control">
    </div>
    <button class="btn btn-primary">注册</button>
  </form>
  <a href="{{url_for('login')}}">已有账户？登录</a>
</div>
</body>
</html>
"""

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>登录</title>
  <link rel="stylesheet" 
        href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
  <h1 class="mt-5">登录</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="alert alert-{{cat}}">{{msg}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  <form method="POST">
    <div class="form-group">
      <label>用户名</label>
      <input name="username" class="form-control">
    </div>
    <div class="form-group">
      <label>密码</label>
      <input name="password" type="password" class="form-control">
    </div>
    <button class="btn btn-primary">登录</button>
  </form>
  <a href="{{url_for('register')}}">没有账户？注册</a>
</div>
</body>
</html>
"""
HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>云端记事本</title>
  <link rel="stylesheet" 
        href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
  <h1 class="mt-5">云端记事本</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="alert alert-{{cat}}">{{msg}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  <form method="POST" class="mb-3">
    <div class="form-group">
      <label>标题</label>
      <input name="title" class="form-control">
    </div>
    <div class="form-group">
      <label>内容</label>
      <textarea name="content" rows="5" class="form-control"></textarea>
    </div>
    <button class="btn btn-primary">保存</button>
  </form>
  <form method="GET" action="{{url_for('search_notes')}}" class="form-inline mb-3">
    <input name="query" class="form-control mr-sm-2" placeholder="搜索标题">
    <button class="btn btn-outline-success">搜索</button>
  </form>
  <ul class="list-group">
    {% for note in notes %}
      <li class="list-group-item">
        <h5>{{note['title']}}</h5>
        <p>{{note['content']}}</p>
        <a href="{{url_for('edit', note_id=note['id'])}}" 
           class="btn btn-secondary btn-sm">编辑</a>
        <a href="{{url_for('delete', note_id=note['id'])}}" 
           class="btn btn-danger btn-sm">删除</a>
      </li>
    {% else %}
      <li class="list-group-item">暂无笔记</li>
    {% endfor %}
  </ul>
  <a href="{{url_for('logout')}}" class="btn btn-warning mt-3">登出</a>
</div>
</body>
</html>
"""
HTML_EDIT = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>编辑笔记</title>
  <link rel="stylesheet" 
        href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
  <h1 class="mt-5">编辑笔记</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="alert alert-{{cat}}">{{msg}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  <form method="POST">
    <div class="form-group">
      <label>标题</label>
      <input name="title" value="{{note['title']}}" class="form-control">
    </div>
    <div class="form-group">
      <label>内容</label>
      <textarea name="content" rows="5" class="form-control">{{note['content']}}</textarea>
    </div>
    <button class="btn btn-primary">保存</button>
  </form>
</div>
</body>
</html>
"""
HTML_SEARCH_RESULTS = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>搜索结果</title>
  <link rel="stylesheet" 
        href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
  <h1 class="mt-5">搜索 “{{query}}”</h1>
  <ul class="list-group">
    {% for note in notes %}
      <li class="list-group-item">
        <h5>{{note['title']}}</h5>
        <p>{{note['content']}}</p>
        <a href="{{url_for('edit', note_id=note['id'])}}" 
           class="btn btn-secondary btn-sm">编辑</a>
        <a href="{{url_for('delete', note_id=note['id'])}}" 
           class="btn btn-danger btn-sm">删除</a>
      </li>
    {% else %}
      <li class="list-group-item">未找到相关笔记</li>
    {% endfor %}
  </ul>
  <a href="{{url_for('index')}}" class="btn btn-primary mt-3">返回</a>
</div>
</body>
</html>
"""
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
