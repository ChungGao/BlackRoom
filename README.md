# BlackRoom Chat - 实时匿名聊天室

基于 Flask-SocketIO 的在线匿名实时聊天室

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#安装部署">安装部署</a> •
  <a href="#配置说明">配置说明</a> •
  <a href="#api文档">API文档</a> •
  <a href="#英文版">English Version</a>
</p>

---

## 📋 功能特性

- **实时通信**: 基于 WebSocket 的即时消息传递，使用 Flask-SocketIO 构建
- **匿名聊天室**: 无需注册，自由加入聊天室，使用自定义用户名
- **AI 助手集成**: 智能聊天机器人，支持 Ollama（DeepSeek、Qwen 等）或 OpenAI 兼容 API
- **富媒体支持**: 支持图片、视频、音频、文档等多种文件类型分享
- **链接预览**: 自动检测共享链接并生成预览
- **聊天记录持久化**: 消息自动保存，可按需查看历史记录
- **重复文件检测**: 通过 SHA256 哈希进行文件去重，节省存储空间
- **Web 管理面板**: 功能完善的管理员界面，支持房间管理、统计和配置
- **文件管理**: 支持文件上传、下载和管理，支持 Unicode 文件名
- **房间管理**: 查看、编辑和删除聊天室，实时追踪在线用户数

## 🚀 快速开始

### 前置要求

- Python 3.7+
- pip (Python 包管理器)

### 所需依赖

核心依赖列表见 `requirements.txt`

### 快速启动

```bash
# 克隆仓库
git clone https://github.com/ChungGao/BlackRoom.git
cd BlackRoom

# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

默认情况下，应用运行在 `http://localhost:5000`

## ⚙️ 配置说明

### AI 配置

支持两种 AI 提供方：

#### 1. Ollama（推荐用于本地/离线使用）
- 安装 [Ollama](https://ollama.ai)
- 拉取模型: `ollama pull deepseek-r1` 或 `ollama pull qwen2.5`
- 在管理面板中启用
- 兼容 DeepSeek-R1 推理模型

#### 2. 第三方 API（OpenAI 兼容）
- 在管理面板中设置 API 密钥
- 支持 SiliconFlow、DeepSeek API 等平台

### 管理面板

- **默认登录地址**: `./admin`
- **默认凭据**:
  - 用户名: `admin`
  - 密码: `congjing520`
- **首次登录后立即修改密码!**
- 管理功能:
  - 查看实时统计（在线用户数、房间数、消息数、文件使用、AI 使用情况）
  - 管理聊天室（查看、删除房间及其文件）
  - 配置网站标题和描述
  - 更新 AI 设置和默认 AI 昵称
  - 测试 AI 连接并预览可用模型
  - 管理上传的文件和删除孤立文件

### 所有配置文件

- `site_config.json` - 网站标题和描述
- `admin_credentials.json` - 哈希后的管理员密码（自动生成）
- `ollama_config.json` - Ollama 配置
- `third_party_ai_config.json` - OpenAI 兼容 API 设置
- `ai_provider.json` - 默认 AI 提供方（ollama 或 thirdparty）
- `room_history.json` - 聊天记录（消息、时间戳、关联文件）
- `file_hash_map.json` - SHA256 哈希到文件名的映射（用于去重）

### ⚠️ 安全注意事项

**在公开部署前修改以下内容：**

- `app.config['SECRET_KEY']` in `app.py` (第 16 行)
- 通过管理面板界面修改默认管理员密码
- 考虑添加 HTTPS/SSL
- 设置防火墙规则，在反向代理（nginx）后部署

## 🎯 使用方法

1. 在浏览器中打开 `http://localhost:5000`
2. 输入您想要的用户名和房间号
3. 启用 AI 助手（可选）
4. 开始聊天！

## 📡 API 文档

### 用户端点

- `GET /` - 主页（主要聊天界面）
- `POST /upload` - 文件上传
- `GET /download/<filename>` - 文件下载
- `SOCKET /` - WebSocket 实时消息

### 管理端点

- `GET /admin` - 管理面板
- `GET /admin/login` - 登录页面
- `GET /admin/logout` - 登出

#### 管理 API

- `GET /api/admin/rooms` - 获取聊天室列表
- `GET /api/admin/room/<room_id>` - 获取房间详细信息（历史、文件、在线用户）
- `DELETE /api/admin/room/<room_id>` - 删除房间及关联文件
- `GET /api/admin/stats` - 服务器统计（房间、消息、文件、AI 使用、运行时间）
- `GET /api/admin/config` - 查看当前网站配置
- `POST /api/admin/config` - 更新网站标题/描述
- `GET`/`POST /api/admin/ai-provider` - 获取/设置默认 AI 提供方
- `GET /api/admin/ollama-config` - 查看 Ollama 配置
- `POST /api/admin/ollama-config` - 更新 Ollama 配置
- `POST /api/admin/ollama-test` - 测试 Ollama 连接（返回可用模型）
- `GET /api/admin/thirdparty-config` - 查看第三方 AI 配置
- `POST /api/admin/thirdparty-config` - 更新第三方 AI 配置
- `POST /api/admin/thirdparty-test` - 测试第三方 API（返回可用模型）
- `POST /api/admin/change-password` - 更改管理员密码/用户名
- `GET /api/admin/files` - 列出所有上传文件并检测孤立文件
- `DELETE /api/admin/file/<filename>` - 删除文件并移除引用
- `POST /api/admin/cleanup-orphaned` - 清理所有未使用文件（一键清理）

## 🔌 WebSocket 事件

### 客户端到服务器

- `join` - 加入房间
  ```json
  {
    "username": "Alice",
    "room": "room1"
  }
  ```

- `leave` - 离开房间
  ```json
  {
    "username": "Alice",
    "room": "room1"
  }
  ```

- `send_message` - 发送消息
  ```json
  {
    "room": "room1",
    "username": "Alice",
    "message": "Hello!",
    "ai_enabled": false,
    "custom_ai_name": "AI小助手"
  }
  ```

- `get_room_history` - 请求房间历史（通过点击"历史记录"按钮触发）
  ```json
  {
    "room": "room1",
    "filter": "all" // 或 "image", "video", "file"
  }
  ```

### 服务器到客户端

- `message` - 收到消息
  ```json
  {
    "username": "Alice",
    "message": "Hello!",
    "type": "user",
    "link_preview": null,
    "timestamp": "2025-11-10 14:30:00",
    "message_id": "room1_Alice_1605003000000"
  }
  ```

- `room_info` - 房间状态更新
  ```json
  {
    "count": 3,
    "members": ["Alice", "Bob", "Charlie"],
    "members_detail": [
      {"username": "Alice", "join_time": "2025-11-10 14:30:00"},
      ...
    ]
  }
  ```

- `room_history_response` - 历史记录响应
  ```json
  {
    "success": true,
    "messages": [],
    "filter": "all",
    "total": 0
  }
  ```

- `link_preview_update` - 消息发送后的异步链接预览
  ```json
  {
    "message_id": "room1_Alice_1605003000000",
    "link_preview": {
      "url": "...",
      "title": "...",
      "description": "...",
      "site_name": "..."
    }
  }
  ```

- `ai_response_start` - AI 流式响应开始
  ```json
  {
    "message_id": "...",
    "timestamp": "...",
    "ai_name": "AI助手",
    "supports_reasoning": true
  }
  ```

- `ai_response_chunk` - AI 响应片段
  ```json
  {
    "message_id": "...",
    "content": "Hello"
  }
  ```

- `ai_response_end` - AI 响应结束
  ```json
  { "message_id": "..." }
  ```

- `ai_reasoning_chunk` - 推理内容片段（针对 DeepSeek-R1 等推理模型）
  ```json
  {
    "message_id": "...",
    "content": "Let me think..."
  }
  ```

- `ai_reasoning_end` - 推理结束，传递完整推理内容
  ```json
  {
    "message_id": "...",
    "content": "..."
  }
  ```

- `ai_response_error` - AI 响应错误
  ```json
  {
    "message_id": "...",
    "error": "连接超时"
  }
  ```

- `room_disbanded` - 房间被管理员解散
  ```json
  {
    "message": "当前房间被管理员解散",
    "room": "room1"
  }
  ```

- `admin_data_update` - 实时管理员数据更新（由应用内操作触发）
  - `type`: 'stats', 'rooms', 'files', 'config'

## 💻 开发指南

### 项目结构

```
BlackRoom/
├── app.py                          # 主应用文件（Flask 后端）
├── requirements.txt                  # Python 依赖
├── site_config.json                  # 网站标题和描述
├── ai_provider.json                  # 默认 AI 提供方（ollama|thirdparty）
├── ollama_config.json               # Ollama 配置
├── third_party_ai_config.json       # OpenAI 兼容 API 配置
├── admin_credentials.json           # 管理员凭据（哈希密码）
├── room_history.json                # 聊天记录与文件引用
├── file_hash_map.json               # 去重映射
├── .gitignore                       # Git 忽略规则
├── templates/                       # HTML 模板
│   ├── index.html                  # 聊天界面（主页面）
│   ├── admin.html                  # 管理面板
│   └── admin_login.html           # 管理员登录表单
├── uploads/                         # 共享文件（运行时创建）
└── README.md                       # 此文件
```

### 添加新功能

1. 将后端逻辑添加到 `app.py`
2. 如有需要，更新 `templates/` 中的模板
3. 更新管理面板 (`admin.html`) 用于配置/管理功能

### 测试

```bash
# 使用 Flask 开发服务器运行
python app.py

# 或使用 WSGI 服务器进行生产部署（可选）
pip install eventlet  # 或 gevent
python app.py
```

## 🚀 部署

### 生产环境

推荐部署配置：
- 使用 `gunicorn` 或 `uwsgi` 代替 `flask run`
- 在 Nginx 反向代理后部署，支持 WebSocket：
  ```nginx
  location / {
      proxy_pass http://127.0.0.1:5000;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
  ```
- 启用 HTTPS 和 SSL 证书
- 配置防火墙（开放端口 5000 和 443）
- 推荐：使用 Supervisord/systemd 进行进程管理
- 以非 root 用户运行以确保安全

### 安全清单

- [ ] 在 `app.py` 中设置安全的 `SECRET_KEY`（第 16 行）
- [ ] 首次登录后修改管理员密码
- [ ] 在生产环境中禁用 `app.debug`
- [ ] 使用 HTTPS
- [ ] 配置 CORS 策略（如需要）
- [ ] 设置适当的文件上传限制
- [ ] 为管理端点实现速率限制
- [ ] 定期备份 JSON 文件（room_history.json、file_hash_map.json）

## ⚡ 性能优化

- 降低消息保存频率：每 10 条消息保存一次
- 自动文件去重以减少存储使用
- 自动清理超过 7 天不活跃的过期房间和孤立文件
- 优化历史记录检索：按需请求消息历史以减少初始加载
- 延迟加载链接预览以减少初始页面加载时间

## 🐛 已知问题与改进计划

### 当前已知问题

- 加载大量历史数据可能导致暂时的延迟
- 匿名用户身份可能被伪造（未验证）

### 未来功能

- 用户认证和授权
- 加密聊天室
- 消息搜索功能
- 导出聊天记录（JSON/Markdown）
- 文件过期策略
- 表情反应和提及功能
- 双向语音消息
- 消息加密和解密

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

## 📄 许可证

本项目是开源的，可在 [MIT 许可证](LICENSE) 下使用。

## 📊 更新日志

### v0.3
- 添加双 AI 提供方支持：Ollama 和 OpenAI 兼容 API
- DeepSeek-R1 推理模型支持，支持 `<think>` 解析
- 添加 AI 深度思考可视化
- 系统统计仪表板（房间、消息、文件、AI 使用、运行时间）
- 使用 SHA256 哈希的文件去重
- 文件与房间关联及生命周期管理（孤立文件清理）
- 一键清理所有未使用文件
- 重构管理 API
- 简化主聊天界面以专注于核心消息功能

## 📞 支持

如有问题和疑问：
- GitHub Issues: https://github.com/ChungGao/BlackRoom/issues
- 作者: ChungGao
- 邮箱: belison.gao@gmail.com

## 🙏 致谢

- 使用 Flask 和 Flask-SocketIO 构建
- AI 集成 via Ollama/Aleph Alpha
- 链接预览 powered by BeautifulSoup
- 文件图标和表情符号来自开源项目

---

<div id="english-version"></div>

# BlackRoom Chat

Real-time anonymous chat room powered by Flask-SocketIO.

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#api-documentation">API</a> •
  <a href="#中文版本">中文版本</a>
</p>

---

## Features

- **Real-time Communication**: WebSocket-based instant messaging using Flask-SocketIO
- **Anonymous Chat Rooms**: No registration required, join chat rooms freely with custom usernames
- **AI Assistant Integration**: Smart chatbot powered by Ollama (DeepSeek, Qwen, etc.) or OpenAI-compatible APIs
- **Rich Media Support**: Share images, videos, audio, documents, and more with file preview
- **Link Previews**: Automatic detection and preview generation for shared links
- **Persistent Chat History**: Messages automatically saved, accessible on-demand
- **Duplicate File Detection**: File deduplication through SHA256 hashing to save storage
- **Web-Based Admin Panel**: Comprehensive admin interface with room management, statistics, and configuration options
- **File Management**: Upload, download, and manage files with Unicode filename support
- **Room Management**: View, edit, and delete chat rooms with user count tracking

## Installation

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Required Libraries

Core dependencies listed in `requirements.txt`.

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ChungGao/BlackRoom.git
cd BlackRoom

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

By default, the app runs on `http://localhost:5000`.

## Configuration

### AI Configuration

Supports two AI providers:

#### 1. Ollama (Recommended for local/offline use)
- Install [Ollama](https://ollama.ai)
- Pull models: `ollama pull deepseek-r1` or `ollama pull qwen2.5`
- Enable in admin panel
- Compatible with DeepSeek-R1 reasoning models

#### 2. Third-Party API (OpenAI-compatible)
- Set API key in admin panel
- Supports platforms like SiliconFlow, DeepSeek API, etc.

### Admin Panel

- **Default login**: `./admin` endpoint
- **Default credentials**:
  - Username: `admin`
  - Password: `congjing520`
- **Change credentials immediately after first login!**
- Admin features:
  - View real-time statistics (online users, room count, message count, file usage, AI usage)
  - Manage chat rooms (view, delete rooms and their files)
  - Configure website title and description
  - Update AI settings and default AI nickname
  - Test AI connectivity and preview available models
  - Manage uploaded files and remove orphaned files

### All Configuration Files

- `site_config.json` - Website title and description
- `admin_credentials.json` - Hashed admin password (auto-generated)
- `ollama_config.json` - Ollama settings
- `third_party_ai_config.json` - OpenAI-like API settings
- `ai_provider.json` - Default AI provider (ollama or thirdparty)
- `room_history.json` - Chat history (messages, timestamps, linked files)
- `file_hash_map.json` - SHA256 hash-to-filename mappings for deduplication

### Security Considerations

**Change these before public deployment**:

- `app.config['SECRET_KEY']` in `app.py` (Line 16)
- Default admin password via admin panel UI
- Consider adding HTTPS/SSL
- Set up firewall rules and deploy under reverse proxy (nginx)

## Usage

1. Open `http://localhost:5000` in a browser
2. Enter your desired username and room number
3. Enable AI assistant (optional)
4. Start chatting!

## API Documentation

### User Endpoints

- `GET /` - Homepage (main chat interface)
- `POST /upload` - File upload
- `GET /download/<filename>` - File download
- `SOCKET /` - WebSocket for real-time messaging

### Admin Endpoints

- `GET /admin` - Admin panel
- `GET /admin/login` - Login page
- `GET /admin/logout` - Logout

#### Admin API

- `GET /api/admin/rooms` - Get chat room list
- `GET /api/admin/room/<room_id>` - Get room details (history, files, online users)
- `DELETE /api/admin/room/<room_id>` - Delete room and remove associated files
- `GET /api/admin/stats` - Server statistics (rooms, messages, files, AI usage, uptime)
- `GET /api/admin/config` - View current website config
- `POST /api/admin/config` - Update website title/description
- `GET`/`POST /api/admin/ai-provider` - Get/set default AI provider
- `GET /api/admin/ollama-config` - View Ollama config
- `POST /api/admin/ollama-config` - Update Ollama config
- `POST /api/admin/ollama-test` - Test Ollama connection (returns available models)
- `GET /api/admin/thirdparty-config` - View third-party AI config
- `POST /api/admin/thirdparty-config` - Update third-party AI config
- `POST /api/admin/thirdparty-test` - Test third-party API (returns available models)
- `POST /api/admin/change-password` - Change admin password/username
- `GET /api/admin/files` - List all uploaded files and orphan detection
- `DELETE /api/admin/file/<filename>` - Delete a file and remove references
- `POST /api/admin/cleanup-orphaned` - Remove all unused files (one-click cleanup)

## WebSocket Events

### Client to Server

- `join` - Join a room

- `leave` - Leave a room

- `send_message` - Send a message

- `get_room_history` - Request room history

### Server to Client

- `message` - Incoming message

- `room_info` - Room status update

- `room_history_response` - Reply to history request

- `link_preview_update` - Async link preview

- `ai_response_start` - AI stream start

- `ai_response_chunk` - AI response chunk

- `ai_response_end` - AI stream end

- `ai_reasoning_chunk` - Reasoning content chunk

- `ai_reasoning_end` - Reasoning end

- `ai_response_error` - AI response error

- `room_disbanded` - Room was deleted

- `admin_data_update` - Real-time admin data updates

## Development

### Project Structure

```
BlackRoom/
├── app.py                          # Main application file
├── requirements.txt                  # Python dependencies
├── site_config.json                  # Website title and description
├── ai_provider.json                  # Default AI provider
├── ollama_config.json               # Ollama configuration
├── third_party_ai_config.json       # OpenAI-like API configuration
├── admin_credentials.json           # Admin credentials
├── room_history.json                # Message history
├── file_hash_map.json               # Deduplication map
├── .gitignore                       # Git ignore rules
├── templates/                       # HTML templates
│   ├── index.html                  # Chat interface
│   ├── admin.html                  # Admin panel
│   └── admin_login.html           # Admin login form
├── uploads/                         # Shared files
└── README.md                       # This file
```

### Testing

```bash
python app.py
```

## Deployment

### Production Environment

- Use `gunicorn` or `uwsgi`
- Deploy behind Nginx reverse proxy with WebSocket support
- Enable HTTPS with SSL certificates
- Configure firewall
- Use Supervisord/systemd
- Run as non-root user

### Security Checklist

- [ ] Set a strong `SECRET_KEY`
- [ ] Change admin password
- [ ] Disable `app.debug`
- [ ] Use HTTPS
- [ ] Set appropriate file upload limits
- [ ] Implement rate limiting
- [ ] Backup JSON files regularly

## Performance Optimization

- Message batching (every 10 messages)
- File deduplication
- Automated cleanup of expired rooms (>7 days)
- On-demand history retrieval
- Lazy link preview loading

## Known Issues & Future Improvements

### Current Known Issues

- Loading large volumes of historical data may cause temporary lag
- Anonymous user identity may be spoofed

### Future Features

- User authentication
- Encrypted chat rooms
- Message search
- Export chat history
- File expiration policies
- Emoji reactions
- Voice messaging

## Contributing

Contributions welcome!

## License

MIT License

## Changelog

### v0.3
- Dual AI provider support (Ollama & OpenAI-compatible)
- DeepSeek-R1 reasoning model support
- AI deep-thinking visualization
- System statistics dashboard
- SHA256 file deduplication
- File lifecycle management
- One-click cleanup
- Refactored admin APIs
- Simplified main UI

## Support

- GitHub Issues: https://github.com/ChungGao/BlackRoom/issues
- Author: ChungGao
- Email: belison.gao@gmail.com

## Acknowledgments

- Flask and Flask-SocketIO
- Ollama
- BeautifulSoup
- Open-source icons and emojis
