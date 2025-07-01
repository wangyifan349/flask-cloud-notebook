from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify  # 引入必要的Flask模块
from flask_sqlalchemy import SQLAlchemy  # 引入SQLAlchemy用于ORM
from flask_wtf import FlaskForm  # 引入Flask-WTF表单
from wtforms import StringField, TextAreaField, PasswordField  # 引入表单字段
from wtforms.validators import InputRequired, Length  # 引入表单验证器
from werkzeug.security import generate_password_hash, check_password_hash  # 引入Werkzeug用于密码安全
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # 用于会话管理的Flask秘钥
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # 数据库URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭修改跟踪节省开销

db = SQLAlchemy(app)  # 绑定Flask应用和数据库对象

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 用户表主键
    username = db.Column(db.String(150), unique=True, nullable=False)  # 用户名字段
    password = db.Column(db.String(150), nullable=False)  # 密码字段
    notes = db.relationship('Note', backref='author', lazy=True)  # 关联笔记

# 笔记模型
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 笔记表主键
    title = db.Column(db.String(100), nullable=False)  # 标题字段
    content = db.Column(db.Text, nullable=False)  # 内容字段
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 外键关联用户

# 用户注册表单
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=150)])

# 登录表单
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])

# 笔记表单
class NoteForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired()])
    content = TextAreaField('Content', validators=[InputRequired()])

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:  # 检查用户是否登录
        form = NoteForm()  # 实例化笔记表单
        if form.validate_on_submit():  # 提交表单后验证
            new_note = Note(title=form.title.data, content=form.content.data, user_id=session['user_id'])
            db.session.add(new_note)  # 添加笔记到会话
            db.session.commit()  # 提交到数据库
            return redirect(url_for('index'))  # 重定向到首页
        user = User.query.filter_by(id=session['user_id']).first()  # 获取当前用户
        notes = user.notes  # 获取用户的所有笔记
        return render_template_string(HTML_INDEX, form=form, notes=notes)  # 渲染页面
    else:
        return redirect(url_for('login'))  # 未登录则重定向到登录

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()  # 实例化注册表单
    if form.validate_on_submit():  # 提交表单后验证
        hashed_password = generate_password_hash(form.password.data)  # 生成密码哈希
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)  # 添加用户到会话
        db.session.commit()  # 提交到数据库
        return redirect(url_for('login'))  # 重定向到登录
    return render_template_string(HTML_REGISTER, form=form)  # 渲染注册页面

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # 实例化登录表单
    if form.validate_on_submit():  # 提交表单后验证
        user = User.query.filter_by(username=form.username.data).first()  # 获取用户
        if user and check_password_hash(user.password, form.password.data):  # 验证密码
            session['user_id'] = user.id  # 记录用户登录状态
            return redirect(url_for('index'))  # 重定向到首页
    return render_template_string(HTML_LOGIN, form=form)  # 渲染登录页面

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # 移除会话中的用户ID
    return redirect(url_for('login'))  # 重定向到登录

@app.route('/edit/<int:note_id>', methods=['GET', 'POST'])
def edit(note_id):
    note = Note.query.get_or_404(note_id)  # 查找笔记或返回404
    if note.author.id != session.get('user_id'):  # 确认用户是所有者
        return redirect(url_for('index'))  # 不是所有者则重定向到首页
    form = NoteForm(obj=note)  # 使用现有笔记实例化表单
    if form.validate_on_submit():  # 验证表单提交
        note.title = form.title.data  # 更新标题
        note.content = form.content.data  # 更新内容
        db.session.commit()  # 更新数据库
        return redirect(url_for('index'))  # 重定向到首页
    return render_template_string(HTML_EDIT, form=form, note=note)  # 渲染编辑页面

@app.route('/delete/<int:note_id>')
def delete(note_id):
    note = Note.query.get_or_404(note_id)  # 查找笔记或返回404
    if note.author.id == session.get('user_id'):  # 确认用户是所有者
        db.session.delete(note)  # 删除笔记
        db.session.commit()  # 更新数据库
    return redirect(url_for('index'))  # 重定向到首页

@app.route('/search', methods=['GET'])
def search_notes():
    if 'user_id' not in session:  # 检查用户是否登录
        return redirect(url_for('login'))  # 否则重定向到登录
    query = request.args.get('query', '')  # 获取搜索查询
    user = User.query.filter_by(id=session['user_id']).first()  # 获取当前用户
    notes = Note.query.filter(Note.user_id == user.id).all()  # 用户的所有笔记
    results = [note for note in notes if lcs(note.title, query) > 0]  # 使用LCS过滤结果
    results.sort(key=lambda note: -lcs(note.title, query))  # 按LCS长度排序
    return render_template_string(HTML_SEARCH_RESULTS, notes=results, query=query)  # 渲染搜索结果页面

def lcs(X, Y):
    # 计算两个字符串X和Y的最长公共子序列长度
    m = len(X)
    n = len(Y)
    L = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0 or j == 0:
                L[i][j] = 0
            elif X[i - 1] == Y[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])
    return L[m][n]

HTML_INDEX = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flask Cloud Notebook</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
    <h1 class="mt-5">欢迎来到你的云端记事本</h1>
    <form method="POST" class="mt-3 mb-3">
        {{ form.hidden_tag() }}
        <div class="form-group">
            {{ form.title.label }}
            {{ form.title(class="form-control") }}
        </div>
        <div class="form-group">
            {{ form.content.label }}
            {{ form.content(class="form-control", rows=5) }}
        </div>
        <button type="submit" class="btn btn-primary">保存笔记</button>
    </form>
    <form method="GET" action="{{ url_for('search_notes') }}" class="form-inline my-2">
        <input name="query" class="form-control mr-sm-2" type="search" placeholder="搜索标题" aria-label="搜索">
        <button class="btn btn-outline-success my-2 my-sm-0" type="submit">搜索</button>
    </form>
    <hr>
    <h2>你的笔记</h2>
    <ul class="list-group">
        {% for note in notes %}
            <li class="list-group-item">
                <h5>{{ note.title }}</h5>
                <p>{{ note.content|safe }}</p>
                <a href="{{ url_for('edit', note_id=note.id) }}" class="btn btn-secondary">编辑</a>
                <a href="{{ url_for('delete', note_id=note.id) }}" class="btn btn-danger">删除</a>
            </li>
        {% else %}
            <li class="list-group-item">你还没有笔记。</li>
        {% endfor %}
    </ul>
    <a href="{{ url_for('logout') }}" class="btn btn-warning mt-3">登出</a>
</div>
</body>
</html>
"""

HTML_REGISTER = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 - Flask Cloud Notebook</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
    <h1 class="mt-5">注册</h1>
    <form method="POST">
        {{ form.hidden_tag() }}
        <div class="form-group">
            {{ form.username.label }}
            {{ form.username(class="form-control") }}
        </div>
        <div class="form-group">
            {{ form.password.label }}
            {{ form.password(class="form-control") }}
        </div>
        <button type="submit" class="btn btn-primary">注册</button>
    </form>
    <a href="{{ url_for('login') }}">已有账户？登录</a>
</div>
</body>
</html>
"""

HTML_LOGIN = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - Flask Cloud Notebook</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
    <h1 class="mt-5">登录</h1>
    <form method="POST">
        {{ form.hidden_tag() }}
        <div class="form-group">
            {{ form.username.label }}
            {{ form.username(class="form-control") }}
        </div>
        <div class="form-group">
            {{ form.password.label }}
            {{ form.password(class="form-control") }}
        </div>
        <button type="submit" class="btn btn-primary">登录</button>
    </form>
    <a href="{{ url_for('register') }}">没有账户？注册</a>
</div>
</body>
</html>
"""

HTML_EDIT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>编辑笔记 - Flask Cloud Notebook</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
    <h1 class="mt-5">编辑笔记</h1>
    <form method="POST">
        {{ form.hidden_tag() }}
        <div class="form-group">
            {{ form.title.label }}
            {{ form.title(class="form-control") }}
        </div>
        <div class="form-group">
            {{ form.content.label }}
            {{ form.content(class="form-control", rows=5) }}
        </div>
        <button type="submit" class="btn btn-primary">保存更改</button>
    </form>
</div>
</body>
</html>
"""

HTML_SEARCH_RESULTS = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>搜索结果 - Flask Cloud Notebook</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
    <h1 class="mt-5">搜索结果</h1>
    <p>搜索关键词: "{{ query }}"</p>
    <ul class="list-group">
        {% for note in notes %}
            <li class="list-group-item">
                <h5>{{ note.title }}</h5>
                <p>{{ note.content|safe }}</p>
                <a href="{{ url_for('edit', note_id=note.id) }}" class="btn btn-secondary">编辑</a>
                <a href="{{ url_for('delete', note_id=note.id) }}" class="btn btn-danger">删除</a>
            </li>
        {% else %}
            <li class="list-group-item">未找到相关笔记。</li>
        {% endfor %}
    </ul>
    <a href="{{ url_for('index') }}" class="btn btn-primary mt-3">返回首页</a>
</div>
</body>
</html>
"""

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # 初始化数据库结构
    app.run(debug=True)  # 启动应用并启用调试模式
