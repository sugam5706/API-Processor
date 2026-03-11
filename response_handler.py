"""
Part 3: Response Handler
Consumes responses from the response topic and finalizes processing
"""

import json
import time
from datetime import datetime
import os
from queue import get_queue
from cache import get_cache

RESPONSE_TOPIC = "responses"


class ResponseHandler:
    """
    Handles and finalizes responses from processors
    Can be run in a separate service
    """

    def __init__(self, handler_id: str = None):
        self.handler_id = handler_id or f"response-handler-{os.getpid()}"
        self.queue = get_queue()
        self.cache = get_cache()
        self.is_running = False
        self.processed_count = 0

    def handle_response(self, response_data: str) -> bool:
        """
        Handle a single response
        This is where you'd send notifications, trigger webhooks, etc.
        """
        try:
            response = json.loads(response_data)
            request_id = response["request_id"]

            print(f"[{self.handler_id}] Handling response for request {request_id}")

            # Update cache with final status
            if response["status"] == "success":
                self.cache.update_status(
                    request_id,
                    "completed",
                    response.get("result"),
                )
                print(f"[{self.handler_id}] ✓ Response {request_id} finalized")

            elif response["status"] == "failed":
                self.cache.update_status(request_id, "failed")
                # Store error details
                request_data = self.cache.get_request(request_id)
                if request_data:
                    request_data["error"] = response.get("error")
                print(f"[{self.handler_id}] ✗ Response {request_id} marked as failed")

            # TODO: Implement additional handlers
            # - Send webhook to client
            # - Write to database
            # - Send email notification
            # - Log to external service
            # - Trigger downstream processing

            self.processed_count += 1
            return True

        except Exception as e:
            print(f"[{self.handler_id}] Error handling response: {e}")
            return False

    def start(self, poll_interval: int = 1):
        """
        Start consuming responses continuously
        """
        self.is_running = True
        print(f"[{self.handler_id}] Starting response handler...")

        while self.is_running:
            try:
                # Consume one message from response topic
                response_data = self.queue.consume(RESPONSE_TOPIC)

                if response_data:
                    self.handle_response(response_data)
                else:
                    # No responses to handle, wait before checking again
                    time.sleep(poll_interval)

            except Exception as e:
                print(f"[{self.handler_id}] Error in handler loop: {e}")
                time.sleep(poll_interval)

    def stop(self):
        """Stop handling responses"""
        self.is_running = False
        print(
            f"[{self.handler_id}] Stopping response handler (processed {self.processed_count} responses)..."
        )

    def get_stats(self) -> dict:
        """Get handler statistics"""
        return {
            "handler_id": self.handler_id,
            "processed_count": self.processed_count,
            "is_running": self.is_running,
        }


def run_handler(handler_id: str = None):
    """Run a single response handler instance"""
    handler = ResponseHandler(handler_id)
    try:
        handler.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        handler.stop()


if __name__ == "__main__":
    import sys

    handler_id = sys.argv[1] if len(sys.argv) > 1 else None
    run_handler(handler_id)
