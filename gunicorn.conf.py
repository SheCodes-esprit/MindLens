import multiprocessing

# Configuration optimisée pour applications lourdes
bind = "0.0.0.0:10000"
workers = 1
worker_class = "sync"  # Utilise sync au lieu d'uvicorn
timeout = 300
keepalive = 5
preload_app = True
max_requests = 100
max_requests_jitter = 20