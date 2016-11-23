############
# database #
############

# start db
db-start:
	docker-compose -p dazzar -f docker/docker-compose.yml up -d --build dazzar_postgres
	docker-compose -p dazzar -f docker/docker-compose.yml up -d --build dazzar_rabbitmq

# stop db
db-stop:
	-docker stop dazzar_postgres
	-docker rm dazzar_postgres
	-docker stop dazzar_rabbitmq
	-docker rm dazzar_rabbitmq

# migrate database from models
db-migrate: build
	-docker run --rm --name dazzar_migrate --link dazzar_postgres --link dazzar_rabbitmq -v $$(pwd)/migrations:/migrations -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db migrate --directory /migrations
	sudo rm -rf migrations/__pycache__ migrations/versions/__pycache__
	sudo chown -R `stat . -c %u:%g` migrations/versions/*


# upgrade database on running postgres
db-upgrade: build
	docker run --rm --name dazzar_upgrade --link dazzar_postgres --link dazzar_rabbitmq -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db upgrade

# downgrade database on running postgres
db-downgrade: build
	docker run --rm --name dazzar_upgrade --link dazzar_postgres --link dazzar_rabbitmq -w /dazzar -e FLASK_APP=/dazzar/web/web_application.py dazzar_web flask db downgrade

###########
# General #
###########

# stop all running dockers
all-stop:
	-docker stop dazzar_web
	-docker rm dazzar_web
	-docker stop dazzar_bot
	-docker rm dazzar_bot
	-docker stop dazzar_postgres
	-docker rm dazzar_postgres
	-docker stop dazzar_rabbitmq
	-docker rm dazzar_rabbitmq

# start all
all-start:
	docker-compose -p dazzar -f docker/docker-compose.yml up -d --build

# start web prod
web-start:
	docker-compose -p dazzar -f docker/docker-compose.yml up -d --build dazzar_web

# start web prod
web-stop:
	-docker stop dazzar_web
	-docker rm dazzar_web

# start web dev
web-run:
	docker-compose -p dazzar -f docker/docker-compose.yml up --build dazzar_web

# start bot prod
bot-start:
	docker-compose -p dazzar -f docker/docker-compose.yml up -d --build dazzar_bot

# stop bot prod
bot-stop:
	-docker stop dazzar_bot
	-docker rm dazzar_bot

# start bot dev
bot-run:
	docker-compose -p dazzar -f docker/docker-compose.yml up --build dazzar_bot

# scripts
SCRIPT?=make_admin -i 76561197961298382
script: build
	docker run --rm --name dazzar_script --link dazzar_postgres --link dazzar_rabbitmq -w /dazzar dazzar_web python3 /dazzar/common/scripts.py $(SCRIPT)

# build
build:
	docker-compose -p dazzar -f docker/docker-compose.yml build

# clean docker images
clean:
	docker rm `docker ps -aq`
	docker rmi `docker images -aq`
