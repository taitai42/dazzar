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
    SQLAlchemy

ENV PYTHONPATH $PYTHONPATH:/dazzar
