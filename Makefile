.PHONY: up down test load metrics evidence psp-slow
up:
	docker compose up -d --build
down:
	docker compose down -v
test:
	docker compose run --rm api python3 /app/tests.py
load:
	docker compose exec -T api python3 /app/loadgen.py
metrics:
	curl -s http://localhost:58004/metrics
evidence:
	curl -s http://localhost:58004/evidence
psp-slow:
	curl -s -X POST http://localhost:58003/_control -H 'content-type: application/json' -d '{"latency_ms":500}'

