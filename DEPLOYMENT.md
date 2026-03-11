# Production Deployment Guide

## Pre-Deployment Checklist

- [ ] Customize `process_request()` in processor.py
- [ ] Implement `handle_response()` in response_handler.py
- [ ] Set up Redis cluster or managed Redis service
- [ ] Configure external message broker (RabbitMQ/Kafka/SQS)
- [ ] Set up database for result persistence
- [ ] Configure logging aggregation (ELK/Datadog/CloudWatch)
- [ ] Set up monitoring and alerting (Prometheus/New Relic)
- [ ] Implement webhook endpoints on client side
- [ ] Load test the system
- [ ] Plan disaster recovery

## Option 1: Kubernetes Deployment

### Prerequisites
```bash
- Kubernetes cluster (1.20+)
- Docker registry access
- kubectl configured
```

### Create Docker Images

```bash
# Build images
docker build -t your-registry/api-processor-server:1.0 .
docker build -t your-registry/api-processor-worker:1.0 .
docker build -t your-registry/api-processor-handler:1.0 .

# Push to registry
docker push your-registry/api-processor-server:1.0
docker push your-registry/api-processor-worker:1.0
docker push your-registry/api-processor-handler:1.0
```

### Kubernetes Manifests

**namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: api-processor
```

**redis-statefulset.yaml**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: api-processor
spec:
  selector:
    matchLabels:
      app: redis
  serviceName: redis
  replicas: 1
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

**api-server-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: api-processor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api-server
        image: your-registry/api-processor-server:1.0
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: API_SERVER_PORT
          value: "8000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/status
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/status
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: api-server
  namespace: api-processor
spec:
  selector:
    app: api-server
  type: LoadBalancer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

**processor-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: processor
  namespace: api-processor
spec:
  replicas: 5  # Start with 5, scale based on load
  selector:
    matchLabels:
      app: processor
  template:
    metadata:
      labels:
        app: processor
    spec:
      containers:
      - name: processor
        image: your-registry/api-processor-worker:1.0
        env:
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: processor-hpa
  namespace: api-processor
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: processor
  minReplicas: 3
  maxReplicas: 25
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**handler-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: response-handler
  namespace: api-processor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: response-handler
  template:
    metadata:
      labels:
        app: response-handler
    spec:
      containers:
      - name: handler
        image: your-registry/api-processor-handler:1.0
        env:
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy Redis
kubectl apply -f redis-statefulset.yaml

# Deploy services (wait for Redis to be ready)
kubectl apply -f api-server-deployment.yaml
kubectl apply -f processor-deployment.yaml
kubectl apply -f handler-deployment.yaml

# Check status
kubectl get all -n api-processor

# View logs
kubectl logs -n api-processor -l app=api-server
kubectl logs -n api-processor -l app=processor
kubectl logs -n api-processor -l app=response-handler

# Port forward for testing
kubectl port-forward -n api-processor svc/api-server 8000:80
```

## Option 2: Docker Compose with Nginx

### docker-compose-prod.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api-server-1
      - api-server-2
      - api-server-3
    restart: always

  api-server-1:
    build: .
    command: python api_server.py
    environment:
      - REDIS_URL=redis://redis:6379/0
      - API_SERVER_PORT=8000
    depends_on:
      redis:
        condition: service_healthy
    restart: always

  api-server-2:
    build: .
    command: python api_server.py
    environment:
      - REDIS_URL=redis://redis:6379/0
      - API_SERVER_PORT=8000
    depends_on:
      redis:
        condition: service_healthy
    restart: always

  api-server-3:
    build: .
    command: python api_server.py
    environment:
      - REDIS_URL=redis://redis:6379/0
      - API_SERVER_PORT=8000
    depends_on:
      redis:
        condition: service_healthy
    restart: always

  processor-1:
    build: .
    command: python processor.py worker-1
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: always

  processor-2:
    build: .
    command: python processor.py worker-2
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: always

  processor-3:
    build: .
    command: python processor.py worker-3
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: always

  response-handler:
    build: .
    command: python response_handler.py
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: always

volumes:
  redis_data:
```

### nginx.conf

```nginx
upstream api_servers {
    server api-server-1:8000;
    server api-server-2:8000;
    server api-server-3:8000;
}

server {
    listen 80;
    server_name api-processor.example.com;

    location / {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Option 3: AWS Deployment

### Using AWS Services

```
ELB (Elastic Load Balancer)
  ↓
ECS Fargate (API Server tasks)
  ↓
ElastiCache (Redis)
  ↓
SQS (Message Queue)
  ↓
ECS Fargate (Processor tasks) - Auto-scaling
  ↓
SQS
  ↓
Lambda (Response Handler)
  ↓
RDS (Postgres for results)
```

### Deployment Steps

1. **Create ECR Repository:**
```bash
aws ecr create-repository --repository-name api-processor-server
aws ecr create-repository --repository-name api-processor-worker
```

2. **Build and Push Images:**
```bash
$(aws ecr get-login-token --region us-east-1 | docker login --username AWS --password-stdin)
docker build -t api-processor-server:latest .
docker tag api-processor-server:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/api-processor-server:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/api-processor-server:latest
```

3. **Create ElastiCache Cluster:**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id api-processor-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1
```

4. **Create ECS Task Definition:**
See AWS documentation for detailed task definition

## Monitoring & Logging

### Prometheus Metrics (Add to your code)

```python
from prometheus_client import Counter, Histogram, start_http_server

request_counter = Counter('requests_total', 'Total requests')
processing_duration = Histogram('processing_seconds', 'Processing time')

# Use in your code
request_counter.inc()
with processing_duration.time():
    # your code
    pass
```

### Logging to ELK Stack

```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("Request processed", extra={
    "request_id": request_id,
    "status": "success",
    "processing_time": elapsed
})
```

### Alerting

Set up alerts for:
- Queue depth > 1000
- Processing time > 5 minutes
- Error rate > 1%
- Processor pod restart > 3 times
- Redis connection failures

## Performance Tuning

### API Server
```python
# Use connection pooling
# Batch operations
# Add caching layer
```

### Processor
```python
# Parallel processing within worker
# Batch database writes
# Optimize resource usage
```

### Handler
```python
# Async webhooks
# Batch notifications
# Efficient database writes
```

## Scaling Guidelines

| Metric | Range | Action |
|--------|-------|--------|
| Queue Depth | < 100 | Normal |
| Queue Depth | 100-1000 | Monitor |
| Queue Depth | > 1000 | Scale up processors |
| Avg Processing | < 1s | Normal |
| Avg Processing | 1-5s | Optimize logic |
| Avg Processing | > 5s | Consider async steps |
| Error Rate | < 0.1% | Normal |
| Error Rate | > 0.1% | Investigate |

## Disaster Recovery

1. **Backup Strategy:** Regular Redis snapshots
2. **Replication:** Multi-region Redis
3. **Circuit Breaker:** Prevent cascading failures
4. **Dead Letter Queue:** Capture failed messages
5. **Graceful Shutdown:** Complete in-flight requests

## Security

- Use HTTPS for all APIs
- Implement rate limiting
- Add authentication/authorization
- Encrypt data at rest and in transit
- Use secrets management (Vault, AWS Secrets Manager)
- Implement request signing
- Regular security audits

## Cost Optimization

- Right-size container resources
- Use auto-scaling to match demand
- Optimize database queries
- Monitor data transfer costs
- Use spot instances where appropriate
