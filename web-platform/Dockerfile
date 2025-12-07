FROM node:23-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN chmod -R 755 /app/frontend/node_modules/.bin
RUN npm run build

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    nginx \
    postgresql \         
    postgresql-contrib \
    redis-server \         
    rabbitmq-server \     
    nodejs \
    npm \
    supervisor \
    openssl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app /var/log/supervisor /etc/ssl/mycerts

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install celery

RUN su postgres -c "/usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data"

RUN rabbitmq-plugins enable rabbitmq_management

COPY --from=frontend-builder /app/frontend /app/frontend
COPY backend/ /app/backend/
COPY .env /app/.env

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/mycerts/server.key \
    -out /etc/ssl/mycerts/server.crt \
    -subj '/C=RU/ST=Moscow/L=Moscow/O=Company/CN=localhost'

RUN chmod +x /app/backend/docker/entrypoint.sh

RUN echo '#!/bin/bash\n\
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf' > /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app
EXPOSE 80 443 4864 6448

CMD ["/app/start.sh"]