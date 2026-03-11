# API-Processor

A decoupled, scalable architecture for processing slow/long-running API requests. This system decouples request acceptance, processing, and response handling into independent services that can be scaled separately.

## Architecture Overview

```
┌─────────────────────────┐
│   API Server            │  Part 1: Accepts requests
│  (FastAPI)              │  - Validates and queues requests
└────────────┬────────────┘  - Returns request_id immediately
             │
             ↓
    ┌─────────────────┐
    │ Request Topic   │
    └────────┬────────┘
             │
             ↓
┌─────────────────────────┐
│  Request Processor(s)   │  Part 2: Scales independently
│  (Horizontal scaling)   │  - Picks requests from queue
│  Multiple workers       │  - Heavy computation happens here
└────────────┬────────────┘  - Publishes results
             │
             ↓
    ┌─────────────────┐
    │ Response Topic  │
    └────────┬────────┘
             │
             ↓
┌─────────────────────────┐
│  Response Handler       │  Part 3: Finalizes responses
│  (FastAPI)              │  - Processes completed tasks
│  Status management      │  - Notifications/webhooks
└─────────────────────────┘
             ↑
             │
    ┌─────────────────┐
    │ Request Cache   │ Tracks request states via Redis/Memory
    └─────────────────┘
```

## Key Benefits

1. **Decoupling**: API Server doesn't block on heavy processing
2. **Scalability**: Add more processors without changing API server
3. **Resilience**: System can handle traffic spikes via queue buffering
4. **Non-blocking**: Clients get immediate response with request_id
5. **Flexibility**: Each component can be deployed/scaled independently

## System Components

### 1. API Server (`api_server.py`)
- Accepts incoming requests via FastAPI
- Assigns unique request IDs
- Stores request metadata in cache
- Publishes requests to queue
- Provides endpoints to check processing status

**Endpoints:**
- `POST /api/request` - Submit a new request
- `GET /api/response/{request_id}` - Check request status/result
- `GET /api/status` - Health check

### 2. Request Processor (`processor.py`)
- Pulls requests from the request queue
- Executes the heavy computation logic
- Publishes results to response topic
- Can run multiple instances for parallel processing

**Customization Point:** Modify `process_request()` method to implement your actual processing logic

### 3. Response Handler (`response_handler.py`)
- Consumes responses from response topic
- Updates cache with final status
- Triggers notifications (webhooks, emails, etc.)
- Can be extended for downstream processing

### 4. Supporting Modules
- `queue.py` - In-memory message queue (supports Redis integration)
- `cache.py` - Request tracking cache (Redis with memory fallback)
- `models.py` - Pydantic models for type safety

## Installation

```bash
# Clone the repository
cd API-Processor

# Install dependencies
pip install -r requirements.txt

# Optional: Set up Redis for production
# Export Redis URL (or use in-memory cache)
export REDIS_URL="redis://localhost:6379/0"
```

## Running the System

### Option 1: Run all services locally (Development)

```bash
# Terminal 1: Start API Server
python api_server.py

# Terminal 2: Start Request Processor(s)
python processor.py worker-1

# Terminal 3: Start Response Handler
python response_handler.py

# Terminal 4: Run demo/tests
python demo.py
```

### Option 2: Run with different port configurations

```bash
# Terminal 1: API Server on port 8000
API_SERVER_PORT=8000 python api_server.py

# Terminal 2: Processor 1
python processor.py worker-1

# Terminal 3: Processor 2 (for horizontal scaling)
python processor.py worker-2

# Terminal 4: Response Handler
python response_handler.py
```

### Option 3: Docker (Optional)

```bash
# Build and run with Docker Compose
docker-compose up
```

## Usage Example

```python
import requests
import time
import json

BASE_URL = "http://localhost:8000"

# 1. Submit a request
response = requests.post(
    f"{BASE_URL}/api/request",
    json={
        "endpoint": "/heavy-computation",
        "method": "POST",
        "payload": {"data": "sample", "count": 100},
        "client_id": "my-client-1"
    }
)

request_data = response.json()
request_id = request_data["request_id"]
print(f"Request submitted: {request_id}")

# 2. Poll for response (with timeout)
max_attempts = 30
attempt = 0

while attempt < max_attempts:
    response = requests.get(f"{BASE_URL}/api/response/{request_id}")
    result = response.json()
    
    if result["status"] == "completed":
        print("✓ Processing complete!")
        print(json.dumps(result, indent=2))
        break
    elif result["status"] == "failed":
        print("✗ Processing failed!")
        print(json.dumps(result, indent=2))
        break
    else:
        print(f"Status: {result['status']}... waiting")
        time.sleep(1)
        attempt += 1
else:
    print("Request timeout")
```

## Configuration

### Environment Variables

```bash
# Redis connection (optional, falls back to in-memory)
export REDIS_URL="redis://localhost:6379/0"

# API Server port
export API_SERVER_PORT=8000

# Request polling intervals
export PROCESSOR_POLL_INTERVAL=1
export HANDLER_POLL_INTERVAL=1
```

## Scaling Strategies

### Horizontal Scaling - Add more processors
```bash
# Run multiple processor instances
python processor.py worker-1 &
python processor.py worker-2 &
python processor.py worker-3 &
```

### Load balancing - Multiple API servers
Consider running multiple API server instances behind a load balancer.

## Production Deployment

For production, consider:

1. **Message Queue**: Replace `InMemoryQueue` with:
   - RabbitMQ
   - Apache Kafka
   - AWS SQS
   - Google Cloud Pub/Sub

2. **Cache Layer**:
   - Use Redis cluster
   - Or managed services (ElastiCache, Memorystore)

3. **API Server**:
   - Run behind Nginx/HAProxy
   - Use Kubernetes for orchestration
   - Auto-scaling based on queue depth

4. **Monitoring**:
   - Add Prometheus metrics
   - Set up logging aggregation (ELK/Loki)
   - Alert on queue depth/processing time

5. **Error Handling**:
   - Implement retry logic with exponential backoff
   - Dead letter queues for failed messages
   - Circuit breakers for dependent services

## Customization

### Implement your processing logic

Edit `processor.py` - `process_request()` method:

```python
def process_request(self, request_data: str) -> dict:
    request = json.loads(request_data.replace("'", '"'))
    request_id = request["request_id"]
    endpoint = request["endpoint"]
    payload = request["payload"]
    
    # YOUR CUSTOM LOGIC HERE
    # - Call external APIs
    # - Run ML models
    # - Process large datasets
    # - Database operations
    
    result = {
        "processed_at": datetime.utcnow().isoformat(),
        "output": "your_processing_result"
    }
    
    return {
        "request_id": request_id,
        "status": "success",
        "result": result,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### Add response handlers

Edit `response_handler.py` - `handle_response()` method:

```python
def handle_response(self, response_data: str) -> bool:
    response = json.loads(response_data)
    request_id = response["request_id"]
    
    # Add custom handlers:
    # - Send webhook notification
    # - Update database
    # - Trigger downstream processing
    # - Send email
    # - Update UI via WebSocket
    
    return True
```

## Testing

Run the demo script:

```bash
python demo.py
```

This will:
1. Submit 3 test requests
2. Poll for responses
3. Display results

## Performance Characteristics

- **Request acceptance**: ~5-10ms (non-blocking)
- **Processing**: Depends on your implementation (simulated as 2 seconds)
- **Response retrieval**: ~1-2ms
- **Queue depth**: Unlimited (limited by available memory/Redis)

## Troubleshooting

**Connection refused**
- Ensure all services are running
- Check port availability

**Redis connection failed**
- System falls back to in-memory cache
- For production, ensure Redis is running: `redis-server`

**Requests not being processed**
- Check processor logs for errors
- Verify queue has requests: `GET /api/status`
- Ensure response handler is running

## License

MIT
