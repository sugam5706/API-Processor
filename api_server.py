"""
Part 1: API Server
Accepts API requests and publishes them to the request topic for processing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime
import uvicorn
import os
from models import ApiRequestModel, ProcessingResponse
from queue import get_queue
from cache import get_cache

app = FastAPI(title="API Processor - Server")

# Initialize queue and cache
queue = get_queue()
cache = get_cache()

# Constants
REQUEST_TOPIC = "requests"
RESPONSE_TOPIC = "responses"


@app.post("/api/request")
async def submit_request(api_request: ApiRequestModel, background_tasks: BackgroundTasks):
    """
    Accept API requests and dispatch to processing queue
    
    Returns immediately with request_id for client to poll response
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    client_id = api_request.client_id or f"client-{request_id[:8]}"

    # Store in cache for later retrieval
    cache.store_request(
        request_id=request_id,
        client_id=client_id,
        metadata={
            "endpoint": api_request.endpoint,
            "method": api_request.method,
        },
    )

    # Create processing request
    processing_request = {
        "request_id": request_id,
        "endpoint": api_request.endpoint,
        "method": api_request.method,
        "payload": api_request.payload,
        "timestamp": datetime.utcnow().isoformat(),
        "client_id": client_id,
    }

    # Publish to request topic
    queue.publish(REQUEST_TOPIC, str(processing_request))
    
    cache.update_status(request_id, "queued")

    return {
        "status": "accepted",
        "request_id": request_id,
        "client_id": client_id,
        "message": "Request queued for processing. Poll /api/response/{request_id} to check status.",
    }


@app.get("/api/response/{request_id}")
async def get_response(request_id: str):
    """
    Retrieve the response for a submitted request
    """
    # Check cache for request status
    request_data = cache.get_request(request_id)

    if not request_data:
        raise HTTPException(status_code=404, detail="Request not found")

    status = request_data.get("status", "unknown")

    if status == "completed":
        return {
            "status": "completed",
            "request_id": request_id,
            "result": request_data.get("result"),
        }
    elif status == "failed":
        return {
            "status": "failed",
            "request_id": request_id,
            "error": request_data.get("error"),
        }
    else:
        return {
            "status": status,
            "request_id": request_id,
            "message": f"Request is {status}. Check back soon.",
        }


@app.get("/api/status")
async def get_server_status():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "API Server",
        "requests_in_queue": len(queue.get_messages(REQUEST_TOPIC)),
    }


if __name__ == "__main__":
    port = int(os.getenv("API_SERVER_PORT", 8000))
    print(f"🚀 Starting API Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
