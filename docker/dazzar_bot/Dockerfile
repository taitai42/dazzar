FROM debian

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install \
    git-core \
    python3-pip \
    libpq-dev \
    libffi-dev

RUN pip3 install \
    psycopg2 \
    SQLAlchemy \
    tornado \
    Flask \
    Flask-Migrate \
    Flask-SQLAlchemy \
    Flask-OpenID \
    Flask-Login \
    Flask-Script \
    pika
RUN pip3 install git+https://github.com/ValvePython/dota2

ENV PYTHONPATH $PYTHONPATH:/dazzar

COPY . /dazzar/
