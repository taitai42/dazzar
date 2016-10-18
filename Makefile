############
# Database #
############

# Create dabase persistence
/docker/dazzar_postgres:
	sudo mkdir -p $@

# Start db
db-start: /docker/dazzar_postgres
	docker-compose -f docker/docker-compose.yml up -d --build dazzar_postgres

# Stop db
db-stop:
	-docker stop dazzar_postgres
	-docker rm dazzar_postgres

# Migrate database from models
db-migrate: build
	mkdir -p /tmp/migrations
	rsync -av --delete migrations /tmp
	docker run --rm --name dazzar_migrate --link dazzar_postgres -v /tmp/migrations:/migrations -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db migrate --directory /migrations
	rsync -av --exclude __pycache__ /tmp/migrations .
	sudo chown -R `stat . -c %u:%g` migrations/versions/*
	sudo rm -rf /tmp/migrations

# Upgrade database on running postgres
db-upgrade: build
	docker run --rm --name dazzar_upgrade --link dazzar_postgres -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db upgrade

###########
# General #
###########

# Stop all running dockers
all-stop:
	-docker stop dazzar_postgres
	-docker rm dazzar_postgres
	-docker stop dazzar_upgrade
	-docker rm dazzar_upgrade
	-docker stop dazzar_migrate
	-docker rm dazzar_migrate
	-docker stop dazzar_web
	-docker rm dazzar_web
	-docker stop dazzar_bot
	-docker rm dazzar_bot

# Start all
all-start:
	docker-compose -f docker/docker-compose.yml up -d --build

# Start web
web-start:
	docker-compose -f docker/docker-compose.yml up --build dazzar_web

# Start bot
bot-start:
	docker-compose -f docker/docker-compose.yml up --build dazzar_bot

# Build
build:
	docker-compose -f docker/docker-compose.yml build
