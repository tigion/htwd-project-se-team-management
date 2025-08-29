# Notes - Production

- [Setup](#setup)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Run](#run)
- [Update](#update)
- [Deinstall](#deinstall)
- [Backup \& Restore](#backup--restore)
- [The start/stop scripts](#the-startstop-scripts)

## Setup

### Requirements

- Docker, Git

### Installation

1. Gets the project:

   ```sh
   git clone https://github.com/tigion/htwd-project-se-team-management.git
   ```

### Configuration

1. Goes to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Makes a working copy of the example environment configuration:

   ```sh
   cp .env.example .env
   ```

3. Edits the environment configuration (or use another editor):

   ```sh
   vim .env
   ```

   > [!WARNING]
   > The default configuration is for local testing only. Values must be
   > adjusted for productive use!
   - 🚧 ... A more detailed description of the settings follows later.

## Run

1. Switches to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Starts the Docker containers with:

   ```sh
   ./start.sh
   # or
   docker compose up -d
   ```

3. Stops the Docker containers with:

   ```sh
   ./stop.sh
   # or
   docker compose down
   ```

> [!NOTE]
> Depending on the OS, the Docker commands or the start/stop scripts need to be
> started with `sudo`.
>
> Infos about the start/stop scripts can be found
> [here](manual_scripts.md).

## Update

### A simple variant

1. Switch to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Stop the Docker containers:

   ```sh
   ./stop.sh
   # or
   docker compose down
   ```

3. Update the project repository with the source code:

   ```sh
   git pull
   ```

4. Start the Docker containers:

   ```sh
   ./start.sh
   # or
   docker compose up -d
   ```

### A variant with reset Docker environment

1. Stop the Docker containers and remove all containers, images and networks:

   ```sh
   ./stop.sh
   # or
   docker compose down
   ```

2. [optional] Save relevant data ([Backup \& Restore](#backup--restore))

3. Update the project repository with the source code:

   ```sh
   git pull
   ```

4. Removes all containers, images and networks and starts Docker with newly
   created ones:

   ```sh
   ./start.sh --reset
   # or
   docker compose down --rmi all --remove-orphans
   ```

   > [!WARNING]
   > With an `--reset-all` or `--volumes` also volumes with important data will
   > be removed and new ones created.
   >
   > - `./start.sh --reset-all`
   > - `docker compose down --rmi all --volumes --remove-orphans`

## Deinstall

1. Switch to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Stop the Docker containers:

   ```sh
   ./stop.sh
   # or
   docker compose down
   ```

3. [optional] Save relevant data ([Backup \& Restore](#backup--restore))

4. Clean up Docker environment with:

   > [!WARNING]
   > This removes all containers, images, networks and volumes!

   ```sh
   ./start.sh --reset-all --no-start
   # or
   docker compose down --rmi all --volumes --remove-orphans
   ```

5. Switch out of the project folder one level up:

   ```sh
   cd ..
   ```

6. Remove the project folder:

   ```sh
   rm -rf htwd-project-se-team-management
   ```

## Backup & Restore

Simply stop Docker and save or restore the configuration and data manually.
Docker can then be restarted.

- **Configuration**: All settings are in the text file `.env`
- **Data**: All data are in the SQLite database file `src/backend/db.sqlite3`
