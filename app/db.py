"""
Pool de connexions pg8000 simple et robuste.
Ferme et recrée une connexion si elle est invalide.
"""
import queue
import threading
import pg8000.native

DB_CONFIG = {
    "host": "localhost",
    "port": 26257,
    "database": "globalshop",
    "user": "root",
    "password": None,
}

POOL_SIZE = 10

_pool = queue.Queue(maxsize=POOL_SIZE)
_lock = threading.Lock()
_initialized = False


def _create_connection():
    return pg8000.native.Connection(**DB_CONFIG)


def _init_pool():
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        for _ in range(POOL_SIZE):
            try:
                _pool.put(_create_connection(), block=False)
            except queue.Full:
                break
        _initialized = True


def get_connection():
    _init_pool()
    try:
        conn = _pool.get_nowait()
        try:
            conn.run("SELECT 1")
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = _create_connection()
        return conn
    except queue.Empty:
        return _create_connection()


def release_connection(conn, valid=True):
    """Remet la connexion au pool. Si invalide, la ferme et en crée une nouvelle."""
    if not valid:
        try:
            conn.close()
        except Exception:
            pass
        try:
            _pool.put_nowait(_create_connection())
        except Exception:
            pass
        return
    try:
        _pool.put_nowait(conn)
    except queue.Full:
        try:
            conn.close()
        except Exception:
            pass