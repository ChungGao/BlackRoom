from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from datetime import datetime, timedelta
import json
import os
from threading import Lock
import time
from werkzeug.utils import secure_filename
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=5 * 1024 * 1024 * 1024)

# 创建上传文件夹
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 允许的文件扩展名（可以根据需要调整）
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', '7z', 'mp3', 'mp4', 'avi', 'mkv', 'mov'}

# 文件哈希映射表（hash -> unique_filename）
file_hash_map = {}  # {hash: unique_filename}
file_hash_lock = Lock()
HASH_MAP_FILE = 'file_hash_map.json'

# 加载文件哈希映射
def load_hash_map():
    global file_hash_map
    if os.path.exists(HASH_MAP_FILE):
        try:
            with open(HASH_MAP_FILE, 'r', encoding='utf-8') as f:
                file_hash_map = json.load(f)
            print(f"已加载 {len(file_hash_map)} 个文件哈希映射")
        except Exception as e:
            print(f"加载哈希映射失败: {e}")
            file_hash_map = {}

# 保存文件哈希映射
def save_hash_map():
    try:
        with open(HASH_MAP_FILE, 'w', encoding='utf-8') as f:
            json.dump(file_hash_map, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存哈希映射失败: {e}")

# 计算文件哈希值（使用SHA256）
def calculate_file_hash(file_stream):
    sha256_hash = hashlib.sha256()
    # 读取文件块计算哈希
    for byte_block in iter(lambda: file_stream.read(4096), b""):
        sha256_hash.update(byte_block)
    file_stream.seek(0)  # 重置文件指针
    return sha256_hash.hexdigest()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 网站配置
site_config = {
    'title': '实时聊天室',
    'description': '一个基于Flask-SocketIO的实时聊天应用'
}
config_lock = Lock()
CONFIG_FILE = 'site_config.json'

# 管理员账户配置
admin_credentials = {
    'username': 'admin',
    'password': hashlib.sha256('congjing520'.encode()).hexdigest()
}
ADMIN_FILE = 'admin_credentials.json'

# Ollama配置
ollama_config = {
    'enabled': False,
    'api_url': 'http://localhost:11434',
    'model': 'qwen2.5:latest',
    'temperature': 0.7,
    'max_tokens': 2000,
    'system_prompt': '你是一个友好的AI助手，在聊天室中帮助用户。请简洁、友好地回答问题。',
    'ai_name': 'AI助手'  # AI助手的默认昵称
}
ollama_config_lock = Lock()
OLLAMA_CONFIG_FILE = 'ollama_config.json'

# 加载Ollama配置
def load_ollama_config():
    global ollama_config
    if os.path.exists(OLLAMA_CONFIG_FILE):
        try:
            with open(OLLAMA_CONFIG_FILE, 'r', encoding='utf-8') as f:
                ollama_config = json.load(f)
            print(f"已加载Ollama配置")
        except Exception as e:
            print(f"加载Ollama配置失败: {e}")

# 保存Ollama配置
def save_ollama_config():
    try:
        # 先在锁外准备数据
        config_to_save = None
        with ollama_config_lock:
            config_to_save = ollama_config.copy()
        
        # 在锁外写入文件
        with open(OLLAMA_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, ensure_ascii=False, indent=2)
        print(f"已保存Ollama配置")
        return True
    except Exception as e:
        print(f"保存Ollama配置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# 第三方（OpenAI兼容）AI配置
third_party_ai_config = {
    'enabled': False,
    'api_base_url': 'https://api.openai.com',
    'api_key': '',
    'model': 'gpt-4o-mini',
    'temperature': 0.7,
    'max_tokens': 2000,
    'system_prompt': '你是一个友好的AI助手，在聊天室中帮助用户。',
    'ai_name': 'AI助手'
}
third_party_lock = Lock()
THIRD_PARTY_CONFIG_FILE = 'third_party_ai_config.json'

def load_third_party_config():
    global third_party_ai_config
    if os.path.exists(THIRD_PARTY_CONFIG_FILE):
        try:
            with open(THIRD_PARTY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                third_party_ai_config = json.load(f)
            print('已加载第三方AI配置')
        except Exception as e:
            print(f"加载第三方AI配置失败: {e}")

def save_third_party_config():
    try:
        with third_party_lock:
            cfg = third_party_ai_config.copy()
        with open(THIRD_PARTY_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print('已保存第三方AI配置')
        return True
    except Exception as e:
        print(f"保存第三方AI配置失败: {e}")
        return False

# 默认AI提供方配置（ollama 或 thirdparty）
ai_provider = 'ollama'
ai_provider_lock = Lock()
AI_PROVIDER_FILE = 'ai_provider.json'

def load_ai_provider():
    global ai_provider
    if os.path.exists(AI_PROVIDER_FILE):
        try:
            with open(AI_PROVIDER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                provider = data.get('provider')
                if provider in ('ollama', 'thirdparty'):
                    ai_provider = provider
            print(f"已加载AI提供方: {ai_provider}")
        except Exception as e:
            print(f"加载AI提供方失败: {e}")

def save_ai_provider():
    try:
        with ai_provider_lock:
            provider = ai_provider
        with open(AI_PROVIDER_FILE, 'w', encoding='utf-8') as f:
            json.dump({'provider': provider}, f, ensure_ascii=False, indent=2)
        print('已保存AI提供方设置')
        return True
    except Exception as e:
        print(f"保存AI提供方失败: {e}")
        return False

# 加载管理员凭据
def load_admin_credentials():
    global admin_credentials
    if os.path.exists(ADMIN_FILE):
        try:
            with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
                admin_credentials = json.load(f)
            print(f"已加载管理员凭据")
        except Exception as e:
            print(f"加载管理员凭据失败: {e}")

# 保存管理员凭据
def save_admin_credentials():
    try:
        with open(ADMIN_FILE, 'w', encoding='utf-8') as f:
            json.dump(admin_credentials, f, ensure_ascii=False, indent=2)
        print(f"已保存管理员凭据")
    except Exception as e:
        print(f"保存管理员凭据失败: {e}")

# 加载网站配置
def load_config():
    global site_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                site_config = json.load(f)
            print(f"已加载网站配置")
        except Exception as e:
            print(f"加载网站配置失败: {e}")

# 保存网站配置
def save_config():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(site_config, f, ensure_ascii=False, indent=2)
        print(f"已保存网站配置")
    except Exception as e:
        print(f"保存网站配置失败: {e}")

# 存储房间信息
rooms = {}
# 存储房间成员及其加入时间
room_members = {}  # {room_id: {username: join_timestamp}}
# 存储房间历史消息和最后活跃时间
room_history = {}  # {room_id: {'messages': [], 'last_active': datetime, 'users': set(), 'files': set()}}
history_lock = Lock()

# AI 请求统计（全局）
ai_stats_lock = Lock()
ai_request_total = 0
ai_request_success = 0

# 历史记录文件路径
HISTORY_FILE = 'room_history.json'

# 加载历史记录
def load_history():
    global room_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换日期字符串为datetime对象
                for room_id, room_data in data.items():
                    room_history[room_id] = {
                        'messages': room_data['messages'],
                        'last_active': datetime.fromisoformat(room_data['last_active']),
                        'users': set(),
                        'files': set(room_data.get('files', []))  # 兼容旧数据
                    }
                print(f"已加载 {len(room_history)} 个房间的历史记录")
        except Exception as e:
            print(f"加载历史记录失败: {e}")
            room_history = {}

# 保存历史记录
def save_history():
    try:
        # 不使用lock,因为调用者已经持有锁
        data = {}
        for room_id, room_data in room_history.items():
            data[room_id] = {
                'messages': room_data['messages'],
                'last_active': room_data['last_active'].isoformat(),
                'files': list(room_data.get('files', set()))  # 保存文件列表
            }
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(data)} 个房间的历史记录")
    except Exception as e:
        print(f"保存历史记录失败: {e}")
        import traceback
        traceback.print_exc()

# 清理过期的房间历史
def cleanup_expired_rooms():
    with history_lock:
        now = datetime.now()
        expired_rooms = []
        
        for room_id, room_data in room_history.items():
            # 如果房间当前没有用户,且距离最后活跃时间超过7天
            if len(room_data['users']) == 0:
                days_inactive = (now - room_data['last_active']).days
                if days_inactive > 7:
                    expired_rooms.append(room_id)
        
        # 清理过期房间及其关联文件
        for room_id in expired_rooms:
            # 获取房间关联的文件列表
            room_files = room_history[room_id].get('files', set())
            
            # 删除房间记录
            del room_history[room_id]
            print(f"已清理过期房间: {room_id}")
            
            # 检查并删除不再被任何房间引用的文件
            cleanup_orphaned_files(room_files)
        
        if expired_rooms:
            save_history()
        
        return len(expired_rooms)

# 清理孤立文件（不再被任何房间引用的文件）
def cleanup_orphaned_files(candidate_files):
    """清理不再被任何房间引用的文件"""
    # 收集所有仍在使用的文件
    files_in_use = set()
    for room_data in room_history.values():
        files_in_use.update(room_data.get('files', set()))
    
    # 删除不再被引用的文件
    with file_hash_lock:
        for unique_filename in candidate_files:
            if unique_filename not in files_in_use:
                # 文件不再被任何房间使用，删除实体文件
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        print(f"已删除孤立文件: {unique_filename}")
                    except Exception as e:
                        print(f"删除文件失败 {unique_filename}: {e}")
                
                # 从哈希映射中移除
                # 找到对应的哈希值并删除
                hash_to_remove = None
                for file_hash, filename in file_hash_map.items():
                    if filename == unique_filename:
                        hash_to_remove = file_hash
                        break
                
                if hash_to_remove:
                    del file_hash_map[hash_to_remove]
                    print(f"已从哈希映射中移除: {unique_filename}")
        
        # 保存更新后的哈希映射
        save_hash_map()

# 初始化:加载历史记录并清理过期房间
load_history()
cleanup_expired_rooms()
load_hash_map()  # 加载文件哈希映射
load_config()  # 加载网站配置
load_admin_credentials()  # 加载管理员凭据
load_ollama_config()  # 加载Ollama配置
load_third_party_config()  # 加载第三方AI配置
load_ai_provider()  # 加载默认AI提供方

# 记录服务器启动时间
server_start_time = datetime.now()

# 通知管理员数据更新
def notify_admin_update(update_type):
    """向所有连接的管理员发送数据更新通知
    update_type: 'stats', 'rooms', 'files', 'config'
    """
    try:
        socketio.emit('admin_data_update', {
            'type': update_type,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        print(f"通知管理员更新失败: {e}")

@app.route('/')
def index():
    return render_template('index.html', site_title=site_config.get('title', '实时聊天室'))

@app.route('/admin')
def admin():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin.html', site_title=site_config.get('title', '实时聊天室'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 验证密码
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username == admin_credentials['username'] and password_hash == admin_credentials['password']:
            session['admin_logged_in'] = True
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
    
    return render_template('admin_login.html', site_title=site_config.get('title', '实时聊天室'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# 管理API - 获取所有房间信息
@app.route('/api/admin/rooms', methods=['GET'])
def get_rooms():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with history_lock:
            rooms_data = []
            for room_id, room_data in room_history.items():
                # 计算房间统计信息
                total_messages = len(room_data['messages'])
                file_count = len(room_data.get('files', set()))
                
                # 统计文件总大小
                total_file_size = 0
                for filename in room_data.get('files', set()):
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(filepath):
                        total_file_size += os.path.getsize(filepath)
                
                rooms_data.append({
                    'room_id': room_id,
                    'message_count': total_messages,
                    'file_count': file_count,
                    'file_size': format_file_size(total_file_size),
                    'last_active': room_data['last_active'].strftime('%Y-%m-%d %H:%M:%S'),
                    'online_users': len(room_data['users']),
                    'users': list(room_data['users'])
                })
            
            return jsonify({
                'success': True,
                'rooms': rooms_data,
                'total_rooms': len(rooms_data)
            })
    except Exception as e:
        print(f"获取房间列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 获取房间详细信息
@app.route('/api/admin/room/<room_id>', methods=['GET'])
def get_room_detail(room_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with history_lock:
            if room_id not in room_history:
                return jsonify({'success': False, 'error': '房间不存在'}), 404
            
            room_data = room_history[room_id]
            return jsonify({
                'success': True,
                'room': {
                    'room_id': room_id,
                    'messages': room_data['messages'],
                    'files': list(room_data.get('files', set())),
                    'last_active': room_data['last_active'].strftime('%Y-%m-%d %H:%M:%S'),
                    'online_users': list(room_data['users'])
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 删除房间
@app.route('/api/admin/room/<room_id>', methods=['DELETE'])
def delete_room(room_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with history_lock:
            if room_id not in room_history:
                return jsonify({'success': False, 'error': '房间不存在'}), 404
            
            # 获取房间文件列表
            room_files = room_history[room_id].get('files', set())
            
            # 向房间内所有在线用户发送解散通知
            socketio.emit('room_disbanded', {
                'message': '当前房间被管理员解散',
                'room': room_id
            }, room=room_id)
            
            # 删除房间
            del room_history[room_id]
            save_history()
            
            # 清理孤立文件
            cleanup_orphaned_files(room_files)
            
            # 通知管理员数据已更新
            notify_admin_update('rooms')
            notify_admin_update('stats')
            
            print(f"管理员删除房间: {room_id}")
            
            return jsonify({'success': True, 'message': f'房间 {room_id} 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 获取网站配置
@app.route('/api/admin/config', methods=['GET'])
def get_config():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with config_lock:
            return jsonify({
                'success': True,
                'config': site_config
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 更新网站配置
@app.route('/api/admin/config', methods=['POST'])
def update_config():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        data = request.get_json()
        with config_lock:
            if 'title' in data:
                site_config['title'] = data['title']
            if 'description' in data:
                site_config['description'] = data['description']
            save_config()
        
        # 通知管理员配置已更新
        notify_admin_update('config')
        
        return jsonify({'success': True, 'message': '配置已更新', 'config': site_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 获取/设置默认AI提供方
@app.route('/api/admin/ai-provider', methods=['GET'])
def get_ai_provider():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with ai_provider_lock:
            provider = ai_provider
        return jsonify({'success': True, 'provider': provider})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/ai-provider', methods=['POST'])
def set_ai_provider():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        data = request.get_json()
        provider = (data or {}).get('provider')
        if provider not in ('ollama', 'thirdparty'):
            return jsonify({'success': False, 'error': '提供方必须为 ollama 或 thirdparty'}), 400
        with ai_provider_lock:
            global ai_provider
            ai_provider = provider
        if save_ai_provider():
            return jsonify({'success': True, 'message': 'AI提供方已更新', 'provider': ai_provider})
        else:
            return jsonify({'success': False, 'error': '保存失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 获取系统统计
@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with history_lock:
            # 统计总消息数
            total_messages = sum(len(room['messages']) for room in room_history.values())
            
            # 统计总文件数和大小
            all_files = set()
            for room_data in room_history.values():
                all_files.update(room_data.get('files', set()))
            
            total_file_size = 0
            for filename in all_files:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath):
                    total_file_size += os.path.getsize(filepath)
            
            # 统计在线用户数
            online_users = sum(len(room['users']) for room in room_history.values())
            
            # 计算服务器运行时长
            uptime = datetime.now() - server_start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            uptime_str = ''
            if days > 0:
                uptime_str += f'{days}天 '
            uptime_str += f'{hours}小时 {minutes}分钟 {seconds}秒'
            
            # 获取服务器配置信息（优雅降级，避免 psutil 缺失导致 500）
            import sys
            import platform
            import shutil
            try:
                import psutil  # 可选依赖
            except Exception:
                psutil = None

            # 获取内存信息
            if psutil:
                memory = psutil.virtual_memory()
                total_memory_gb = memory.total / (1024 ** 3)
            else:
                total_memory_gb = None
            
            # 获取磁盘信息（使用标准库，避免依赖 psutil）
            try:
                disk = shutil.disk_usage(os.getcwd())
                total_disk_gb = disk.total / (1024 ** 3)
            except Exception:
                total_disk_gb = None
            
            # 获取处理器信息
            if psutil:
                cpu_count = psutil.cpu_count(logical=False) or 0
                cpu_count_logical = psutil.cpu_count(logical=True) or (os.cpu_count() or 0)
            else:
                cpu_count = None
                cpu_count_logical = os.cpu_count() or 0
            cpu_info = f'{platform.processor()} ({cpu_count}核{cpu_count_logical}线程)' if cpu_count else platform.processor()
            
            # AI请求统计
            with ai_stats_lock:
                total_ai = ai_request_total
                success_ai = ai_request_success
            success_rate = 0.0
            if total_ai > 0:
                success_rate = (success_ai / total_ai) * 100.0
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_rooms': len(room_history),
                    'total_messages': total_messages,
                    'total_files': len(all_files),
                    'total_file_size': format_file_size(total_file_size),
                    'online_users': online_users,
                    'server_status': 'running',
                    'uptime': uptime_str,
                    'start_time': server_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'ai_requests_total': total_ai,
                    'ai_success_rate': f"{success_rate:.1f}%",
                    # 服务器配置信息
                    'server_config': {
                        'python_version': platform.python_version(),
                        'os': f'{platform.system()} {platform.release()}',
                        'processor': cpu_info,
                        'total_memory': f'{total_memory_gb:.1f} GB' if total_memory_gb is not None else '-',
                        'total_disk': f'{total_disk_gb:.1f} GB' if total_disk_gb is not None else '-',
                        'max_file_size': '5GB',
                        'upload_folder': app.config['UPLOAD_FOLDER']
                    }
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 更改管理员密码
@app.route('/api/admin/change-password', methods=['POST'])
def change_password():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    try:
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        new_username = data.get('new_username')
        
        # 验证旧密码
        old_password_hash = hashlib.sha256(old_password.encode()).hexdigest()
        if old_password_hash != admin_credentials['password']:
            return jsonify({'success': False, 'error': '原密码错误'}), 401
        
        # 更新凭据
        if new_username:
            admin_credentials['username'] = new_username
        if new_password:
            admin_credentials['password'] = hashlib.sha256(new_password.encode()).hexdigest()
        
        save_admin_credentials()
        
        return jsonify({'success': True, 'message': '账户信息已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 获取Ollama配置
@app.route('/api/admin/ollama-config', methods=['GET'])
def get_ollama_config():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with ollama_config_lock:
            return jsonify({
                'success': True,
                'config': ollama_config
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 更新Ollama配置
@app.route('/api/admin/ollama-config', methods=['POST'])
def update_ollama_config():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        data = request.get_json()
        with ollama_config_lock:
            if 'enabled' in data:
                ollama_config['enabled'] = bool(data['enabled'])
            if 'api_url' in data:
                ollama_config['api_url'] = data['api_url']
            if 'model' in data:
                ollama_config['model'] = data['model']
            if 'temperature' in data:
                ollama_config['temperature'] = float(data['temperature'])
            if 'max_tokens' in data:
                ollama_config['max_tokens'] = int(data['max_tokens'])
            if 'system_prompt' in data:
                ollama_config['system_prompt'] = data['system_prompt']
            if 'ai_name' in data:
                ollama_config['ai_name'] = data['ai_name'].strip() or 'AI助手'
        
        # 在锁外保存配置
        if save_ollama_config():
            return jsonify({'success': True, 'message': 'Ollama配置已更新', 'config': ollama_config})
        else:
            return jsonify({'success': False, 'error': '保存配置文件失败'}), 500
    except Exception as e:
        print(f"更新Ollama配置失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 测试Ollama连接
@app.route('/api/admin/ollama-test', methods=['POST'])
def test_ollama():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        data = request.get_json()
        # 如果请求体中有api_url，使用请求的URL，否则使用配置的URL
        if data and 'api_url' in data:
            api_url = data['api_url']
        else:
            with ollama_config_lock:
                api_url = ollama_config['api_url']
        
        # 尝试连接Ollama API，设置较短的超时时间
        test_response = requests.get(f"{api_url}/api/tags", timeout=3)
        if test_response.status_code == 200:
            models = test_response.json().get('models', [])
            model_names = [m['name'] for m in models]
            return jsonify({
                'success': True, 
                'message': 'Ollama连接成功',
                'models': model_names
            })
        else:
            return jsonify({'success': False, 'error': f'连接失败: HTTP {test_response.status_code}'}), 500
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': '连接超时，请检查Ollama服务地址是否正确，或Ollama是否运行'}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': '无法连接到Ollama服务，请检查地址和网络'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'连接失败: {str(e)}'}), 500

# 管理API - 获取第三方AI配置
@app.route('/api/admin/thirdparty-config', methods=['GET'])
def get_thirdparty_config():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with third_party_lock:
            return jsonify({'success': True, 'config': third_party_ai_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 更新第三方AI配置
@app.route('/api/admin/thirdparty-config', methods=['POST'])
def update_thirdparty_config():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        data = request.get_json() or {}
        with third_party_lock:
            if 'enabled' in data:
                third_party_ai_config['enabled'] = bool(data['enabled'])
            if 'api_base_url' in data:
                third_party_ai_config['api_base_url'] = data['api_base_url'].rstrip('/')
            if 'api_key' in data:
                third_party_ai_config['api_key'] = data['api_key']
            if 'model' in data:
                third_party_ai_config['model'] = data['model']
            if 'temperature' in data:
                third_party_ai_config['temperature'] = float(data['temperature'])
            if 'max_tokens' in data:
                third_party_ai_config['max_tokens'] = int(data['max_tokens'])
            if 'system_prompt' in data:
                third_party_ai_config['system_prompt'] = data['system_prompt']
            if 'ai_name' in data:
                third_party_ai_config['ai_name'] = data['ai_name'].strip() or 'AI助手'
        if save_third_party_config():
            return jsonify({'success': True, 'message': '第三方AI配置已更新', 'config': third_party_ai_config})
        else:
            return jsonify({'success': False, 'error': '保存配置文件失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 测试第三方AI连接（兼容OpenAI）
@app.route('/api/admin/thirdparty-test', methods=['POST'])
def test_thirdparty():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        data = request.get_json() or {}
        base_url = data.get('api_base_url') or third_party_ai_config.get('api_base_url')
        api_key = data.get('api_key') or third_party_ai_config.get('api_key')
        if not base_url or not api_key:
            return jsonify({'success': False, 'error': '请提供API地址与API Key'}), 400
        # 尝试列出模型
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        try:
            resp = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get('id') for m in data.get('data', [])]
                return jsonify({'success': True, 'message': '第三方API连接成功', 'models': models})
            else:
                return jsonify({'success': False, 'error': f'HTTP {resp.status_code}: {resp.text[:200]}'})
        except requests.exceptions.Timeout:
            return jsonify({'success': False, 'error': '连接超时，请检查第三方API地址或服务状态'}), 500
        except requests.exceptions.ConnectionError:
            return jsonify({'success': False, 'error': '无法连接到第三方API，请检查网络与地址'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 判断文件类型
def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}:
        return 'image'
    elif ext in {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'}:
        return 'video'
    elif ext in {'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'}:
        return 'audio'
    elif ext in {'pdf'}:
        return 'pdf'
    elif ext in {'txt', 'md', 'log'}:
        return 'text'
    elif ext in {'zip', 'rar', '7z', 'tar', 'gz'}:
        return 'archive'
    elif ext in {'doc', 'docx'}:
        return 'word'
    elif ext in {'xls', 'xlsx'}:
        return 'excel'
    elif ext in {'ppt', 'pptx'}:
        return 'powerpoint'
    else:
        return 'other'

# Socket.IO事件 - 获取房间历史消息
@socketio.on('get_room_history')
def handle_get_room_history(data):
    """用户主动请求房间历史消息"""
    room = data.get('room')
    filter_type = data.get('filter', 'all')  # all, video, image, file
    
    if not room:
        emit('room_history_response', {'success': False, 'error': '房间号不能为空'})
        return
    
    try:
        with history_lock:
            if room not in room_history:
                emit('room_history_response', {
                    'success': True,
                    'messages': [],
                    'filter': filter_type
                })
                return
            
            all_messages = room_history[room]['messages']
            
            # 根据过滤类型筛选消息
            filtered_messages = []
            if filter_type == 'all':
                filtered_messages = all_messages
            elif filter_type == 'video':
                # 包含视频文件的消息
                for msg in all_messages:
                    if msg.get('file_info') and msg['file_info'].get('file_type') == 'video':
                        filtered_messages.append(msg)
            elif filter_type == 'image':
                # 包含图片文件的消息
                for msg in all_messages:
                    if msg.get('file_info') and msg['file_info'].get('file_type') == 'image':
                        filtered_messages.append(msg)
            elif filter_type == 'file':
                # 包含任何文件的消息
                for msg in all_messages:
                    if msg.get('file_info'):
                        filtered_messages.append(msg)
            
            emit('room_history_response', {
                'success': True,
                'messages': filtered_messages,
                'filter': filter_type,
                'total': len(all_messages)
            })
    except Exception as e:
        print(f"获取房间历史失败: {e}")
        import traceback
        traceback.print_exc()
        emit('room_history_response', {'success': False, 'error': str(e)})

# 管理API - 获取所有文件列表
@app.route('/api/admin/files', methods=['GET'])
def get_files():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    try:
        files_list = []
        upload_folder = app.config['UPLOAD_FOLDER']
        
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                filepath = os.path.join(upload_folder, filename)
                if os.path.isfile(filepath):
                    file_stat = os.stat(filepath)
                    file_size = file_stat.st_size
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 检查文件被哪些房间引用
                    referenced_rooms = []
                    with history_lock:
                        for room_id, room_data in room_history.items():
                            if filename in room_data.get('files', set()):
                                referenced_rooms.append(room_id)
                    
                    # 检查是否在哈希映射中
                    is_hashed = False
                    with file_hash_lock:
                        for hash_value, hash_filename in file_hash_map.items():
                            if hash_filename == filename:
                                is_hashed = True
                                break
                    
                    # 获取文件类型
                    file_type = get_file_type(filename)
                    
                    files_list.append({
                        'filename': filename,
                        'size': format_file_size(file_size),
                        'size_bytes': file_size,
                        'modified_time': file_mtime,
                        'referenced_rooms': referenced_rooms,
                        'is_hashed': is_hashed,
                        'is_orphaned': len(referenced_rooms) == 0,
                        'file_type': file_type
                    })
        
        # 按修改时间排序
        files_list.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files_list,
            'total_files': len(files_list)
        })
    except Exception as e:
        print(f"获取文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 删除文件
@app.route('/api/admin/file/<filename>', methods=['DELETE'])
def delete_file(filename):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        # 从所有房间中移除该文件的引用
        with history_lock:
            for room_id, room_data in room_history.items():
                if filename in room_data.get('files', set()):
                    room_data['files'].discard(filename)
            save_history()
        
        # 从哈希映射中移除
        with file_hash_lock:
            hash_to_remove = None
            for file_hash, hash_filename in file_hash_map.items():
                if hash_filename == filename:
                    hash_to_remove = file_hash
                    break
            
            if hash_to_remove:
                del file_hash_map[hash_to_remove]
                save_hash_map()
        
        # 删除物理文件
        os.remove(filepath)
        print(f"已删除文件: {filename}")
        
        # 通知管理员文件已更新
        notify_admin_update('files')
        notify_admin_update('stats')
        
        return jsonify({'success': True, 'message': f'文件 {filename} 已删除'})
    except Exception as e:
        print(f"删除文件失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# 管理API - 批量清理孤立文件
@app.route('/api/admin/cleanup-orphaned', methods=['POST'])
def cleanup_orphaned_files_api():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    try:
        # 获取所有物理文件
        upload_folder = app.config['UPLOAD_FOLDER']
        all_files = set()
        if os.path.exists(upload_folder):
            all_files = set(os.listdir(upload_folder))
        
        # 获取所有被引用的文件
        referenced_files = set()
        with history_lock:
            for room_data in room_history.values():
                referenced_files.update(room_data.get('files', set()))
        
        # 找出孤立文件
        orphaned_files = all_files - referenced_files
        
        deleted_count = 0
        for filename in orphaned_files:
            filepath = os.path.join(upload_folder, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    print(f"清理孤立文件: {filename}")
                    
                    # 从哈希映射中移除
                    with file_hash_lock:
                        hash_to_remove = None
                        for file_hash, hash_filename in file_hash_map.items():
                            if hash_filename == filename:
                                hash_to_remove = file_hash
                                break
                        if hash_to_remove:
                            del file_hash_map[hash_to_remove]
                except Exception as e:
                    print(f"删除孤立文件失败 {filename}: {e}")
        
        with file_hash_lock:
            save_hash_map()
        
        # 通知管理员文件已更新
        notify_admin_update('files')
        notify_admin_update('stats')
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 个孤立文件',
            'deleted_count': deleted_count
        })
    except Exception as e:
        print(f"清理孤立文件失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    # 记录房间成员
    if room not in rooms:
        rooms[room] = set()
    rooms[room].add(username)
    
    # 记录房间成员加入时间
    if room not in room_members:
        room_members[room] = {}
    room_members[room][username] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 初始化房间历史记录
    with history_lock:
        if room not in room_history:
            room_history[room] = {
                'messages': [],
                'last_active': datetime.now(),
                'users': set(),
                'files': set()  # 初始化文件集合
            }
        
        room_history[room]['users'].add(username)
        room_history[room]['last_active'] = datetime.now()
        
        # 不再自动发送历史消息，改为用户点击历史记录按钮时获取
    
    # 发送系统消息
    join_message = {
        'username': '系统',
        'message': f'{username} 加入了房间',
        'type': 'system',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    emit('message', join_message, room=room)
    
    # 保存系统消息到历史
    try:
        with history_lock:
            room_history[room]['messages'].append(join_message)
    except Exception as e:
        print(f"保存加入消息失败: {e}")
    
    # 构建成员列表（包含加入时间）
    members_with_time = [{
        'username': member,
        'join_time': room_members[room].get(member, '')
    } for member in rooms[room]]
    
    # 发送当前房间人数和成员信息
    emit('room_info', {
        'count': len(rooms[room]),
        'members': list(rooms[room]),
        'members_detail': members_with_time
    }, room=room)
    
    # 通知管理员房间数据已更新
    notify_admin_update('rooms')
    notify_admin_update('stats')

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    
    # 移除房间成员
    if room in rooms and username in rooms[room]:
        rooms[room].remove(username)
        if len(rooms[room]) == 0:
            del rooms[room]
    
    # 移除成员加入时间记录
    if room in room_members and username in room_members[room]:
        del room_members[room][username]
        if len(room_members[room]) == 0:
            del room_members[room]
    
    # 更新房间历史记录
    try:
        with history_lock:
            if room in room_history:
                room_history[room]['users'].discard(username)
                # 如果房间没有用户了,更新最后活跃时间并保存
                if len(room_history[room]['users']) == 0:
                    room_history[room]['last_active'] = datetime.now()
                    save_history()
    except Exception as e:
        print(f"更新房间历史失败: {e}")
    
    # 发送系统消息
    leave_message = {
        'username': '系统',
        'message': f'{username} 离开了房间',
        'type': 'system',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    emit('message', leave_message, room=room)
    
    # 保存离开消息到历史
    try:
        with history_lock:
            if room in room_history:
                room_history[room]['messages'].append(leave_message)
    except Exception as e:
        print(f"保存离开消息失败: {e}")
    
    # 更新房间人数
    if room in rooms:
        # 构建成员列表（包含加入时间）
        members_with_time = [{
            'username': member,
            'join_time': room_members[room].get(member, '')
        } for member in rooms[room]]
        
        emit('room_info', {
            'count': len(rooms[room]),
            'members': list(rooms[room]),
            'members_detail': members_with_time
        }, room=room)
    
    # 通知管理员房间数据已更新
    notify_admin_update('rooms')
    notify_admin_update('stats')

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    username = data['username']
    raw_message = data['message']
    # 基础HTML/指令片段清洗
    try:
        def sanitize_user_message(text: str) -> str:
            if not isinstance(text, str):
                try:
                    text = str(text)
                except Exception:
                    return ''
            # 去除<script>和<style>块内容
            text = re.sub(r"<\s*script[^>]*>[\s\S]*?<\s*/\s*script\s*>", "", text, flags=re.IGNORECASE)
            text = re.sub(r"<\s*style[^>]*>[\s\S]*?<\s*/\s*style\s*>", "", text, flags=re.IGNORECASE)
            # 去除HTML注释
            text = re.sub(r"<!--[\s\S]*?-->", "", text)
            # 去除HTML标签但保留纯文本
            text = re.sub(r"<[^>]+>", "", text)
            # 去除围栏代码块中标注为html/script的内容（基础指令片段清洗）
            text = re.sub(r"```\s*(html|script)[\s\S]*?```", "", text, flags=re.IGNORECASE)
            # 归一化空白，限制长度
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 4000:
                text = text[:4000]
            return text
        message = sanitize_user_message(raw_message)
    except Exception:
        message = raw_message
    ai_enabled = data.get('ai_enabled', False)
    custom_ai_name = data.get('custom_ai_name', None)  # 获取自定义AI昵称
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 检测消息中是否包含链接
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message)
    
    # 构建消息对象(不带预览)
    message_obj = {
        'username': username,
        'message': message,
        'type': 'user',
        'link_preview': None,
        'timestamp': timestamp,
        'message_id': f"{room}_{username}_{int(time.time() * 1000)}"  # 唯一消息ID
    }
    
    # 立即发送消息
    emit('message', message_obj, room=room)
    
    # 保存消息到历史记录
    try:
        with history_lock:
            if room in room_history:
                room_history[room]['messages'].append(message_obj)
                room_history[room]['last_active'] = datetime.now()
                # 限制历史消息数量,最多保存1000条
                if len(room_history[room]['messages']) > 1000:
                    room_history[room]['messages'] = room_history[room]['messages'][-1000:]
                # 每10条消息保存一次,减少IO操作
                if len(room_history[room]['messages']) % 10 == 0:
                    save_history()
    except Exception as e:
        print(f"保存消息历史失败: {e}")
    
    # 如果有链接,异步获取预览
    if urls:
        # 使用 socketio 的后台任务机制
        socketio.start_background_task(fetch_and_send_preview, urls[0], message_obj['message_id'], room)
    
    # 如果启用了AI，调用Ollama
    if ai_enabled and ollama_config['enabled']:
        socketio.start_background_task(handle_ai_response, room, username, message, custom_ai_name)

def fetch_and_send_preview(url, message_id, room):
    """后台线程获取链接预览并发送更新"""
    try:
        link_preview = get_link_preview(url)
        if link_preview:
            # 发送链接预览更新
            socketio.emit('link_preview_update', {
                'message_id': message_id,
                'link_preview': link_preview
            }, room=room)
            
            # 更新历史记录中的预览信息
            try:
                with history_lock:
                    if room in room_history:
                        for msg in reversed(room_history[room]['messages']):
                            if msg.get('message_id') == message_id:
                                msg['link_preview'] = link_preview
                                break
            except Exception as e:
                print(f"更新历史记录预览失败: {e}")
    except Exception as e:
        print(f"获取链接预览失败: {e}")

def build_ai_context_messages(room, max_items=20):
    """构建最近聊天上下文（不包含文件），含昵称与时间。

    返回OpenAI/Ollama兼容的messages结构：[{role, content}...]
    content格式：『YYYY-MM-DD HH:MM:SS』『昵称』消息内容
    """
    context_messages = []
    try:
        with history_lock:
            if room in room_history:
                all_messages = room_history[room]['messages']
                # 过滤掉文件与系统类消息，仅保留用户与AI消息
                filtered = []
                for msg in reversed(all_messages):
                    t = msg.get('type')
                    if t == 'file':
                        continue
                    if t in ('user', 'ai'):
                        filtered.append(msg)
                # 取最近max_items条，并恢复为时间正序
                recent = list(reversed(filtered[:max_items]))
                for m in recent:
                    role = 'assistant' if m.get('type') == 'ai' else 'user'
                    name = m.get('username') or ''
                    text = m.get('message') or ''
                    # 仅保留用户昵称；AI上下文不包含昵称前缀
                    content = text if role == 'assistant' else f"【{name}】{text}"
                    context_messages.append({'role': role, 'content': content})
    except Exception as e:
        print(f"构建AI上下文失败: {e}")
    return context_messages

# AI响应处理
def handle_ai_response(room, username, user_message, custom_ai_name=None):
    """处理AI响应并流式发送到房间，支持 Ollama 与第三方(OpenAI兼容)"""
    global ai_request_total, ai_request_success
    message_id = f"{room}_AI_{int(time.time() * 1000)}"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # 统计一次AI请求开始
        with ai_stats_lock:
            ai_request_total += 1
        notify_admin_update('stats')
        # 读取当前默认提供方
        with ai_provider_lock:
            provider = ai_provider

        # 准备通用的系统提示与昵称
        if provider == 'thirdparty':
            with third_party_lock:
                base_url = third_party_ai_config['api_base_url']
                api_key = third_party_ai_config['api_key']
                model = third_party_ai_config['model']
                temperature = third_party_ai_config['temperature']
                max_tokens = third_party_ai_config['max_tokens']
                system_prompt = third_party_ai_config['system_prompt']
                default_ai_name = third_party_ai_config.get('ai_name', 'AI助手')
            ai_name = custom_ai_name if custom_ai_name else default_ai_name

            # 标记是否可能支持“深度思考”（例如 deepseek reasoner 等）
            supports_reasoning = any(s in (model or '').lower() for s in ['reason', 'deepseek', 'r1'])
            full_reasoning = ''

            # 开始事件
            socketio.emit('ai_response_start', {
                'message_id': message_id,
                'timestamp': timestamp,
                'ai_name': ai_name,
                'supports_reasoning': supports_reasoning
            }, room=room)
            socketio.sleep(0.1)

            # 构建OpenAI兼容请求（加入最近上下文，并优化提示词）
            augmented_system_prompt = (
                (system_prompt or '') +
                "\n\n注意：你将收到一段最近的对话上下文（最多20条）。其中：\n" +
                "- 用户消息采用格式：【昵称】消息文本\n" +
                "- AI消息为纯文本，不包含昵称前缀\n" +
                "请在理解上下文时正确区分不同用户的昵称，保持回答简洁友好。"
            )
            payload = {
                'model': model,
                'messages': (
                    [{'role': 'system', 'content': augmented_system_prompt}] +
                    build_ai_context_messages(room, max_items=20) +
                    [{'role': 'user', 'content': user_message}]
                ),
                'stream': True,
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            full_response = ''
            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=20
            )

            if response.status_code == 200:
                buffer = ''
                chunk_count = 0
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode('utf-8')
                    # OpenAI流式格式: 以"data: "开头
                    if line.startswith('data: '):
                        data_str = line[6:].strip()
                    else:
                        data_str = line.strip()
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        # 兼容delta流式内容
                        content = ''
                        if 'choices' in chunk_json and chunk_json['choices']:
                            choice = chunk_json['choices'][0]
                            if 'delta' in choice and 'content' in choice['delta']:
                                content = choice['delta']['content'] or ''
                            elif 'message' in choice and 'content' in choice['message']:
                                content = choice['message']['content'] or ''
                            # 采集可能存在的“深度思考”字段
                            if supports_reasoning:
                                # 常见兼容字段：reasoning_content / reasoning / thoughts
                                rc = ''
                                if 'delta' in choice:
                                    rc = choice['delta'].get('reasoning_content') or choice['delta'].get('reasoning') or choice['delta'].get('thoughts') or ''
                                elif 'message' in choice:
                                    rc = choice['message'].get('reasoning_content') or choice['message'].get('reasoning') or choice['message'].get('thoughts') or ''
                                if rc:
                                    full_reasoning += rc
                                    # 发送推理片段事件
                                    socketio.emit('ai_reasoning_chunk', {
                                        'message_id': message_id,
                                        'content': rc
                                    }, room=room)
                                    # 让事件及时刷新到客户端，避免被后续块吞并
                                    socketio.sleep(0.01)
                                else:
                                    # 若未提供显式推理字段，尝试从文本内容中提取<think>…</think>
                                    try:
                                        import re
                                        combined = full_response + (content or '')
                                        thinks = re.findall(r"<think>([\s\S]*?)</think>", combined)
                                        if thinks:
                                            joined = "\n\n".join(thinks)
                                            if len(joined) > len(full_reasoning):
                                                new_part = joined[len(full_reasoning):]
                                                if new_part.strip():
                                                    full_reasoning = joined
                                                    socketio.emit('ai_reasoning_chunk', {
                                                        'message_id': message_id,
                                                        'content': new_part
                                                    }, room=room)
                                                    # 让事件及时刷新到客户端
                                                    socketio.sleep(0.01)
                                    except Exception:
                                        pass
                        if content:
                            full_response += content
                            buffer += content
                            chunk_count += 1
                            if len(buffer) >= 5 or chunk_count >= 3:
                                socketio.emit('ai_response_chunk', {
                                    'message_id': message_id,
                                    'content': buffer
                                }, room=room)
                                buffer = ''
                                chunk_count = 0
                                socketio.sleep(0.01)
                    except json.JSONDecodeError:
                        continue

                if buffer:
                    socketio.emit('ai_response_chunk', {
                        'message_id': message_id,
                        'content': buffer
                    }, room=room)

                socketio.emit('ai_response_end', {'message_id': message_id}, room=room)

                # 结束时，如果有采集到推理内容，发送推理结束事件（用于一次性显示完整内容）
                if supports_reasoning and full_reasoning:
                    socketio.emit('ai_reasoning_end', {
                        'message_id': message_id,
                        'content': full_reasoning
                    }, room=room)

                ai_message_obj = {
                    'username': ai_name,
                    'message': full_response,
                    'type': 'ai',
                    'timestamp': timestamp,
                    'message_id': message_id
                }
                try:
                    with history_lock:
                        if room in room_history:
                            room_history[room]['messages'].append(ai_message_obj)
                            room_history[room]['last_active'] = datetime.now()
                            if len(room_history[room]['messages']) % 10 == 0:
                                save_history()
                except Exception as e:
                    print(f"保存AI消息历史失败: {e}")
                # 成功计数+1
                with ai_stats_lock:
                    ai_request_success += 1
                notify_admin_update('stats')
            else:
                socketio.emit('ai_response_error', {
                    'message_id': message_id,
                    'error': f'AI响应失败: HTTP {response.status_code}'
                }, room=room)
                notify_admin_update('stats')

        else:
            # 默认使用Ollama
            with ollama_config_lock:
                api_url = ollama_config['api_url']
                model = ollama_config['model']
                temperature = ollama_config['temperature']
                max_tokens = ollama_config['max_tokens']
                system_prompt = ollama_config['system_prompt']
                default_ai_name = ollama_config.get('ai_name', 'AI助手')
            ai_name = custom_ai_name if custom_ai_name else default_ai_name

            # 标记是否可能支持“深度思考”（例如 deepseek-r1 等会输出<think>内容）
            supports_reasoning = any(s in (model or '').lower() for s in ['reason', 'deepseek', 'r1'])
            full_reasoning = ''

            socketio.emit('ai_response_start', {
                'message_id': message_id,
                'timestamp': timestamp,
                'ai_name': ai_name,
                'supports_reasoning': supports_reasoning
            }, room=room)
            socketio.sleep(0.1)

            augmented_system_prompt = (
                (system_prompt or '') +
                "\n\n注意：你将收到一段最近的对话上下文（最多20条）。其中：\n" +
                "- 用户消息采用格式：【昵称】消息文本\n" +
                "- AI消息为纯文本，不包含昵称前缀\n" +
                "请在理解上下文时正确区分不同用户的昵称，保持回答简洁友好。"
            )
            payload = {
                'model': model,
                'messages': (
                    [{'role': 'system', 'content': augmented_system_prompt}] +
                    build_ai_context_messages(room, max_items=20) +
                    [{'role': 'user', 'content': user_message}]
                ),
                'stream': True,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            }

            full_response = ''
            response = requests.post(
                f"{api_url}/api/chat",
                json=payload,
                stream=True,
                timeout=15
            )

            if response.status_code == 200:
                buffer = ''
                chunk_count = 0
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line.decode('utf-8'))
                            if 'message' in chunk_data and 'content' in chunk_data['message']:
                                content = chunk_data['message']['content']
                                full_response += content
                                buffer += content
                                chunk_count += 1
                                # 若模型输出<think>...</think>，提取作为“深度思考”内容
                                if supports_reasoning and content:
                                    try:
                                        txt = str(content)
                                        # 提取所有<think>...</think>内容（可能跨chunk累积）
                                        # 简易策略：基于累计的full_response提取，再与已有的full_reasoning比较
                                        combined = full_response
                                        import re
                                        thinks = re.findall(r"<think>([\s\S]*?)</think>", combined)
                                        if thinks:
                                            joined = "\n\n".join(thinks)
                                            if len(joined) > len(full_reasoning):
                                                new_part = joined[len(full_reasoning):]
                                                if new_part.strip():
                                                    full_reasoning = joined
                                                    socketio.emit('ai_reasoning_chunk', {
                                                        'message_id': message_id,
                                                        'content': new_part
                                                    }, room=room)
                                                    # 及时将推理片段送达客户端
                                                    socketio.sleep(0.01)
                                    except Exception:
                                        pass
                                if len(buffer) >= 5 or chunk_count >= 3:
                                    socketio.emit('ai_response_chunk', {
                                        'message_id': message_id,
                                        'content': buffer
                                    }, room=room)
                                    buffer = ''
                                    chunk_count = 0
                                    socketio.sleep(0.01)
                        except json.JSONDecodeError:
                            continue
                if buffer:
                    socketio.emit('ai_response_chunk', {
                        'message_id': message_id,
                        'content': buffer
                    }, room=room)
                socketio.emit('ai_response_end', {'message_id': message_id}, room=room)

                # 结束时，如果有采集到推理内容，发送推理结束事件
                if supports_reasoning and full_reasoning:
                    socketio.emit('ai_reasoning_end', {
                        'message_id': message_id,
                        'content': full_reasoning
                    }, room=room)

                ai_message_obj = {
                    'username': ai_name,
                    'message': full_response,
                    'type': 'ai',
                    'timestamp': timestamp,
                    'message_id': message_id
                }
                try:
                    with history_lock:
                        if room in room_history:
                            room_history[room]['messages'].append(ai_message_obj)
                            room_history[room]['last_active'] = datetime.now()
                            if len(room_history[room]['messages']) % 10 == 0:
                                save_history()
                except Exception as e:
                    print(f"保存AI消息历史失败: {e}")
                # 成功计数+1
                with ai_stats_lock:
                    ai_request_success += 1
                notify_admin_update('stats')
            else:
                socketio.emit('ai_response_error', {
                    'message_id': message_id,
                    'error': f'AI响应失败: HTTP {response.status_code}'
                }, room=room)
                notify_admin_update('stats')

    except requests.exceptions.Timeout:
        socketio.emit('ai_response_error', {
            'message_id': message_id,
            'error': 'AI响应超时，请检查后台服务是否正常'
        }, room=room)
        notify_admin_update('stats')
    except requests.exceptions.ConnectionError:
        socketio.emit('ai_response_error', {
            'message_id': message_id,
            'error': '无法连接到AI服务，请检查配置'
        }, room=room)
        notify_admin_update('stats')
    except Exception as e:
        print(f"AI响应处理失败: {e}")
        import traceback
        traceback.print_exc()
        socketio.emit('ai_response_error', {
            'message_id': message_id,
            'error': f'AI响应失败: {str(e)}'
        }, room=room)
        notify_admin_update('stats')

def get_link_preview(url):
    """获取链接的标题和描述"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 设置较短的超时时间
        response = requests.get(url, headers=headers, timeout=3)
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取标题
        title = None
        
        # 优先获取 og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title.get('content')
        
        # 其次获取 twitter:title
        if not title:
            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            if twitter_title and twitter_title.get('content'):
                title = twitter_title.get('content')
        
        # 最后获取 title 标签
        if not title:
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = str(title_tag.string)
        
        # 获取描述
        description = None
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            description = og_desc.get('content')
        
        if not description:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content')
        
        # 获取网站名称
        site_name = None
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            site_name = og_site.get('content')
        
        if not site_name:
            site_name = urlparse(url).netloc
        
        if title:
            # 确保 title 和 description 是字符串类型
            title_str = str(title).strip() if title else None
            description_str = None
            if description:
                desc = str(description).strip()
                description_str = desc[:100] + '...' if len(desc) > 100 else desc
            
            return {
                'url': url,
                'title': title_str,
                'description': description_str,
                'site_name': str(site_name) if site_name else None
            }
    except Exception as e:
        print(f"获取链接预览失败 {url}: {e}")
    
    return None

# 文件上传路由
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        room = request.form.get('room')
        username = request.form.get('username')
        
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            
            # 计算文件哈希值
            file_hash = calculate_file_hash(file.stream)
            
            # 检查是否已存在相同哈希的文件
            unique_filename = None
            is_duplicate = False
            
            with file_hash_lock:
                if file_hash in file_hash_map:
                    # 检查文件是否真实存在
                    cached_filename = file_hash_map[file_hash]
                    cached_filepath = os.path.join(app.config['UPLOAD_FOLDER'], cached_filename)
                    
                    if os.path.exists(cached_filepath):
                        # 文件存在，使用已有文件
                        unique_filename = cached_filename
                        is_duplicate = True
                        print(f"检测到重复文件: {filename}, 使用已有文件: {unique_filename}")
                    else:
                        # 文件已被删除，需要重新上传
                        print(f"缓存文件已丢失: {cached_filename}, 重新上传: {filename}")
                        # 删除失效的哈希映射
                        del file_hash_map[file_hash]
                        save_hash_map()
                
                # 如果文件不存在或哈希映射中没有，保存新文件
                if not is_duplicate:
                    timestamp = int(time.time() * 1000)
                    unique_filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    # 保存文件
                    file.save(filepath)
                    
                    # 记录哈希映射
                    file_hash_map[file_hash] = unique_filename
                    save_hash_map()
                    print(f"上传新文件: {filename}, 保存为: {unique_filename}")
            
            # 获取文件大小和类型
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file_size = os.path.getsize(filepath)
            file_size_str = format_file_size(file_size)
            file_type = get_file_type(filename)  # 获取文件类型
            
            # 发送文件消息到房间
            file_message = {
                'username': username,
                'message': f'发送了文件: {filename}' + (' (已缓存)' if is_duplicate else ''),
                'type': 'file',
                'file_info': {
                    'filename': filename,
                    'original_filename': filename,  # 添加原始文件名
                    'unique_filename': unique_filename,
                    'size': file_size_str,
                    'download_url': f'/download/{unique_filename}',
                    'file_type': file_type,  # 添加文件类型
                    'is_cached': is_duplicate
                },
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message_id': f"{room}_{username}_{int(time.time() * 1000)}"
            }
            
            # 通过Socket.IO发送文件消息到房间的所有用户
            with app.app_context():
                socketio.emit('message', file_message, room=room, namespace='/')
            
            # 保存到历史记录
            try:
                with history_lock:
                    if room in room_history:
                        room_history[room]['messages'].append(file_message)
                        room_history[room]['last_active'] = datetime.now()
                        # 将文件关联到房间
                        if 'files' not in room_history[room]:
                            room_history[room]['files'] = set()
                        room_history[room]['files'].add(unique_filename)
                        print(f"文件 {unique_filename} 已关联到房间 {room}")
                        if len(room_history[room]['messages']) % 10 == 0:
                            save_history()
            except Exception as e:
                print(f"保存文件消息历史失败: {e}")
            
            # 通知管理员界面更新文件列表和统计数据
            notify_admin_update('files')
            notify_admin_update('stats')
            
            return jsonify({
                'success': True,
                'filename': filename,
                'size': file_size_str,
                'is_cached': is_duplicate
            })
    except Exception as e:
        print(f"文件上传失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# 文件下载路由
@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': '文件不存在'}), 404

# 格式化文件大小
def format_file_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
