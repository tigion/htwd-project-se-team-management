# SE Team Management

A web application to manage teams, projects, roles and students.

Developed in and for the study course Software Engineering I+II at the HTW Dresden.
- Technologies: Django Python web framework, Docker

> [!WARNING]
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

- [Issue #2](https://github.com/tigion/htwd-project-se-team-management/issues/2): ModuleNotFoundError: No module named 'pandas' (18.08.2023)
- [Issue #3](https://github.com/tigion/htwd-project-se-team-management/issues/3): CommandError: You must use --email with --noinput (14.09.2023)
