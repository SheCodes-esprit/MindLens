# gunicorn.conf.py - CONFIGURATION ULTIME
bind = "0.0.0.0:10000"
workers = 1
worker_class = "sync"
timeout = 600  # Augmentez à 600 secondes
keepalive = 2
preload_app = True
max_requests = 10  # Redémarre très fréquemment
max_requests_jitter = 3
worker_tmp_dir = "/dev/shm"  # Utilise la mémoire partagée