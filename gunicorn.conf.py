import multiprocessing

# Réduire le nombre de workers pour économiser la mémoire
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:10000"
timeout = 120