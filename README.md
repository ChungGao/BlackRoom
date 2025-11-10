# BlackRoom Chat

Real-time anonymous chat room powered by Flask-SocketIO.

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

## Screenshots

*Screenshots will be available soon*

## Tech Stack

- **Backend**: Python Flask with Flask-SocketIO for WebSocket support
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Database**: JSON file-based storage
- **AI Integration**:
  - Ollama (local, offline, reasoning models like DeepSeek-R1)
  - OpenAI-compatible API support (e.g., SiliconFlow API)
- **File Handling**: SHA256-based deduplication, 5GB max upload per file
- **Link Previews**: BeautifulSoup + requests for metadata scraping

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

## API Endpoints

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
  ```json
  {
    "username": "Alice",
    "room": "room1"
  }
  ```

- `leave` - Leave a room
  ```json
  {
    "username": "Alice",
    "room": "room1"
  }
  ```

- `send_message` - Send a message
  ```json
  {
    "room": "room1",
    "username": "Alice",
    "message": "Hello!",
    "ai_enabled": false,
    "custom_ai_name": "AI小助手"
  }
  ```

- `get_room_history` - Request room history (triggered by clicking the "History" button)
  ```json
  {
    "room": "room1",
    "filter": "all" // or "image", "video", "file"
  }
  ```

### Server to Client

- `message` - Incoming message
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

- `room_info` - Room status update
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

- `room_history_response` - Reply to history request
  ```json
  {
    "success": true,
    "messages": [],
    "filter": "all",
    "total": 0
  }
  ```

- `link_preview_update` - Async link preview after message sent
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

- `ai_response_start` - AI stream start
  ```json
  {
    "message_id": "...",
    "timestamp": "...",
    "ai_name": "AI助手",
    "supports_reasoning": true
  }
  ```

- `ai_response_chunk` - AI response chunk
  ```json
  {
    "message_id": "...",
    "content": "Hello"
  }
  ```

- `ai_response_end` - AI stream end
  ```json
  { "message_id": "..." }
  ```

- `ai_reasoning_chunk` - Reasoning content chunk (for deep-thinking models like DeepSeek-R1)
  ```json
  {
    "message_id": "...",
    "content": "Let me think..."
  }
  ```

- `ai_reasoning_end` - Reasoning end, pass complete reasoning content
  ```json
  {
    "message_id": "...",
    "content": "..."
  }
  ```

- `ai_response_error` - AI response error
  ```json
  {
    "message_id": "...",
    "error": "Connection timeout"
  }
  ```

- `room_disbanded` - Room was deleted by admin
  ```json
  {
    "message": "当前房间被管理员解散",
    "room": "room1"
  }
  ```

- `admin_data_update` - Real-time admin data updates (triggered by in-app actions)
  - `type`: 'stats', 'rooms', 'files', 'config'

## Development

### Project Structure

```
BlackRoom/
├── app.py                          # Main application file (Flask backend)
├── requirements.txt                  # Python dependencies
├── site_config.json                  # Website title and description
├── ai_provider.json                  # Default AI provider (ollama|thirdparty)
├── ollama_config.json               # Ollama configuration
├── third_party_ai_config.json       # OpenAI-like API configuration
├── admin_credentials.json           # Admin credentials (hashed password)
├── room_history.json                # Message history with file references
├── file_hash_map.json               # Deduplication map
├── .gitignore                       # Git ignore rules
├── templates/                       # HTML templates
│   ├── index.html                  # Chat interface (main page)
│   ├── admin.html                  # Admin panel
│   └── admin_login.html           # Admin login form
├── uploads/                         # Shared files (created at runtime)
└── README.md                       # This file
```

### Adding New Features

1. Add backend logic to `app.py`
2. Update templates in `templates/` if needed
3. Update admin panel (`admin.html`) for configuration/manage features

### Testing

```bash
# Run with Flask development server
python app.py

# Or run with WSGI server for production (optional)
pip install eventlet  # or gevent
python app.py
```

## Deployment

### Production Environment

Recommended deployment setup:
- Use `gunicorn` or `uwsgi` instead of `flask run`
- Deploy behind Nginx reverse proxy with WebSocket support:
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
- Enable HTTPS with SSL certificates
- Configure firewall (open ports 5000 and 443)
- Recommended: Supervisord/systemd for process management
- Run as non-root user for security

### Security Checklist

- [ ] Set a strong `SECRET_KEY` in `app.py` (Line 16)
- [ ] Change admin password after first login
- [ ] Disable `app.debug` in production
- [ ] Use HTTPS
- [ ] Configure CORS policies if needed
- [ ] Set appropriate file upload limits
- [ ] Implement rate limiting for admin endpoints
- [ ] Backup JSON files regularly (room_history.json, file_hash_map.json)

## Performance Optimization

- Reduced message save frequency: every 10 messages
- Automated file deduplication to reduce storage usage
- Weekly automated cleanup of expired rooms (>7 days inactive) and orphaned files
- Optimized history retrieval: request message history on-demand to reduce initial load
- Lazy link preview loading to minimize initial page load time

## Known Issues & Future Improvements

### Current Known Issues

- Loading large volumes of historical data may cause temporary lag
- Anonymous user identity may be spoofed (not verified)

### Future Features

- User authentication and authorization
- Encrypted chat rooms
- Message search functionality
- Export chat history (JSON/Markdown)
- File expiration policies
- Emoji reactions and mentions
- Bidirectional voice messaging
- Message encryption and decryption

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Changelog

### v0.3
- Added dual AI provider support: Ollama and OpenAI-compatible APIs
- DeepSeek-R1 reasoning model support with `<think>` parsing
- Added AI deep-thinking visualization
- System statistics dashboard (rooms, messages, files, AI usage, uptime)
- File deduplication using SHA256 hash
- File association with rooms and lifecycle management (orphan file cleanup)
- One-click cleanup for all unused files
- Refactored admin APIs
- Simplified main chat interface to focus on core messaging features

## Support

For issues and questions:
- GitHub Issues: https://github.com/ChungGao/BlackRoom/issues
- Author: ChungGao
- Email: belison.gao@gmail.com

## Acknowledgments

- Built with Flask and Flask-SocketIO
- AI integration via Ollama/Aleph Alpha
- Link previews powered by BeautifulSoup
- File icons and emojis from open-source projects
