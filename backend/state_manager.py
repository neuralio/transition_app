import json
from redis_conn import redis_client  # Χρησιμοποίησε τον υπάρχοντα client

SESSION_TTL_SEC = 14 * 24 * 60 * 60  # 14 days


def touch_session_ttl(session_id: str):
    """
    Refresh TTL for all keys related to this session.
    Safe to call even if some keys don't exist.
    """
    keys = [
        f"chat:{session_id}",
        f"chat:{session_id}:history",
        f"state:{session_id}",
        f"session:{session_id}",           # global doc (if present)
        f"session:{session_id}:owner",     # owner pointer (if present)
    ]
    pipe = redis_client.pipeline()
    for k in keys:
        pipe.expire(k, SESSION_TTL_SEC)
    pipe.execute()

# Επιστρέφει το Redis state ενός session
def load_state(session_id: str):
    key = f"state:{session_id}"
    if redis_client.exists(key):
        return json.loads(redis_client.get(key))
    return None

# Αποθηκεύει το state στο Redis
def save_state(session_id: str, state: dict):
    key = f"state:{session_id}"
    pipe = redis_client.pipeline()
    pipe.set(key, json.dumps(state))
    pipe.expire(key, SESSION_TTL_SEC)        # state key expires in 14d
    pipe.execute()
    touch_session_ttl(session_id)            # refresh all related keys

# Δημιουργεί νέο state όταν ξεκινά μια συνεδρία
def init_state(session_id: str):
    state = {
        "service": None,
        "current_step": "select_service",
        "collected_inputs": {}
    }
    save_state(session_id, state)
    return state