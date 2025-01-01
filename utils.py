import os

def get_file_type(filename):
    """根据文件扩展名判断文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    
    # 文件类型映射
    type_map = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
        'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'],
        'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'],
        'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
        'code': ['.py', '.js', '.html', '.css', '.json', '.xml']
    }
    
    for file_type, extensions in type_map.items():
        if ext in extensions:
            return file_type
    return 'other'

def format_file_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"