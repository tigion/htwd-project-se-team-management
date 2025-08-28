# Notes - Development

- [Setup](#setup)
  - [Initialize workspace](#initialize-workspace)
  - [Prepare Django project](#prepare-django-project)
  - [Start and stop the server](#start-and-stop-the-server)
- [Project](#project)
  - [Prepare for test or new version](#prepare-for-test-or-new-version)
  - [Logging](#logging)
- [Helpful things](#helpful-things)
  - [Python](#python)
    - [Virtual environment (venv)](#virtual-environment-venv)
    - [Save (working) pip packages in project venv](#save-working-pip-packages-in-project-venv)
  - [Django](#django)
    - [Reset Migrations](#reset-migrations)
    - [Generate a new SECRET_KEY](#generate-a-new-secret_key)
  - [SQLite](#sqlite)
    - [Backup \& Restore](#backup--restore)
  - [nginx](#nginx)
    - [Create self signed certificate](#create-self-signed-certificate)
  - [Docker](#docker)
    - [Inspect running Docker containers](#inspect-running-docker-containers)

## Setup

### Initialize workspace

```sh
# Clones the source code.
git clone https://github.com/tigion/htwd-project-se-team-management.git

# Switches to the project folder.
cd htwd-project-se-team-management

# Uses the default configuration (changes can be made).
cp .env.template .env

# Creates and activates the Python virtual environment.
python3 -m venv .venv
source .venv/bin/activate

# Installs the required Python packages.
pip3 install -r src/backend/requirements.txt
```

### Prepare Django project

```sh
# Switches to the source folder of the Django project.
cd src/backend/

# Detects and collects model changes.
python3 manage.py makemigrations

# Migrates collected model changes to the database.
python3 manage.py migrate

# Creates a superuser.
# He is used to log in as an admin (lecturer) and
# manages the projects and students
# - This is only needed for a new database.
# - It is part of the Docker compose.yaml.
python3 manage.py createsuperuser

# Collects and saves static files.
# - They are later delivered directly via nginx.
python3 manage.py collectstatic
```

### Start and stop the server

#### Django development server

```sh
# Start:
cd src/backend/
python3 manage.py runserver 0.0.0.0:8000

# URI: localhost:8000

# Stop: `CTRL+C`
```

#### Gunicorn server

```sh
# Start:
cd src/backend/
gunicorn config.wsgi:application -c gunicorn.conf.py

# URI: localhost:8000

# Stop: `CTRL+C`
```

#### Docker compose

```sh
# Start (in the root folder of the project):
docker compose up -d

# URI: localhost

# Stop:
docker compose down
```

Depending on the OS, the docker commands need to be started with `sudo`.

## Project

### Prepare for test or new version

1. Remove sensitive data or outsource them to the .env file.
2. Prepare the Django project:

   ```sh
   python3 manage.py makemigrations
   python3 manage.py migrate
   python3 manage.py collectstatic
   ```

3. Test the project.
4. Freeze (working) pip package versions:

   ```sh
   pip freeze -l > requirements.freeze.txt
   ```

### Prepare for production

1. Use the [Deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/):

   ```sh
   python3 manage.py check --deploy
   ```

2. Check the [Prepare for test or new version](#prepare-for-test-or-new-version) section.
3. Use the frozen versions of the working pip packages:

   ```sh
   cp requirements.txt requirements.dev.txt
   cp requirements.freeze.txt requirements.txt
   ```

### Logging

When the project is running with Docker, log files from Django and nginx are
stored under:

- `docker/logs/django/`: _django.log_
- `docker/logs/nginx/`: _access.log_, _error.log_

## Helpful things

### Python

#### Virtual environment (venv)

```sh
# Create
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install pip packages
pip3 install -r requirements.txt

# Update pip packages in venv only
pip freeze --require-virtualenv | cut -d'=' -f1 | xargs -n1 pip install -U

# Deactivate
deactivate

# Remove
deactivate
rm -rf .venv
```

#### Save (working) pip packages in project venv

```sh
pip freeze -l > requirements.freeze.txt
```

### Django

#### Reset Migrations

> [!WARNING]
> This will delete the database! Relevant data must be backed up.

```sh
rm db.sqlite3
rm app/migrations/00*.py
rm poll/migrations/00*.py
rm team/migrations/00*.py
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py createsuperuser
```

#### Generate a new SECRET_KEY

```sh
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### SQLite

#### Backup & Restore

```sh
# Backups all tables.
sqlite3 db.sqlite3
sqlite> .output db_dump_all.sql
sqlite> .dump
sqlite> .exit

# Backups the table <table>.
sqlite3 db.sqlite3
sqlite> .output db_dump_<table>.sql
sqlite> .dump <table>
sqlite> .exit

# Restores the table <table>.
sqlite3 db.sqlite3
.read db_dump_<table>.sql
.exit
```

### nginx

#### Create self signed certificate

```sh
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout localhost.key -out localhost.crt
```

### Docker

#### Inspect running Docker containers

```sh
docker ps
docker exec -it <Container-ID or Name> /bin/sh
```
