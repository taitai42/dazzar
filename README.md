# Dazzar - Tool bazar for Dota

Website with tools for the French Dota 2 community. Some planned features are:

* [X] Logging with Steam for a unique account.
* [X] VIP Ladder system for 5K+ players, open 1 times per week.
* [X] Mix tool to find players to make new teams.
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

- `make web-start` - start the web image only, detached (prod).
- `make web-stop` - stop the web image only.
- `make web-run` - start the web image only, attached (debug).
- `make bot-start` - start the bot image only, attached (prod).
- `make bot-stop` - stop the bot image only.
- `make bot-run` - start the bot image only, attached (debug).
- `make script SCRIPT=SCRIPT_TO_RUN` - run the `SCRIPT_TO_RUN` defined in the `common/scripts.py` file.

## About configurations

Some configurations files are necessary to run the project. Because of secrets, they are not integrated into the depot. However, you can have a peek at the structure of such files watching their `*.example` counterpart. These files are `common/cfg/settings.cfg`, `docker/dazzar_postgres/conf.env` and `docker/dazzar_rabbitmq/conf.env`.

## Details

### Project structure

    .
    ├── bot                   # Files used inside the worker
    ├── common                # Sources shared between the worker and the web app
    ├── docker                # Docker files and compose
    ├── migrations            # Database migrations
    ├── web                   # Web sources
    ├── LICENSE
    ├── Makefile
    └── README.md

### Docker images

The project is composed of 4 docker images:

- `dazzar_postgres` - Postgres database used for persistence stuff, shared between the web part and the worker part.
- `dazzar_rabbitmq` - A queue to send jobs from the web platform to the workers.
- `dazzar_web` - Flask application managing the website.
- `dazzar_bot` - Image managing background tasks: bot manager, steam bots, tasks...

### Web

The web project is a classic Flask application, rendering views using Jinja2 templating. The project is connected to a database to store all infos but also to a queue to send background jobs to workers.

### Worker

The bot worker is managing a pool of steam bots to process background task (analyse profiles, create games, report results...).
