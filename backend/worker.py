"""Simple RQ worker launcher. Run this when Redis is available.

Example:
  redis-cli ping
  python backend/worker.py
"""
try:
    from redis import Redis
    from rq import Worker, Queue, Connection
except ImportError:
    print('RQ/Redis packages not installed; worker not started.')
else:
    try:
        redis_conn = Redis()
        listen = ['default']
        with Connection(redis_conn):
            worker = Worker(list(map(Queue, listen)))
            worker.work()
    except Exception as e:  # pylint: disable=broad-exception-caught
        print('Failed to start RQ worker:', e)
        print('Ensure Redis is running and rq/redis packages are installed.')
