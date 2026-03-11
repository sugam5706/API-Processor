# Quick Start Guide

Get the API Processor system up and running in 5 minutes.

## Prerequisites

- Python 3.9+
- Redis (optional, system uses in-memory cache as fallback)

## Installation

```bash
# 1. Clone/setup the project
cd API-Processor

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Start Redis
redis-server
```

## Run Locally (3 Terminals)

**Terminal 1 - API Server:**
```bash
python api_server.py
# Output: 🚀 Starting API Server on port 8000
```

**Terminal 2 - Request Processor:**
```bash
python processor.py worker-1
# Output: [worker-1] Starting request processor...
```

**Terminal 3 - Response Handler:**
```bash
python response_handler.py
# Output: [response-handler-XXXX] Starting response handler...
```

**Terminal 4 - Run Demo (Optional):**
```bash
python demo.py
```

## Run with Docker

```bash
# Build and start all services
docker-compose up

# In another terminal, run demo
python demo.py
```

## Test the System

### Using cURL:

```bash
# 1. Submit a request
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "/process",
    "method": "POST",
    "payload": {"data": "test"}
  }'

# Response:
# {
#   "status": "accepted",
#   "request_id": "uuid-here",
#   "client_id": "client-uuid",
#   "message": "Request queued for processing..."
# }

# 2. Check status (replace REQUEST_ID with actual id)
curl http://localhost:8000/api/response/REQUEST_ID

# 3. Check server health
curl http://localhost:8000/api/status
```

### Using Python:

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# Submit request
r = requests.post(f"{BASE_URL}/api/request", json={
    "endpoint": "/process",
    "payload": {"data": "test"}
})
request_id = r.json()["request_id"]
print(f"Request ID: {request_id}")

# Poll for response
while True:
    r = requests.get(f"{BASE_URL}/api/response/{request_id}")
    result = r.json()
    
    if result["status"] == "completed":
        print("✓ Done!")
        print(result["result"])
        break
    else:
        print(f"Status: {result['status']}")
        time.sleep(1)
```

## Scaling

### Add More Processors:

```bash
# Terminal 2a - Second processor
python processor.py worker-2

# Terminal 2b - Third processor
python processor.py worker-3
```

The load will automatically distribute across all processors!

## Common Issues

**Port already in use:**
```bash
# Change port
API_SERVER_PORT=8001 python api_server.py
```

**Redis connection failed:**
```bash
# System automatically falls back to in-memory cache
# No action needed - everything still works!
```

**Requests not processing:**
1. Verify all 3 services are running
2. Check logs for errors
3. Verify firewall isn't blocking connections

## Stop Services

```bash
# Press Ctrl+C in each terminal

# Or stop Docker containers:
docker-compose down
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Customize processing logic in [processor.py](processor.py)
- Add webhooks in [response_handler.py](response_handler.py)
- Deploy to production (see README.md for options)

## Performance Tips

1. **Increase processors** for parallelism
2. **Use Redis** for distributed deployments
3. **Add load balancer** for multiple API servers
4. **Monitor queue depth** to scale proactively

## Get Help

- Check logs for detailed error messages
- Run `python demo.py` to test the full flow
- Review code comments in each module
