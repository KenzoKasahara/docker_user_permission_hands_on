FROM python:3.14-slim

WORKDIR /app

# コンテナ内に一般ユーザーを作成する
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 \
               --gid appgroup \
               --create-home \
               --shell /usr/sbin/nologin \
               appuser

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/
RUN chown -R appuser:appgroup /app

# ここから先の実行ユーザーをappuserにする
USER appuser

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
