# Notes - Development

- [Setup](#setup)
  - [Init workspace](#init-workspace)
  - [Prepare Django project](#prepare-django-project)
  - [Start and stop the server](#start-and-stop-the-server)
- [Project](#project)
  - [Prepare for test or new git version](#prepare-for-test-or-new-git-version)
  - [Logging](#logging)
- [Helpful things](#helpful-things)
  - [Python](#python)
    - [Virtual environment (venv)](#virtual-environment-venv)
    - [Save (working) pip packages in project venv](#save-working-pip-packages-in-project-venv)
  - [Django](#django)
    - [Reset Migrations](#reset-migrations)
    - [Generate a new SECRET\_KEY](#generate-a-new-secret_key)
  - [Sqlite](#sqlite)
    - [Backup \& Restore](#backup--restore)
  - [nginx](#nginx)
    - [Create self signed certificate](#create-self-signed-certificate)
  - [Docker](#docker)
    - [Inspect running Docker containers](#inspect-running-docker-containers)


## Setup

### Init workspace

```sh
# Clone the source code
git clone <project_git_repository>

# Switch to project folder
cd <project_folder>

# Use default config (or change something)
cp .env.template .env

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required Python packages
pip3 install -r src/backend/requirements.txt
```

### Prepare Django project

```sh
# detect and collect model changes
python3 manage.py makemigrations

# migrate collected model changes to database
python3 manage.py migrate

# create superuser
# - Only needed for new database
# - Is part in the Docker compose.yaml
python3 manage.py createsuperuser

# collect and save static files
# - They are later delivered directly via nginx
python3 manage.py collectstatic
```

### Start and stop the server

- **Django development server**:
    ```sh
    # - URI: localhost:8000
    # Start
    cd <project_folder>/src/backend/
    python3 manage.py runserver 0.0.0.0:8000
    # Stop: CTRL+C
    ```

- **Gunicorn server**:
    ```sh
    # - URI: localhost:8000
    cd <project_folder>/src/backend/
    gunicorn config.wsgi:application -c gunicorn.conf.py
    # Stop: CTRL+C
    ```

- **Docker**:
    ```sh
    # - URI: localhost
    cd <project_folder>/
    (sudo) docker compose up -d
    # Stop
    (sudo) docker compose down
    ```

## Project

### Prepare for test or new git version

1. Remove sensitive data or outsource them to the .env file.
2. Prepare Django project:
    ```sh
    python3 manage.py makemigrations
    python3 manage.py migrate
    python3 manage.py collectstatic
    ```
3. Test the project
4. Freeze (working) pip package versions:
    ```sh
    pip freeze -l > requirments.freeze.txt
    ```

> [!WARNING]
> For final deployment use the [Deployment checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/):
>
> `python3 manage.py check --deploy`.

### Logging

When the project is running with Docker, log files from Django and nginx are stored under:
- `docker/logs/django/`: *django.log*
- `docker/logs/nginx/`: *access.log*, *error.log*

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
pip freeze -l > requirments.freeze.txt
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

### Sqlite

#### Backup & Restore

```sh
# Backup all tables
sqlite3 db.sqlite3
sqlite> .output db_dump_all.sql
sqlite> .dump
sqlite> .exit

# Backup table <table>
sqlite3 db.sqlite3
sqlite> .output db_dump_<table>.sql
sqlite> .dump <table>
sqlite> .exit

# Restore table: <table>
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
