FROM debian

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update
RUN apt-get -y install \
    python3-pip \
    libpq-dev

RUN pip3 install \
    tornado \
    psycopg2 \
    Flask \
    Flask-Migrate \
    Flask-SQLAlchemy \
    SQLAlchemy \
    Flask-OpenID \
    Flask-Login

RUN mkdir -p /dazzar
ENV PYTHONPATH $PYTHONPATH:/dazzar

COPY migrations /dazzar/migrations
COPY common /dazzar/common
COPY web /dazzar/web
