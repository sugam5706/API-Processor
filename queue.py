"""
Message queue implementation for request/response topics
"""
import json
import os
from typing import Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
import threading
import time
from models import ProcessingRequest, ProcessingResponse


@dataclass
class Message:
    """A message in the queue"""
    content: str
    timestamp: float
    topic: str
    message_id: str


class InMemoryQueue:
    """
    In-memory message queue for decoupled communication
    Can be replaced with RabbitMQ, Kafka, or Redis for production
    """

    def __init__(self):
        self.topics: dict = {}
        self.subscribers: dict = {}
        self.lock = threading.RLock()

    def publish(self, topic: str, message: str) -> bool:
        """Publish a message to a topic"""
        with self.lock:
            if topic not in self.topics:
                self.topics[topic] = []

            self.topics[topic].append(
                Message(
                    content=message,
                    timestamp=time.time(),
                    topic=topic,
                    message_id=f"{topic}-{len(self.topics[topic])}",
                )
            )
            return True

    def subscribe(self, topic: str, callback: Callable) -> str:
        """
        Subscribe to a topic with a callback function
        Returns subscriber ID
        """
        with self.lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = {}

            subscriber_id = f"{topic}-sub-{len(self.subscribers[topic])}"
            self.subscribers[topic][subscriber_id] = callback
            return subscriber_id

    def unsubscribe(self, topic: str, subscriber_id: str) -> bool:
        """Unsubscribe from a topic"""
        with self.lock:
            if topic in self.subscribers and subscriber_id in self.subscribers[topic]:
                del self.subscribers[topic][subscriber_id]
                return True
            return False

    def get_messages(self, topic: str, start_index: int = 0) -> List[Message]:
        """Get all messages for a topic"""
        with self.lock:
            if topic not in self.topics:
                return []
            return self.topics[topic][start_index:]

    def consume(self, topic: str) -> Optional[str]:
        """Consume (get and remove) the first message from a topic"""
        with self.lock:
            if topic in self.topics and len(self.topics[topic]) > 0:
                message = self.topics[topic].pop(0)
                return message.content
            return None

    def _notify_subscribers(self, topic: str, message: str):
        """Notify all subscribers about a new message"""
        with self.lock:
            if topic in self.subscribers:
                for callback in self.subscribers[topic].values():
                    try:
                        callback(message)
                    except Exception as e:
                        print(f"Error in subscriber callback: {e}")


# Global queue instance
_queue_instance = None


def get_queue() -> InMemoryQueue:
    """Get or create the global queue instance"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = InMemoryQueue()
    return _queue_instance
