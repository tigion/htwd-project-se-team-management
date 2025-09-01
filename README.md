# SE Team Management

A web application to manage projects and students and generate teams.

Developed in and for the study course Software Engineering I+II at the [HTW Dresden].

[HTW Dresden]: https://www.htw-dresden.de/

> [!WARNING]
> Work in progress. Features can change.
> Not yet fully tested. Use at your own risk.

> [!NOTE]
> `2025-08-20`: Version with roles is archived in the branch `archive/v1`.
>
> `2023-09-15`: The original implementation with the OR-Tools is based on the
> earlier student project "I7 Team Management" from 2022-09.

- [Features](#features)
- [Technologies](#technologies)
- [Setup](#setup)
- [Use](#use)
- [Known bugs](#known-bugs)
- [Todo](#todo)

## Features

- Manages projects and students.
  - Projects can have multiple instances.
  - Imports students from a CSV file.
- Uses surveys (polls) for project wishes.
- Generates teams based on the polls.
  - Uses the [OR-Tools] to assign students to projects in the best possible way.
  - Shows student happiness and scores for the generated teams.
- Shows a statistics overview.
- Authenticates students to the university LDAP.
- Backups the database file.

## Technologies

- [Django] Python web framework for backend and frontend
- [OR-Tools] optimization library
- [Bootstrap] frontend toolkit
- [SQLite] database
- [Docker], [nginx]

[Django]: https://www.djangoproject.com/
[OR-Tools]: https://developers.google.com/optimization
[Bootstrap]: https://getbootstrap.com/
[SQLite]: https://www.sqlite.org/
[Docker]: https://www.docker.com/
[nginx]: https://www.nginx.com/

## Setup

1. Clone or download the project and switch to it.
2. Copy the `.env.template` to a new file with the name `.env` and make needed
   configuration changes.
3. Start with `docker compose up -d` and stop with `docker compose down`.

More detailed instructions can be found at:

- [📘 Notes - Production](docs/notes_production.md)
- [📕 Notes - Development](docs/notes_development.md)

## Use

- 🚧 ... Follows later in a separate document

## Known bugs

- `2025-09-01`: [Issue #4](https://github.com/tigion/htwd-project-se-team-management/issues/4):
  Field error messages are not displayed correctly
- `2023-09-14`: ~~[Issue
  #3](https://github.com/tigion/htwd-project-se-team-management/issues/3):
  CommandError: You must use --email with --noinput~~
- `2023-08-18`: ~~[Issue
  #2](https://github.com/tigion/htwd-project-se-team-management/issues/2):
  ModuleNotFoundError: No module named 'pandas'~~

## Todo

- 🚧 ... Currently in another place.
