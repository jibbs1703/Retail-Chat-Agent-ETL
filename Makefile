.PHONY: add commit push secret-key fernet-key lint clear clear-ruff clear-pytest clear-pycache  ingestion-build  ingestion-init  ingestion-up  ingestion-up-flower  ingestion-down  ingestion-restart  ingestion-clean  ingestion-reset  ingestion-health  ingestion-scale-workers

add:
	git add .

commit: add
	git commit -m "$(msg)"

push: commit
	git push

lint:
	python3 -m ruff format .
	python3 -m ruff check .

clear-pycache:
	find . -type d -name '__pycache__' -exec rm -rf {} +

clear-ruff: clear-pycache
	find . -type d -name '.ruff_cache' -exec rm -rf {} +

clear-pytest: clear-ruff
	find . -type d -name '.pytest_cache' -exec rm -rf {} +

clear: clear-pytest
	clear

secret-key:
	python -c "import secrets; print(secrets.token_hex(32))"

fernet-key:
	python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

ingestion-build:
	docker build -f docker/Dockerfile -t retail-chat-airflow:latest .

 ingestion-init:
	docker-compose -f docker-compose.yaml up airflow-init

 ingestion-up:  ingestion-init
	docker-compose -f docker-compose.yaml up -d

 ingestion-up-flower:  ingestion-init
	docker-compose -f docker-compose.yaml --profile flower up -d

 ingestion-down:
	docker-compose -f docker-compose.yaml down

 ingestion-restart:  ingestion-down  ingestion-up

 ingestion-clean:
	docker-compose -f docker-compose.yaml down -v --remove-orphans
	rm -rf ./logs/*
	docker system prune -af --volumes
	docker image prune -af
	docker volume prune -af

 ingestion-reset:  ingestion-clean  ingestion-init  ingestion-up
