from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3
import hashlib
from markdown2 import markdown

# 初始化 Flask 应用
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 设置密钥以保护会话

# 数据库连接函数
def get_db_connection():
    """ 获取数据库连接 """
    conn = sqlite3.connect('notebook.db')  # 连接到 SQLite 数据库
    conn.row_factory = sqlite3.Row  # 设置游标返回字典格式
    return conn

# 数据库初始化函数
def init_db():
    """ 初始化数据库和表 """
    conn = get_db_connection()  # 获取数据库连接
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # 创建笔记表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            markdown_enabled INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()  # 提交事务
    conn.close()   # 关闭数据库连接

# 长公共子序列 (LCS) 实现
def longest_common_subsequence(s1, s2):
    """ 计算字符串 s1 和 s2 的最长公共子序列 """
    m, n = len(s1), len(s2)       # 获取两个字符串的长度
    dp = [[0] * (n + 1) for _ in range(m + 1)]  # 初始化 DP 表

    # 构建 LCS DP 表
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:  # 字符相等
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])  # 取最大

    # 回溯构建 LCS 字符串
    lcs = []
    while m > 0 and n > 0:
        if s1[m - 1] == s2[n - 1]:  # 找到公共字符
            lcs.append(s1[m - 1])
            m -= 1
            n -= 1
        elif dp[m - 1][n] > dp[m][n - 1]:
            m -= 1  # 移动到上方
        else:
            n -= 1  # 移动到左侧

    return ''.join(reversed(lcs))  # 返回反转后的 LCS 字符串

# 用户注册功能
@app.route('/register', methods=['GET', 'POST'])
def register():
    """ 处理用户注册 """
    if request.method == 'POST':
        username = request.form['username']  # 获取用户名
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()  # 加密密码
        
        conn = get_db_connection()  # 获取数据库连接
        cursor = conn.cursor()
        try:
            # 插入新用户
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()  # 提交事务
            flash('注册成功，请登录！')  # 显示成功信息
            return redirect(url_for('login'))  # 重定向到登录页面
        except sqlite3.IntegrityError:  # 捕获用户名已存在的错误
            flash('用户名已存在，请选择其他用户名。')
        finally:
            conn.close()  # 关闭数据库连接
    
    return render_template('register.html')  # 返回注册页面

# 用户登录功能
@app.route('/login', methods=['GET', 'POST'])
def login():
    """ 处理用户登录 """
    if request.method == 'POST':
        username = request.form['username']  # 获取用户名
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()  # 加密密码
        
        conn = get_db_connection()  # 获取数据库连接
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()  # 查找用户
        conn.close()  # 关闭数据库连接

        if user:
            session['user_id'] = user['id']  # 将用户 ID 存入会话
            return redirect(url_for('notes'))  # 登录成功后重定向到笔记列表
        else:
            flash('用户名或密码错误！')

    return render_template('login.html')  # 返回登录页面

# 用户登出功能
@app.route('/logout')
def logout():
    """ 用户登出 """
    session.pop('user_id', None)  # 移除会话中的用户 ID
    return redirect(url_for('login'))  # 重定向到登录页面

# 笔记列表功能
@app.route('/notes', methods=['GET', 'POST'])
def notes():
    """ 显示用户的笔记列表 """
    if 'user_id' not in session:  # 检查用户是否已登录
        return redirect(url_for('login'))

    conn = get_db_connection()  # 获取数据库连接
    
    if request.method == 'POST':  # 处理搜索请求
        search_query = request.form.get('search')  # 获取搜索查询
        notes = conn.execute('SELECT * FROM notes WHERE user_id = ?', (session['user_id'],)).fetchall()  # 获取所有笔记
        # 搜索匹配的笔记标题
        matched_notes = []
        for note in notes:
            if longest_common_subsequence(note['title'], search_query) != '':  # 使用 LCS 算法进行匹配
                matched_notes.append(note)  # 记录匹配的笔记

        conn.close()  # 关闭数据库连接
        return render_template('notes.html', notes=matched_notes)  # 返回匹配笔记列表

    notes = conn.execute('SELECT * FROM notes WHERE user_id = ?', (session['user_id'],)).fetchall()  # 获取所有笔记
    conn.close()  # 关闭数据库连接

    return render_template('notes.html', notes=notes)  # 返回笔记列表页面

# 创建笔记功能
@app.route('/notes/new', methods=['GET', 'POST'])
def new_note():
    """ 创建新笔记 """
    if 'user_id' not in session:  # 检查用户是否已登录
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']  # 获取笔记标题
        content = request.form['content']  # 获取笔记内容
        markdown_enabled = 1 if request.form.get('markdown_enabled') else 0  # 获取 Markdown 启用状态

        conn = get_db_connection()  # 获取数据库连接
        conn.execute('INSERT INTO notes (user_id, title, content, markdown_enabled) VALUES (?, ?, ?, ?)', (session['user_id'], title, content, markdown_enabled))
        conn.commit()  # 提交事务
        conn.close()  # 关闭数据库连接
        return redirect(url_for('notes'))  # 重定向到笔记列表

    return render_template('new_note.html')  # 返回新建笔记页面

# 编辑笔记功能
@app.route('/notes/edit/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    """ 编辑现有笔记 """
    if 'user_id' not in session:  # 检查用户是否已登录
        return redirect(url_for('login'))

    conn = get_db_connection()  # 获取数据库连接
    note = conn.execute('SELECT * FROM notes WHERE id = ? AND user_id = ?', (note_id, session['user_id'])).fetchone()  # 查找笔记
    
    if request.method == 'POST':
        title = request.form['title']  # 获取笔记标题
        content = request.form['content']  # 获取笔记内容
        markdown_enabled = 1 if request.form.get('markdown_enabled') else 0  # 获取 Markdown 启用状态
        conn.execute('UPDATE notes SET title = ?, content = ?, markdown_enabled = ? WHERE id = ?', (title, content, markdown_enabled, note_id))
        conn.commit()  # 提交事务
        conn.close()  # 关闭数据库连接
        return redirect(url_for('notes'))  # 重定向到笔记列表

    conn.close()  # 关闭数据库连接
    return render_template('edit_note.html', note=note)  # 返回编辑笔记页面

# 删除笔记功能
@app.route('/notes/delete/<int:note_id>')
def delete_note(note_id):
    """ 删除指定笔记 """
    if 'user_id' not in session:  # 检查用户是否已登录
        return redirect(url_for('login'))

    conn = get_db_connection()  # 获取数据库连接
    conn.execute('DELETE FROM notes WHERE id = ? AND user_id = ?', (note_id, session['user_id']))  # 删除笔记
    conn.commit()  # 提交事务
    conn.close()  # 关闭数据库连接
    return redirect(url_for('notes'))  # 重定向到笔记列表

# 获取笔记功能
@app.route('/notes/get/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """ 获取指定笔记的详情 """
    if 'user_id' not in session:  # 检查用户是否已登录
        return redirect(url_for('login'))

    conn = get_db_connection()  # 获取数据库连接
    note = conn.execute('SELECT title, content, markdown_enabled FROM notes WHERE id = ? AND user_id = ?', (note_id, session['user_id'])).fetchone()  # 查找笔记
    conn.close()  # 关闭数据库连接

    if note:
        return {
            'title': note['title'],
            'content': note['content'],
            'markdown_enabled': note['markdown_enabled']
        }
    return {}, 404  # 如果未找到笔记，返回 404

# 初始化数据库
init_db()

# 启动 Flask 应用
if __name__ == '__main__':
    app.run(debug=True)  # 在调试模式下运行应用
