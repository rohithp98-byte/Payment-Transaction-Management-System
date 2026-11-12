# SEZG583 — Payment Transaction Management System

A learning-only microservices demo using synthetic payment data. It does **not** connect to Visa or any real payment network.

## Architecture
- `payment-service` — FastAPI API, SQLite-owned payment records, simulated deterministic authorization.
- `transaction-service` — FastAPI API, separate SQLite-owned transaction records.
- Payment service calls transaction service over HTTP.
- Each service has its own Dockerfile and can be kept in a separate Git repository.
- Kubernetes manifests are under `deployment/k8s/`.

SQLite is used initially to keep Windows setup simple and reproducible. Each service owns its own separate database file. PostgreSQL can be a later extension.

## Prerequisites
1. Python 3.12+ installed on Windows 11.
2. Docker Desktop (needed for container and Minikube stages).
3. Git (optional, for repositories).

## Run locally on Windows
Open **two PowerShell windows** in this project directory.

### Terminal 1 — Transaction Service
```powershell
cd transaction-service
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:DB_PATH = "$PWD\transactions.db"
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

If PowerShell blocks activation, use:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Terminal 2 — Payment Service
```powershell
cd payment-service
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:DB_PATH = "$PWD\payments.db"
$env:TRANSACTION_SERVICE_URL = "http://127.0.0.1:8001"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open API docs:
- Payment: http://127.0.0.1:8000/docs
- Transactions: http://127.0.0.1:8001/docs

## Test with PowerShell
Create a synthetic payment:
```powershell
$body = @{
  merchant_id = "MERCHANT-1001"
  amount = "1500.00"
  currency = "INR"
  payment_method = "TEST_CARD"
  idempotency_key = "demo-payment-0001"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/payments" -ContentType "application/json" -Body $body
```

Retrieve payments (replace the ID with the response's payment_id):
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/payments/<PAYMENT_ID>"
```

List transactions:
```powershell
Invoke-RestMethod "http://127.0.0.1:8001/transactions"
```

The demo authorization is deterministic: an amount <= 10000 INR is approved; larger amounts are declined. This is just a classroom rule, not real fraud or payment logic. Use a new idempotency key for each new test. Reusing the same key returns the existing payment.

## Docker stage
Install Docker Desktop for Windows, start it, and confirm:
```powershell
docker version
docker compose version
```
Then, from the project root:
```powershell
docker compose up --build
```
This compose setup starts both application services. The starter app uses separate SQLite files inside containers; data persists only while the container filesystem persists. For durable data, add named volumes or PostgreSQL before treating this as anything beyond a demo.

## Minikube stage
Install `kubectl` and Minikube after Docker Desktop is running. From PowerShell, at the project root:
```powershell
minikube start --driver=docker
minikube image build -t payment-service:1.0 ./payment-service
minikube image build -t transaction-service:1.0 ./transaction-service
kubectl apply -f deployment/k8s/
kubectl get pods
kubectl get deployments
kubectl get services
minikube dashboard
```
Port-forward APIs in separate PowerShell windows:
```powershell
kubectl port-forward service/payment-service 8000:8000
kubectl port-forward service/transaction-service 8001:8001
```
Check health:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8001/health
```
Kubernetes uses `transaction-service:8001` for service-to-service calls. Note: this starter uses SQLite in each pod, so two replicas do **not** share data. For a proper scaled deployment, use PostgreSQL with persistent storage or another shared database strategy. The replica count is for demonstrating orchestration, not production data consistency.

## Suggested evidence for report
Capture real screenshots from your machine:
1. Both Swagger `/docs` pages.
2. A successful `POST /payments` and response.
3. Transaction list containing the created record.
4. `docker compose ps` and logs.
5. `kubectl get pods`, `kubectl get deployments`, `kubectl get services`.
6. Minikube dashboard deployments/pods.
7. Invalid request response and health endpoints.

## Safety
Only use fake merchant references and synthetic amounts. Do not use real PAN, CVV, cardholder data, Visa credentials, internal APIs, or production systems.
