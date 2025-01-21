.PHONY: help env up down restart deploy build logs ps migrate makemigrations superuser shell dbshell

help:
	@echo "make env            - create .env from .env.example (won't overwrite an existing one)"
	@echo "make up             - start the stack"
	@echo "make down           - stop the stack"
	@echo "make restart        - restart all containers"
	@echo "make deploy         - git pull + rebuild + rolling recreate, no full-stack downtime"
	@echo "make build          - rebuild backend image"
	@echo "make logs           - tail logs for all services"
	@echo "make ps             - show container status"
	@echo "make migrate        - apply Django migrations"
	@echo "make makemigrations - generate Django migrations"
	@echo "make superuser      - create a Django admin superuser"
	@echo "make shell          - open a Django shell"
	@echo "make dbshell        - open a psql shell on the postgres container"

env:
	cp -n .env.example .env

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

deploy:
	git pull
	docker compose build
	docker compose up -d --remove-orphans

build:
	docker compose build

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

migrate:
	docker compose run --rm django python manage.py migrate

makemigrations:
	docker compose run --rm django python manage.py makemigrations

superuser:
	docker compose run --rm django python manage.py createsuperuser

shell:
	docker compose run --rm django python manage.py shell

dbshell:
	docker compose exec postgres psql -U $${POSTGRES_USER:-messenger} -d $${POSTGRES_DB:-messenger}
