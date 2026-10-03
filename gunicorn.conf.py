import os

# Render dynamically sets $PORT (defaults to 5000 if not set)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Concurrency & timeout configurations for cloud deployment
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))

# Stream stdout/stderr for Render live logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
