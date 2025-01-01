import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # HuggingFace配置
    HF_DATASET_ID = os.getenv('HF_DATASET_ID')
    HF_TOKEN = os.getenv('HF_TOKEN')
    HF_BRANCH = os.getenv('HF_BRANCH', 'main')
    PROXY_DOMAIN = os.getenv('PROXY_DOMAIN', 'huggingface.co')
    
    # 系统配置
    REQUIRE_LOGIN = os.getenv('REQUIRE_LOGIN', 'true').lower() == 'true'
    ACCESS_PASSWORD = os.getenv('ACCESS_PASSWORD')
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # MySQL配置
    MYSQL_CONFIG = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE')
    }