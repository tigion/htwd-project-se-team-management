# Notes - Production

- [Setup](#setup)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Run](#run)
  - [Update](#update)
  - [Deinstall](#deinstall)
  - [Backup \& Restore](#backup--restore)

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

### Run

1. Switches to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Starts the Docker containers with:

   ```sh
   # Linux
   sudo docker compose up -d

   # macOS
   docker compose up -d
   ```

3. Stops the Docker containers with:

   ```sh
   # Linux
   sudo docker compose down

   # macOS
   docker compose down
   ```

> [!NOTE]
> Depending on the OS, the docker commands need to be started with `sudo`.

### Update

#### A simple variant

1. Switch to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Stop the Docker containers:

   ```sh
   # Linux
   sudo docker compose down

   # macOS
   docker compose down
   ```

3. Update the project repository with the source code:

   ```sh
   git pull
   ```

4. Start the Docker containers:

   ```sh
   # Linux
   sudo docker compose up -d

   # macOS
   docker compose up -d
   ```

#### A variant with reset Docker environment

1. Stop the Docker containers and remove all containers, images and networks:

   ```sh
   # Linux
   sudo docker compose down --rmi all --remove-orphans

   # macOS
   docker compose down --rmi all --remove-orphans
   ```

   Can be run even if Docker has already been terminated.

   > [!WARNING]
   > With an additional `--volume` also volumes with important data will be
   > removed!

2. Update the project repository with the source code:

   ```sh
   git pull
   ```

3. Start Docker with newly created containers, images and networks:

   ```sh
   # Linux
   sudo docker compose up -d

   # macOS
   docker compose up -d
   ```

### Deinstall

1. Switch to the project folder:

   ```sh
   cd htwd-project-se-team-management
   ```

2. Stop the Docker containers:

   ```sh
   # Linux
   sudo docker compose down

   # macOS
   docker compose down
   ```

3. [optional] Save relevant data ([Backup \& Restore](#backup--restore))

4. Clean up Docker environment with:

   ```sh
   # Linux
   sudo docker compose down --rmi all --volumes --remove-orphans

   # macOS
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

### Backup & Restore

Simply stop Docker and save or restore the configuration and data manually.
Docker can then be restarted.

- **Configuration**: All settings are in the text file `.env`
- **Data**: All data are in the SQLite database file `src/backend/db.sqlite3`
