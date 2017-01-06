FROM debian

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install wget tar python-pip python-dev build-essential sed uwsgi uwsgi-plugin-python
RUN pip install uwsgi

RUN wget http://static.moinmo.in/files/moin-1.9.9.tar.gz
RUN tar xvzf moin-1.9.9.tar.gz
RUN cd moin-1.9.9 && python setup.py install --force --record=install.log
RUN cp /usr/local/share/moin/server/moin.wsgi /usr/local/share/moin/moin.wsgi
RUN cp /usr/local/share/moin/config/wikiconfig.py /usr/local/share/moin/wikiconfig.py
RUN sed -i "21isys.path.insert(0, '/usr/local/share/moin/')" /usr/local/share/moin/moin.wsgi
