# Dazzar - Tool bazar for Dota

Website with tools for the French Dota 2 community. Some planned features are:

* [X] Logging with Steam for a unique account.
* [ ] VIP Ladder system for 5K+ players, open 1 times per week.
* [ ] Mix tool to find players to make new teams.
* [ ] Managing tools to help teams organize training, scrims and tournaments.
* [ ] Pool of teams looking to scrim against each others.
* [ ] Social tools with news, comments, twitters, videos
* [ ] Tournament tools to help the community manage tournaments.

## Dependencies

- `Makefile`
- [Docker engine](https://www.docker.com/products/docker-engine) and [docker-compose](https://docs.docker.com/compose/)

## Commands

General commands

- `make build` - build the 4 docker images used
- `make all-start` - start the images detached (prod)
- `make all-stop` - stop the images if detached (prod)

Database commands

- `make db-start` - start the database and queue only, detached.
- `make db-stop` - stop the database and queue only, if started.
- `make db-migrate` - create the migrations if the models changed.
- `make db-upgrade` - apply the migrations to the database.

Other commands

- `make web-start` - start the web image only, attached (to debug).
- `make bot-start` - start the bot image only, attached (to debug).
- `make script SCRIPT=SCRIPT_TO_RUN` - run the `SCRIPT_TO_RUN` defined in the `common/scripts.py` file.

## About configurations

Some configuration files are cyphered using [transcrypt](https://github.com/elasticdog/transcrypt) and a secret key. However, you can have a peek at the structure of such files watching their `*.example` couterpardt. These files are `common/settings.cfg` and `docker/dazzar_postgres/conf.env`

## Project structure

The project is composed of 4 big components:

- `dazzar_postgres` - Postgres database used for persistence stuff, shared between the web part and the worker part.
- `dazzar_rabbitmq` - A queue to send jobs from the web platform to the workers.
- `dazzar_web` - Flask application managing the website.
- `dazzar_bot` - Image managing background tasks: bot manager, steam bots, tasks...
