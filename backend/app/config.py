import os
from dotenv import load_dotenv

load_dotenv()
APP_ENV = os.getenv('APP_ENV', 'production')
SECRET_KEY = os.getenv('SECRET_KEY', '')
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
if len(SECRET_KEY) < 32:
    raise RuntimeError('SECRET_KEY must contain at least 32 random characters.')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL is required. Use persistent PostgreSQL in production.')
if APP_ENV == 'production' and DATABASE_URL.startswith('sqlite'):
    raise RuntimeError('Production requires persistent PostgreSQL, not ephemeral SQLite.')
EMAIL_TRANSPORT = os.getenv('EMAIL_TRANSPORT', 'smtp')
OTP_SECONDS = 600
TOKEN_HOURS = 12
