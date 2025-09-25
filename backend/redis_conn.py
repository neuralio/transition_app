# redis_conn.py
import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    db=0,
    decode_responses=True
)