"""
Cache layer for tracking request IDs and their states
"""
import json
from typing import Optional, Dict, Any
import redis
import os
from datetime import datetime, timedelta


class RequestCache:
    """
    Manages the requestID cache to track request states across services
    """

    def __init__(self, redis_url: str = None):
        """
        Initialize cache with optional Redis backend
        Falls back to in-memory cache if Redis is not available
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.use_redis = False
        self.redis_client = None
        self.memory_cache: Dict[str, Any] = {}

        try:
            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()
            self.use_redis = True
            print("✓ Connected to Redis")
        except Exception as e:
            print(f"⚠ Redis connection failed: {e}. Using in-memory cache.")
            self.use_redis = False

    def store_request(self, request_id: str, client_id: str, metadata: dict = None) -> bool:
        """
        Store a mapping from request_id to client_id
        """
        data = {
            "client_id": client_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        try:
            if self.use_redis:
                self.redis_client.setex(
                    f"request:{request_id}",
                    86400,  # 24 hours TTL
                    json.dumps(data),
                )
            else:
                self.memory_cache[request_id] = data
            return True
        except Exception as e:
            print(f"Error storing request: {e}")
            return False

    def get_request(self, request_id: str) -> Optional[dict]:
        """
        Retrieve request metadata
        """
        try:
            if self.use_redis:
                data = self.redis_client.get(f"request:{request_id}")
                if data:
                    return json.loads(data)
            else:
                return self.memory_cache.get(request_id)
        except Exception as e:
            print(f"Error retrieving request: {e}")
        return None

    def update_status(self, request_id: str, status: str, result: dict = None) -> bool:
        """
        Update request status
        """
        try:
            request_data = self.get_request(request_id)
            if not request_data:
                return False

            request_data["status"] = status
            request_data["updated_at"] = datetime.utcnow().isoformat()
            if result:
                request_data["result"] = result

            if self.use_redis:
                self.redis_client.setex(
                    f"request:{request_id}",
                    86400,
                    json.dumps(request_data),
                )
            else:
                self.memory_cache[request_id] = request_data
            return True
        except Exception as e:
            print(f"Error updating status: {e}")
            return False

    def delete_request(self, request_id: str) -> bool:
        """
        Delete request from cache
        """
        try:
            if self.use_redis:
                self.redis_client.delete(f"request:{request_id}")
            else:
                self.memory_cache.pop(request_id, None)
            return True
        except Exception as e:
            print(f"Error deleting request: {e}")
            return False


# Global cache instance
_cache_instance = None


def get_cache() -> RequestCache:
    """Get or create the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RequestCache()
    return _cache_instance
