"""
Demo script to test the API Processor system
Run this after starting API server, processor, and response handler
"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 3


def submit_request(request_num: int) -> str:
    """Submit a test request and return request_id"""
    payload = {
        "data": f"Test payload {request_num}",
        "timestamp": time.time(),
        "processing_intensity": request_num * 10,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/request",
            json={
                "endpoint": "/heavy-computation",
                "method": "POST",
                "payload": payload,
                "client_id": f"demo-client-{request_num}",
            },
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Request {request_num} submitted: {data['request_id']}")
            return data["request_id"]
        else:
            print(f"✗ Request {request_num} failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Request {request_num} error: {e}")
        return None


def poll_response(request_id: str, max_attempts: int = 30) -> dict:
    """Poll for response until completed or timeout"""
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(f"{BASE_URL}/api/response/{request_id}", timeout=5)

            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"  Error polling {request_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"  Error polling {request_id}: {e}")

        time.sleep(1)
        attempt += 1

    return {"status": "timeout", "request_id": request_id}


def check_server_health():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=3)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API Server is healthy")
            print(f"  Requests in queue: {data.get('requests_in_queue', 'N/A')}")
            return True
    except Exception as e:
        print(f"✗ API Server is not responding: {e}")
        return False


def main():
    print("=" * 60)
    print("API Processor System - Demo")
    print("=" * 60)

    # Check server health
    print("\n1. Checking server health...")
    if not check_server_health():
        print("Please start the API server first: python api_server.py")
        sys.exit(1)

    # Submit requests
    print(f"\n2. Submitting {NUM_REQUESTS} test requests...")
    request_ids = []
    for i in range(1, NUM_REQUESTS + 1):
        req_id = submit_request(i)
        if req_id:
            request_ids.append(req_id)

    if not request_ids:
        print("No requests were submitted successfully")
        sys.exit(1)

    # Poll for responses
    print(f"\n3. Polling for responses ({len(request_ids)} submitted)...")
    print("   (This may take a moment...)\n")

    results = {}
    for request_id in request_ids:
        print(f"  Polling {request_id}...")
        result = poll_response(request_id)
        results[request_id] = result

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    for request_id, result in results.items():
        if result:
            print(f"\nRequest ID: {request_id}")
            print(f"  Status: {result.get('status')}")

            if result.get("status") == "completed":
                print(f"  ✓ COMPLETED")
                if result.get("result"):
                    print(f"  Result: {json.dumps(result['result'], indent=4)}")
            elif result.get("status") == "failed":
                print(f"  ✗ FAILED")
                if result.get("error"):
                    print(f"  Error: {result['error']}")
            else:
                print(f"  Status: {result.get('status')}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)

    # Summary
    completed = sum(
        1 for r in results.values() if r and r.get("status") == "completed"
    )
    failed = sum(1 for r in results.values() if r and r.get("status") == "failed")
    timeout = sum(1 for r in results.values() if r and r.get("status") == "timeout")

    print(f"\nSummary:")
    print(f"  Completed: {completed}/{len(results)}")
    print(f"  Failed: {failed}/{len(results)}")
    print(f"  Timeout: {timeout}/{len(results)}")


if __name__ == "__main__":
    main()
