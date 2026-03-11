"""
Part 2: Request Processor
Picks requests from the queue, processes them, and publishes results to response topic
This service can be scaled independently
"""

import time
import json
from datetime import datetime
import os
from queue import get_queue
from cache import get_cache

REQUEST_TOPIC = "requests"
RESPONSE_TOPIC = "responses"


class RequestProcessor:
    """
    Processes requests from the queue
    Can be instantiated multiple times for horizontal scaling
    """

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        self.queue = get_queue()
        self.cache = get_cache()
        self.is_running = False

    def process_request(self, request_data: str) -> dict:
        """
        Process a single request
        This is where your heavy computation logic goes
        """
        try:
            # Parse request
            request = json.loads(request_data.replace("'", '"'))

            request_id = request["request_id"]
            endpoint = request["endpoint"]
            payload = request["payload"]

            print(
                f"[{self.worker_id}] Processing request {request_id} for endpoint {endpoint}"
            )

            # Simulate processing time (replace with actual API call)
            processing_time = 2  # seconds
            print(
                f"[{self.worker_id}] Simulating {processing_time}s processing for {request_id}..."
            )
            time.sleep(processing_time)

            # Simulate processing result
            result = {
                "processed_at": datetime.utcnow().isoformat(),
                "input": payload,
                "computation": "Heavy computation completed successfully",
                "data_points": len(str(payload)),
            }

            # Create response
            response = {
                "request_id": request_id,
                "status": "success",
                "result": result,
                "error": None,
                "timestamp": datetime.utcnow().isoformat(),
                "processed_by": self.worker_id,
            }

            print(f"[{self.worker_id}] ✓ Request {request_id} processed successfully")
            return response

        except Exception as e:
            print(f"[{self.worker_id}] ✗ Error processing request: {e}")
            return {
                "request_id": request.get("request_id", "unknown"),
                "status": "failed",
                "result": None,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "processed_by": self.worker_id,
            }

    def start(self, poll_interval: int = 1):
        """
        Start processing requests continuously
        """
        self.is_running = True
        print(f"[{self.worker_id}] Starting request processor...")

        while self.is_running:
            try:
                # Consume one message from request topic
                request_data = self.queue.consume(REQUEST_TOPIC)

                if request_data:
                    # Process the request
                    response = self.process_request(request_data)

                    # Publish response to response topic
                    self.queue.publish(RESPONSE_TOPIC, json.dumps(response))

                    # Update cache with result
                    self.cache.update_status(
                        response["request_id"],
                        response["status"],
                        response.get("result"),
                    )
                else:
                    # No requests in queue, wait before checking again
                    time.sleep(poll_interval)

            except Exception as e:
                print(f"[{self.worker_id}] Error in processing loop: {e}")
                time.sleep(poll_interval)

    def stop(self):
        """Stop processing requests"""
        self.is_running = False
        print(f"[{self.worker_id}] Stopping request processor...")


def run_processor(worker_id: str = None):
    """Run a single processor instance"""
    processor = RequestProcessor(worker_id)
    try:
        processor.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        processor.stop()


if __name__ == "__main__":
    import sys

    worker_id = sys.argv[1] if len(sys.argv) > 1 else None
    run_processor(worker_id)
