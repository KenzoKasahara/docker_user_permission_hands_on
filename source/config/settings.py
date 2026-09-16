"""ハンズオン用の最小設定。接続情報はすべて環境変数から読む。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 秘密情報はイメージに含めず、docker-compose.yml 経由で .env から渡す
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ["DB_HOST"],
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

USE_TZ = True
TIME_ZONE = "Asia/Tokyo"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
