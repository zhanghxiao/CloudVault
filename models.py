import pymysql
from config import Config

class Database:
    def __init__(self):
        self.conn = pymysql.connect(
            host=Config.MYSQL_CONFIG['host'],
            port=Config.MYSQL_CONFIG['port'],
            user=Config.MYSQL_CONFIG['user'],
            password=Config.MYSQL_CONFIG['password'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        self.init_db()
    
    def init_db(self):
        with self.conn.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_CONFIG['database']}")
            cursor.execute(f"USE {Config.MYSQL_CONFIG['database']}")
            
            # 创建文件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    original_name VARCHAR(255) NOT NULL,
                    stored_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_type VARCHAR(50),
                    file_size BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY idx_path (file_path)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
        self.conn.commit()
    
    def search_files(self, keyword):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM files 
                WHERE original_name LIKE %s 
                OR file_path LIKE %s 
                ORDER BY created_at DESC
            """, (f"%{keyword}%", f"%{keyword}%"))
            return cursor.fetchall()