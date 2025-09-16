# source: https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py
from multiprocessing import cpu_count
from dotenv import load_dotenv
from os import environ

# load environment variables
load_dotenv()


# return max workers
def max_workers():
    return cpu_count() * 2 + 1


# Server socket
# bind = "0.0.0.0:8000"
bind = "0.0.0.0:" + environ.get("DJANGO_PORT", "8000")
backlog = 2048

# Worker processes
workers = max_workers()
worker_class = "sync"
worker_connections = 1000
# The timeout depends on the duration of team generation.
timeout = 300
graceful_timeout = 30
keepalive = 2  # 5

# SSL
# TODO: Needed in Docker environment with Nginx as reverse proxy?
# keyfile = '/var/www/ssl/server.key'
# certfile = '/var/www/ssl/server_with_ca.crt'
