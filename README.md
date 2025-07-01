# Flask Cloud Notebook ☁️📝

Flask Cloud Notebook 是一个简单的云端记事本应用，使用 Flask 框架构建，允许用户注册、登录、创建、编辑、删除和搜索笔记。它支持 Markdown 格式的笔记内容，旨在帮助用户高效管理个人笔记。

## 特性 ✨
- **用户注册和登录**：提供安全的身份验证机制。
- **笔记管理**：
  - **创建新笔记**：支持添加标题和内容，并支持 Markdown 格式。
  - **编辑笔记**：能够更新已有笔记的内容和标题。
  - **删除笔记**：轻松删除不再需要的笔记，保持笔记列表的整洁。
- **搜索功能**：使用最长公共子序列（LCS）算法快速搜索输入的笔记标题。
- **友好的用户界面**：基于 Bootstrap 提供响应式设计，确保良好的用户体验。

## 技术栈 🛠
- **Flask**：Python Web 应用框架。
- **SQLite**：轻量级关系型数据库，用于存储用户和笔记数据。
- **HTML/CSS/JavaScript**：用于前端开发。
- **Bootstrap**：前端 UI 框架，帮助美化应用界面。
- **Markdown2**：用于支持 Markdown 渲染的库。

## 安装步骤 📦

以下是安装和运行该应用的步骤：

1. **克隆项目**：
   ```bash
   git clone https://github.com/wangyifan349/flask-cloud-notebook.git
   cd flask-cloud-notebook
   ```

2. **创建虚拟环境**（可选，但推荐）：
   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Mac 或 Linux 上
   venv\Scripts\activate     # 在 Windows 上
   ```

3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

4. **初始化数据库**：
   在项目目录下运行：
   ```bash
   python app.py
   ```

5. **访问应用**：
   在浏览器中输入 `http://127.0.0.1:5000` 来访问应用。

## 使用说明 🖥

### 用户注册
1. 在首页点击“注册”按钮。
2. 输入用户名和密码，点击“注册”进行创建。

### 用户登录
1. 注册后返回首页，点击“登录”按钮。
2. 输入注册的用户名和密码，点击“登录”。

### 管理笔记
- **创建笔记**：登录后，点击“新建笔记”按钮。
- **编辑笔记**：在笔记列表中点击笔记标题进入编辑页面。
- **删除笔记**：在笔记列表中找到对应的笔记，点击“删除”按钮。

### 搜索笔记
在笔记列表页面，输入标题进行搜索，快速找到需要的笔记。

## 贡献 💡
欢迎提交问题或拉取请求以改进项目！如果你有好的想法或功能请求，请随时告诉我。贡献步骤：
1. Fork 这个仓库。
2. 创建自己的分支 (git checkout -b feature-xyz)。
3. 提交更改 (git commit -m "Add some feature")。
4. 推送到分支 (git push origin feature-xyz)。
5. 提交 Pull Request。

## 许可证 📄
该项目遵循 GNU 通用公共许可证第 3 版 (GPL-3.0)。您可以自由使用、修改和分发此项目，但需要遵循相应的许可证条款。要了解更多信息，请参阅 [LICENSE](LICENSE) 文件。

## 联系我 📫
如有任何问题或建议，请通过我的 GitHub 联系我: [wangyifan349](https://github.com/wangyifan349)。

感谢您访问这个项目！希望您能喜欢这个 Flask 云端记事本应用！😊
