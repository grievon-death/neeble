FROM python:3.10-alpine

RUN apk add --update bash
RUN apk add --update python3
RUN apk add --update mariadb-dev
RUN apk add --update re2
RUN apk add --update re2-dev
RUN apk add --update git
RUN apk add --update make
RUN apk add --no-cache --virtual .build-deps python3-dev build-base linux-headers gcc
RUN pip3 install --upgrade pip

COPY . .

RUN pip install -r requirements/common.txt
