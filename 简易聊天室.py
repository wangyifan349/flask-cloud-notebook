"""pip install Flask Flask-SocketIO eventlet"""
# app.py

import sqlite3
import uuid
from flask import Flask, g, request, redirect, url_for, abort, render_template_string
from flask_socketio import SocketIO, join_room, leave_room, emit

# 配置
DATABASE = 'chat.db'
SECRET_KEY = 'your-very-secret-key'  # 请改成自己更安全的字符串

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app)

# ---------- 数据库相关 ----------

def get_db():
    """获取或创建 SQLite 连接"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc):
    """请求结束时关闭数据库连接"""
    db = getattr(g, '_database', None)
    if db:
        db.close()

def init_db():
    """初始化表结构"""
    sql = """
    CREATE TABLE IF NOT EXISTS rooms (
      id TEXT PRIMARY KEY,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS joins (
      ip TEXT PRIMARY KEY,
      room_id TEXT,
      joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(room_id) REFERENCES rooms(id)
    );
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      room_id TEXT,
      ip TEXT,
      username TEXT,
      content TEXT,
      sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(room_id) REFERENCES rooms(id)
    );
    """
    db = get_db()
    db.executescript(sql)
    db.commit()

@app.before_first_request
def setup():
    init_db()

# ---------- 路由和视图 ----------

INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>聊天室首页</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <style>
    body { background: #f0f2f5; }
    .card { max-width: 400px; margin: 100px auto; }
  </style>
</head>
<body>
  <div class="card shadow-sm">
    <div class="card-header text-center bg-primary text-white">
      <h5>简易聊天室</h5>
    </div>
    <div class="card-body">
      <form action="{{ url_for('create_or_join_room') }}" method="POST">
        <div class="mb-3">
          <label class="form-label">昵称</label>
          <input type="text" class="form-control" name="username" required>
        </div>
        <div class="mb-3">
          <label class="form-label">房间 ID（选填，留空新建）</label>
          <input type="text" class="form-control" name="room_id">
        </div>
        <button type="submit" class="btn btn-primary w-100">进入房间</button>
      </form>
    </div>
  </div>
</body>
</html>
"""

ROOM_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>房间 {{ room_id }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/socket.io-client@4/dist/socket.io.min.js"></script>
  <style>
    body { background: #f0f2f5; }
    #chat-box {
      height: 60vh;
      overflow-y: auto;
      background: #fff;
      padding: 1rem;
      border: 1px solid #ddd;
      border-radius: .25rem;
    }
    #chat-box ul { list-style: none; padding: 0; margin: 0; }
    #chat-box li + li { margin-top: .5rem; }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid">
      <span class="navbar-brand">房间 {{ room_id }}</span>
      <div class="d-flex ms-auto">
        <span class="navbar-text me-3">你好，{{ username }}</span>
        <a href="{{ url_for('index') }}" class="btn btn-outline-light btn-sm">退出</a>
      </div>
    </div>
  </nav>

  <div class="container py-4">
    <div id="chat-box">
      <ul id="messages"></ul>
    </div>
    <div class="input-group mt-3">
      <input id="message_input"
             type="text"
             class="form-control"
             placeholder="输入消息后按回车发送...">
    </div>
  </div>

  <script>
    const socket = io();
    const room = "{{ room_id }}";
    const user = "{{ username }}";
    const messagesEl = document.getElementById('messages');
    const chatBox = document.getElementById('chat-box');

    function scrollBottom() {
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    socket.emit('join', { room, user });

    socket.on('status', data => {
      const li = document.createElement('li');
      li.className = 'text-muted fst-italic';
      li.textContent = data.msg;
      messagesEl.appendChild(li);
      scrollBottom();
    });

    socket.on('message', data => {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${data.user}:</strong> ${data.msg}`;
      messagesEl.appendChild(li);
      scrollBottom();
    });

    document.getElementById('message_input')
      .addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          const msg = e.target.value.trim();
          if (msg) {
            socket.emit('text', { room, user, msg });
            e.target.value = '';
          }
          e.preventDefault();
        }
      });

    window.addEventListener('beforeunload', () => {
      socket.emit('leave', { room, user });
    });
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/room', methods=['POST'])
def create_or_join_room():
    username = request.form.get('username', '').strip()
    room_id = request.form.get('room_id', '').strip()
    if not username:
        return abort(400, '请提供用户名')

    client_ip = request.remote_addr
    db = get_db()
    cur = db.cursor()

    # 检查 IP 是否已加入过
    cur.execute("SELECT 1 FROM joins WHERE ip = ?", (client_ip,))
    if cur.fetchone():
        return abort(403, '每个 IP 只能加入一次，您已加入过房间。')

    # 创建新房间或加入已有房间
    if not room_id:
        room_id = uuid.uuid4().hex[:8]
        cur.execute("INSERT INTO rooms(id) VALUES(?)", (room_id,))
    else:
        cur.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,))
        if not cur.fetchone():
            return abort(404, '房间不存在。')

    # 记录 join
    cur.execute("INSERT INTO joins(ip, room_id) VALUES(?, ?)", (client_ip, room_id))
    db.commit()

    return redirect(url_for('chat_room', room_id=room_id, username=username))

@app.route('/room/<room_id>')
def chat_room(room_id):
    username = request.args.get('username', '').strip()
    if not username:
        return redirect(url_for('index'))

    client_ip = request.remote_addr
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT 1 FROM joins WHERE ip = ? AND room_id = ?", (client_ip, room_id))
    if not cur.fetchone():
        return abort(403, '您无权访问此房间。')

    return render_template_string(ROOM_HTML,
                                  room_id=room_id,
                                  username=username)

# ---------- Socket.IO 事件 ----------

@socketio.on('join')
def on_join(data):
    room = data['room']
    user = data['user']
    join_room(room)
    emit('status', {'msg': f"{user} 加入了房间"}, room=room)

@socketio.on('text')
def on_text(data):
    room = data['room']
    user = data['user']
    msg  = data['msg']
    ip   = request.remote_addr

    # 存消息
    db = get_db()
    db.execute(
        "INSERT INTO messages(room_id, ip, username, content) VALUES(?,?,?,?)",
        (room, ip, user, msg)
    )
    db.commit()

    emit('message', {'user': user, 'msg': msg}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    user = data['user']
    leave_room(room)
    emit('status', {'msg': f"{user} 离开了房间"}, room=room)

# ---------- 启动 ----------

if __name__ == '__main__':
    # 安装依赖：Flask, Flask-SocketIO, eventlet
    # 运行： python app.py
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
