# SE Team Management

A web application to manage teams, projects, roles and students.

Developed in and for the study course Software Engineering I+II at the HTW Dresden.
- Technologies: Django Python web framework, Docker

> **Warning**
> Work in progress. Not yet fully tested. Use at your own risk.

- [Features](#features)
- [Todo](#todo)
- [Setup](#setup)
- [Use](#use)
- [Known bugs](#known-bugs)


## Features

- Manage projects, roles and students
- Use of polls for project and role wishes
- Generate teams based on the polls
  - The current algorithm is based on a student project "I7 Teamverwaltung 202209" and uses the Google OR-Tools.
- Authentication of students against the university LDAP

## Todo

- 🚧 ... Yes exist ... more later


## Setup

1. Clone or download the project
2. Copy the `.env.template` to a new file with the name `.env` and make needed settings
3. Start with `docker compose up -d` (stop with `docker compose down`)

More detailed instructions can be found at:
- [📘 Notes - Production](docs/notes_production.md)
- [📕 Notes - Development](docs/notes_development.md)

## Use

- 🚧 ... Follows later in a separate document


## Known bugs

- **Python package**: ortools 9.7 (18.08.2023)
  - `ModuleNotFoundError: No module named 'pandas'`
  - Solution in comming 9.8 ([Source](https://github.com/google/or-tools/issues/3889))
  - [workaround]:
    - Use Version 9.6.2534 in requirements.txt: `ortools==9.6.2534`

- **Python package**: django 4.2.5 (14.09.2023)
  - `CommandError: You must use --email with --noinput.`
  - The `createsuperuser --noinput` command does not accept an empty email.
    - `python manage.py createsuperuser --noinput`
  - It is fixed in the main branch, but not released yet. ([Source](https://code.djangoproject.com/ticket/34542))
  - [workaround]:
    - `python manage.py createsuperuser --noinput --email "no@need.email"`