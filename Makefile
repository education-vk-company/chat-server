MANAGE=server/manage.py
REQUIREMENTS=setup/requirements.txt
DOCKER_COMPOSE=setup/docker/docker-compose.yml

.PHONY: dev
dev:
	@uvicorn server.app.main:app --reload

.PHONY: install
install:
	@pip install --upgrade pip
	@pip install -r $(REQUIREMENTS)

.PHONY: lock
lock:
	@pip freeze > $(REQUIREMENTS)

.PHONY: pep
pep:
	@black server
	@isort server --multi-line 3 --profile black

.PHONY: superuser
superuser:
	@python $(MANAGE) createsuperuser

.PHONY: migrations
migrations:
	@python $(MANAGE) makemigrations

.PHONY: migrate
migrate:
	@python $(MANAGE) migrate

.PHONY: static
static:
	@python $(MANAGE) collectstatic --no-input

