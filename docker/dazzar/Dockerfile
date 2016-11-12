FROM debian

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install \
    python3-pip \
    libpq-dev \
    libffi-dev \
    git-core
RUN pip3 install \
    tornado \
    psycopg2 \
    Flask \
    Flask-Migrate \
    Flask-SQLAlchemy \
    SQLAlchemy \
    Flask-OpenID \
    Flask-Login \
    Flask-Script \
    pika \
    git+https://github.com/ValvePython/steam \
    git+https://github.com/ValvePython/dota2

ENV PYTHONPATH $PYTHONPATH:/dazzar

COPY . /dazzar/
