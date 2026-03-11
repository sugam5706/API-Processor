# Architecture Documentation

## System Overview

The API Processor is a three-tier decoupled architecture designed to handle long-running API requests without blocking client connections.

```
┌──────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW                              │
└──────────────────────────────────────────────────────────────────┘

CLIENT
  │
  ├─────────────┐
  │             ↓
  │    ┌─────────────────────┐
  │    │  API Server (Tier 1) │
  │    │  - Validate request   │
  │    │  - Assign request_id  │
  │    │  - Return immediately │
  │    └──────────┬────────────┘
  │             │ Publish
  │             ↓
  │    ┌─────────────────────┐
  │    │  Request Queue      │
  │    │  (message broker)   │
  │    └──────────┬────────────┘
  │             │ Consume
  │             ↓
  │    ┌─────────────────────┐
  │    │ Processor (Tier 2)   │
  │    │ - Heavy processing   │
  │    │ - Long computation   │
  │    │ - Publish result     │
  │    │ - Scalable workers   │
  │    └──────────┬────────────┘
  │             │ Publish
  │             ↓
  │    ┌─────────────────────┐
  │    │  Response Queue     │
  │    │  (message broker)   │
  │    └──────────┬────────────┘
  │             │ Consume
  │             ↓
  │    ┌─────────────────────┐
  │    │ Handler (Tier 3)    │
  │    │ - Finalize response │
  │    │ - Update cache      │
  │    │ - Trigger webhooks  │
  │    └──────────┬────────────┘
  │             │ Update
  │             ↓
  │    ┌─────────────────────┐
  │    │  Cache (Redis/Mem)  │
  │    │  - Track state      │
  │    │  - Store result     │
  │    └─────────────────────┘
  │
  └─────────────────────────────┐
                                │ Poll
                                ↓
                    ┌─────────────────────┐
                    │  API Server         │
                    │  GET /response/{id}  │
                    └─────────────────────┘
```

## Tier 1: API Server

**File:** `api_server.py`

### Responsibilities
- Accept incoming API requests
- Validate request format and size
- Generate unique request IDs
- Store metadata in cache
- Publish requests to queue
- Provide status endpoints

### Key Endpoints
```
POST /api/request
  Input: { endpoint, method, payload, client_id }
  Output: { status, request_id, message }
  Time: ~5-10ms (non-blocking)

GET /api/response/{request_id}
  Output: { status, request_id, result/error }
  Time: ~1-2ms

GET /api/status
  Output: { status, requests_in_queue }
  Time: ~1ms
```

### Architecture Decisions
- **Non-blocking:** Returns immediately with request_id
- **Stateless:** Can run multiple instances behind load balancer
- **Failure Handling:** Graceful error messages
- **Request Validation:** Size and format checks

## Tier 2: Request Processor

**File:** `processor.py`

### Responsibilities
- Pull requests from queue (FIFO)
- Execute processing logic
- Handle errors gracefully
- Publish results to response queue
- Track metrics

### Key Features
- **Scalability:** Run multiple worker instances
- **Parallel Processing:** Handle N requests simultaneously
- **Customizable:** Modify `process_request()` for your logic
- **Error Recovery:** Retry logic (implementable)

### Processor Instance
```python
class RequestProcessor:
    def __init__(self, worker_id):
        # Initialize worker
        
    def process_request(self, request_data):
        # YOUR CUSTOM LOGIC HERE
        # - API calls
        # - ML inference
        # - Data processing
        # - Database operations
        
    def start(self):
        # Continuous polling loop
        while running:
            request = queue.consume()
            result = process_request(request)
            queue.publish("responses", result)
```

### Scaling Pattern
```bash
processor-1 \
processor-2  |---> Shared Queue
processor-3 /
```

Each processor independently pulls from the same queue, ensuring:
- Load balancing across workers
- High throughput
- Independent failure isolation

## Tier 3: Response Handler

**File:** `response_handler.py`

### Responsibilities
- Consume responses from queue
- Update cache with final status
- Trigger notifications (webhooks, emails, etc.)
- Persist to database (optional)
- Clean up resources

### Handler Instance
```python
class ResponseHandler:
    def handle_response(self, response_data):
        # Update cache
        cache.update_status(request_id, "completed", result)
        
        # Optional: Send webhook
        # webhook.send(client_id, result)
        
        # Optional: Write to database
        # db.save_result(result)
        
        # Optional: Email notification
        # email.send(client_id, "Your request completed!")
```

## Supporting Components

### Cache Layer (`cache.py`)

**Purpose:** Track request state across services

```
Redis (Production)
    │
    └─-> key: "request:{id}"
         value: {
           client_id,
           status,
           result,
           timestamps
         }
```

**Fallback:** In-memory dictionary (development)

**Features:**
- TTL-based expiration (24 hours)
- Atomic updates
- Thread-safe operations

### Message Queue (`queue.py`)

**Purpose:** Decouple services via async messaging

**In-Memory Implementation:**
```python
{
  "requests": [msg1, msg2, msg3, ...],
  "responses": [msg1, msg2, msg3, ...]
}
```

**Production Alternatives:**
- RabbitMQ (reliability)
- Kafka (high throughput)
- AWS SQS (managed service)
- Google Pub/Sub (Google Cloud)

## Data Models

### ProcessingRequest
```json
{
  "request_id": "uuid",
  "endpoint": "/api/endpoint",
  "method": "POST",
  "payload": { /* user data */ },
  "timestamp": "2024-03-11T10:00:00Z",
  "client_id": "client-123"
}
```

### ProcessingResponse
```json
{
  "request_id": "uuid",
  "status": "success|failed|processing",
  "result": { /* computed result */ },
  "error": null,
  "timestamp": "2024-03-11T10:00:05Z",
  "processed_by": "worker-1"
}
```

## Request Lifecycle

### Phase 1: Acceptance (API Server)
```
1. Client submits request
2. API Server validates
3. Generate request_id
4. Store in cache (status: "queued")
5. Publish to request topic
6. Return request_id to client
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Elapsed: ~5-10ms
```

### Phase 2: Processing (Processor)
```
1. Consume from request topic
2. Deserialize request
3. Execute processing logic
4. Handle any errors
5. Publish to response topic
6. Update processed counter
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Elapsed: Variable (2s - hours)
Can be parallelized across workers
```

### Phase 3: Finalization (Handler)
```
1. Consume from response topic
2. Update cache (status: "completed")
3. Store result in cache
4. Execute custom handlers
   - Webhooks
   - Database writes
   - Notifications
5. Clean up if needed
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Elapsed: ~1-10ms
```

### Phase 4: Retrieval (Client Poll)
```
1. Client polls GET /api/response/{id}
2. Server checks cache
3. Return current status and result
4. Client continues polling or receives result
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Elapsed: ~1-2ms per poll
```

## Deployment Scenarios

### Single Machine (Development)
```
One machine:
  ├─ API Server (port 8000)
  ├─ Processor 1 (shares memory)
  └─ Response Handler (shares memory)
  
Use: In-memory queue and cache
```

### Multi-Machine (Production)
```
Load Balancer
  ├─ API Server 1 ┐
  ├─ API Server 2 |──→ Redis Cluster
  └─ API Server 3 ┘
  
Processor Cluster
  ├─ Worker 1 ┐
  ├─ Worker 2 |──→ Message Broker (RabbitMQ/Kafka)
  ├─ Worker 3 |
  └─ Worker 4 ┘
  
Handler Service
  └─ Response Handler ──→ Redis + Database + Notifications
```

### Serverless (Cloud-Native)
```
API Gateway
  ↓
Cloud Functions (API Server)
  ↓
Message Queue (Pub/Sub)
  ↓
Cloud Functions (Processor) - Auto-scaling
  ↓
Message Queue
  ↓
Cloud Functions (Handler)
  ↓
Cloud Database + Cache
```

## Error Handling

### Request Validation Errors (Tier 1)
```
→ Return 400/422 immediately
→ Do not queue request
→ Log error
```

### Processing Errors (Tier 2)
```
→ Catch exception
→ Create error response
→ Publish to response topic
→ Handler marks as "failed"
```

### Handler Errors (Tier 3)
```
→ Log error
→ Retry if transient
→ Alert operations team
→ Do not fail silently
```

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Request Submit | 5-10ms | Non-blocking |
| Queue Publish | <1ms | O(1) |
| Queue Consume | <1ms | O(1) |
| Response Retrieve | 1-2ms | Cache lookup |
| Processing | Variable | Depends on logic |
| Total E2E | Request time + Processing | Can be minutes/hours |

## Scalability

### Horizontal (Add More Servers)
- Add more processors for parallelism
- Add more API servers behind load balancer
- Add more handlers for webhooks
- All services are stateless

### Vertical (Single Server)
- Add processor workers (threads/processes)
- Increase cache size
- Increase message queue buffer

### Queue Depth
As requests accumulate:
```
- Queue depth increases
- Longer wait times for clients
- Solution: Add more processors
```

## Monitoring

Key metrics to track:
- Queue depth (requests waiting)
- Processing time (per request)
- Handler latency
- Error rate
- Cache hit rate
- Worker utilization

```bash
# Health check endpoint
GET /api/status
→ {
    "status": "healthy",
    "requests_in_queue": 42
  }
```
