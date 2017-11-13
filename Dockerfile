FROM jfloff/alpine-python:latest
MAINTAINER Mark Heppner <mheppner@users.noreply.github.com>

ENV BASE_DIR=/app

RUN mkdir -p $BASE_DIR /static
WORKDIR $BASE_DIR
ADD ./ ./

RUN apk add --no-cache nginx libmemcached-dev zlib-dev cyrus-sasl-dev \
    && apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
                                       postgresql-dev postgresql \
    && pip install --no-cache-dir -r requirements/common.txt \
                                  -r requirements/prod.txt \
    && cp deploy/nginx.conf /etc/nginx/conf.d/default.conf \
    && mkdir -p /run/nginx \
    && ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log \
    && touch .env \
    && echo 'STATIC_ROOT=/static' > .env \
    && python -m compileall -q . \
    && SECRET_KEY=temp python src/manage.py collectstatic --noinput

EXPOSE 80

CMD ["circusd", "/app/deploy/circus.ini"]
