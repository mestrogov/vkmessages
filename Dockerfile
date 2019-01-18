FROM python:3.7.2-alpine3.8
MAINTAINER Yaroslav <hello@unimarijo.com>
ENV INSTALL_PATH /data

COPY . $INSTALL_PATH
WORKDIR $INSTALL_PATH

RUN apk add --update build-base
RUN pip install -r requirements/requirements.txt

CMD python run.py
