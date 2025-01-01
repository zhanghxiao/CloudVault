from flask import (
    Flask, 
    render_template, 
    request, 
    jsonify, 
    redirect, 
    url_for,
    send_file
)
from io import BytesIO
import urllib.parse
from functools import wraps
import requests
import hashlib
import os
from config import Config
from models import Database
from utils import get_file_type, format_file_size
from huggingface_hub import HfApi

# 初始化 HuggingFace API
api = HfApi(token=Config.HF_TOKEN)
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
db = Database()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not Config.REQUIRE_LOGIN:
            return f(*args, **kwargs)
        if not request.cookies.get('authenticated'):
            if request.is_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == Config.ACCESS_PASSWORD:
            response = jsonify({'success': True})
            response.set_cookie('authenticated', 'true', secure=True, httponly=True)
            return response
        return jsonify({'error': 'Invalid password'}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    response = redirect(url_for('login'))
    response.delete_cookie('authenticated')
    return response

@app.route('/')
@require_auth
def index():
    return render_template('index.html')

@app.route('/api/files/list/')
@app.route('/api/files/list/<path:directory>')
@require_auth
def list_files(directory=''):
    try:
        url = f"https://huggingface.co/api/datasets/{Config.HF_DATASET_ID}/tree/{Config.HF_BRANCH}"
        if directory:
            url = f"{url}/{directory}"
            
        response = requests.get(
            url, 
            headers={'Authorization': f'Bearer {Config.HF_TOKEN}'}
        )
        if not response.ok:
            return jsonify({'error': 'Failed to fetch files', 'details': response.text}), response.status_code
        
        files = response.json()
        for file in files:
            if file['type'] == 'file':
                file['file_type'] = get_file_type(file['path'])
                file['size_formatted'] = format_file_size(file['size'])
                # 添加预览和下载URL
                file['preview_url'] = f"/api/files/preview/{file['path']}"
                file['download_url'] = f"/api/files/download/{file['path']}"
                
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/preview/<path:filepath>')
@require_auth
def preview_file(filepath):
    try:
        file_type = get_file_type(filepath)
        if file_type not in ['image', 'video', 'document']:
            return jsonify({'error': 'File type not supported for preview'}), 400
            
        url = f"https://{Config.PROXY_DOMAIN}/datasets/{Config.HF_DATASET_ID}/resolve/{Config.HF_BRANCH}/{filepath}"
        response = requests.get(
            url,
            headers={'Authorization': f'Bearer {Config.HF_TOKEN}'},
            stream=True
        )
        
        if response.ok:
            # 创建文件的内存缓存
            file_data = BytesIO(response.content)
            
            # 根据文件类型返回适当的响应
            return send_file(
                file_data,
                mimetype=response.headers.get('content-type', 'application/octet-stream'),
                conditional=True  # 启用条件请求支持
            )
        
        return jsonify({'error': 'Failed to fetch file'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/files/download/<path:filepath>')
@require_auth
def download_file(filepath):
    try:
        url = f"https://{Config.PROXY_DOMAIN}/datasets/{Config.HF_DATASET_ID}/resolve/{Config.HF_BRANCH}/{filepath}"
        response = requests.get(
            url, 
            headers={'Authorization': f'Bearer {Config.HF_TOKEN}'},
            stream=True
        )
        
        if response.ok:
            # 创建内存文件对象
            file_obj = BytesIO(response.content)
            
            # 获取文件名并进行编码
            filename = os.path.basename(filepath)
            encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
            
            # 使用 send_file 返回文件
            return send_file(
                file_obj,
                download_name=filename,
                as_attachment=True,
                mimetype=response.headers.get('content-type', 'application/octet-stream')
            )
            
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/files/upload', methods=['POST'])
@require_auth
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    current_path = request.form.get('path', '').strip('/')
    
    try:
        file_content = file.read()
        file.seek(0)
        
        original_name = file.filename
        stored_name = original_name
        full_path = os.path.join(current_path, stored_name).replace("\\", "/")
        
        response = api.upload_file(
            path_or_fileobj=file_content,
            path_in_repo=full_path,
            repo_id=Config.HF_DATASET_ID,
            repo_type="dataset",
            token=Config.HF_TOKEN
        )
        
        if response:
            with db.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO files (
                        original_name, stored_name, file_path, 
                        file_type, file_size
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    original_name,
                    stored_name,
                    full_path,
                    get_file_type(original_name),
                    len(file_content)
                ))
                db.conn.commit()
            
            return jsonify({'success': True})
        
        return jsonify({'error': 'Upload failed'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
   
@app.route('/api/files/search')
@require_auth
def search_files():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    try:
        files = db.search_files(keyword)
        return jsonify([{
            'name': f['original_name'],
            'path': f['file_path'],
            'type': get_file_type(f['file_path']),
            'size': format_file_size(f['file_size']),
            'created_at': f['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        } for f in files])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/delete/<path:filepath>', methods=['DELETE'])
@require_auth
def delete_file(filepath):
    try:
        # Initialize HuggingFace API
        api = HfApi(token=Config.HF_TOKEN)
        
        # Delete file from HuggingFace Hub
        api.delete_file(
            path_in_repo=filepath,
            repo_id=Config.HF_DATASET_ID,
            repo_type="dataset"
        )
        
        # Delete file record from database
        with db.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM files WHERE file_path = %s",
                [filepath]
            )
            db.conn.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)