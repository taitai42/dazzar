##############
# Deployment #
##############

deploy:
	sudo mkdir -p /docker/dazzar_web
	sudo mkdir -p /docker/dazzar_postgres
	sudo rsync -av --delete --exclude .git --exclude .idea . /docker/dazzar_web

############
# Database #
############

# Start db
db-start: deploy
	-docker stop dazzar_postgres
	-docker rm dazzar_postgres
	docker-compose -f docker/docker-compose.yml up -d --build dazzar_postgres

# Migrate database from models
db-migrate: build deploy
	docker run --rm --name dazzar_migrate --link dazzar_postgres -v /docker/dazzar_web:/dazzar -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db migrate
	rsync -av /docker/dazzar_web/migrations/versions $$(pwd)/migrations
	cd migrations/versions && chown -R `stat . -c %u:%g` *
	rm -rf migrations/versions/__pycache__

# Upgrade database on running postgres
db-upgrade: build deploy
	docker run --rm --name dazzar_upgrade --link dazzar_postgres -v /docker/dazzar_web:/dazzar -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db upgrade

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
all-start: db-start
	docker-compose -f docker/docker-compose.yml up -d dazzar_web

# Start web
web-start: build deploy
	docker-compose -f docker/docker-compose.yml up dazzar_web

# Start bot
bot-start: build deploy
	docker-compose -f docker/docker-compose.yml up -d dazzar_bot

# Build
build:
	docker-compose -f docker/docker-compose.yml build
