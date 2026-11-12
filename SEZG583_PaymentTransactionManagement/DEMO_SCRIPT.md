# Genuine demo script (5–7 minutes)

Do not use pre-made fake screenshots. Run the application and capture the actual output.

1. Introduce the academic payment simulation; state clearly that it uses synthetic data only.
2. Show the architecture and separate service directories/repositories.
3. Start Transaction Service and Payment Service in separate terminals.
4. Open `http://127.0.0.1:8000/docs`; submit a synthetic payment with a new idempotency key.
5. Show the response containing `payment_id`, `transaction_id`, and simulated status.
6. Open `http://127.0.0.1:8001/docs`; list transactions and show the corresponding payment ID.
7. Repeat the same request with the same idempotency key to show duplicate protection.
8. Try an amount of `12000.00` with a fresh key to demonstrate the deterministic declined scenario.
9. In Docker stage, show `docker compose ps` and `docker compose logs --tail 30`.
10. In Minikube stage, show `kubectl get pods`, `kubectl get deployments`, `kubectl get services`, then open the dashboard.
11. End with limitations: authorization is simulated; SQLite per pod is a learning shortcut, not a scalable production database.

Suggested screenshots:
- `01-payment-swagger.png`
- `02-payment-created.png`
- `03-transaction-list.png`
- `04-docker-compose-ps.png`
- `05-kubectl-resources.png`
- `06-minikube-dashboard.png`

Windows recording options: use Snipping Tool screen recording or Xbox Game Bar (`Win+Alt+R`) if available. Verify that the saved video plays before submitting.
