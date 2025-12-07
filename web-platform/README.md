# Web-Platform

### 1. Install Node.js
- [ ] [Downoland Node.js](https://nodejs.org/en/download/prebuilt-installer)

```
node -v
npm -v
```

### 2. Install PostgreSQL
- [ ] [Downoland Postgresql](https://www.postgresql.org/download/)

## Environment Variables

In .env
```
secret_key='django-insecure-<your key>'

DB_NAME=<DB_NAME>
DB_USER=<DB_USER>
DB_PASSWORD=<DB_PASSWORD>
DB_HOST=<DB_HOST>
DB_PORT=<DB_PORT>
CELERY_BROKER_URL='amqp://guest:guest@localhost:5672//'
USE_CLOUD_STORAGE=False or True
```

If USE_CLOUD_STORAGE=True write: 

```
URL_STORAGE='URL_STORAGE'
ACCESS_KEY_ID='ACCESS_KEY_ID'
SECRET_ACCESS_KEY='SECRET_ACCESS_KEY'
BUCKET_NAME='BUCKET_NAME'
```

## Create Python Virtual Environment

```
python -m venv venv
venv\Scripts\activate
```

## Install Python & Node Dependencies

```
pip install -r requirements.txt
npm install
```

## Start the Backend (Django)

```
cd backend
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Start Celery

```
venv\Scripts\activate
cd backend
celery -A backend worker --loglevel=info
```

## Start the Frontend

```
cd ../frontend
npm run dev
```
