FROM debian

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install \
    python3-pip \
    libpq-dev \
    libffi-dev \
    git-core \
    locales
RUN pip3 install \
    tornado \
    psycopg2 \
    Flask \
    Flask-Markdown \
    Flask-Migrate \
    Flask-SQLAlchemy \
    SQLAlchemy \
    Flask-OpenID \
    Flask-Login \
    Flask-Script \
    pika \
    pytz
RUN echo 'fr_FR.UTF-8 UTF-8' > /etc/locale.gen && locale-gen

RUN pip3 install git+https://github.com/Philaeux/dota2@chat

ENV PYTHONPATH $PYTHONPATH:/dazzar
COPY . /dazzar/
