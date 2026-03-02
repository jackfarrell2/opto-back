bind = "127.0.0.1:8000"
workers = 3
accesslog = "/app/logs/gunicorn.access.log"
errorlog = "/app/logs/gunicorn.app.log"
capture_output = True
loglevel = "info"
