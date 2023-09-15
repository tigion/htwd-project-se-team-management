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

1. Get the project:
    ```sh
    git clone ...
    ```

### Configuration

1. Go to the project folder:

    ```sh
    cd <project_folder>
    ```

2. Copy or rename the `.env.template` file to `.env`:
    ```sh
    cp .env.example .env
    ```

3. Edit the `.env` file:
    ```sh
    vim .env
    ```
    > **Warning**
    > The default configuration is for local testing only. Values must be adjusted for productive use!
    - 🚧 ... A more detailed description of the settings follows later in a separate document

### Run

1. Go to the project folder:
    ```sh
    cd <project_folder>
    ```

2. Start with:
    ```sh
    # Linux
    sudo docker compose up -d
    # macOS
    docker compose up -d
    ```

3. Stop with:
    ```sh
    # Linux
    sudo docker compose down
    # macOS
    docker compose down
    ```

### Update

- A simple variant:
  ```sh
  # Stop the Docker containers
  docker compose down
  # Update the project source
  git pull
  # Start the Docker containers
  sudo docker compose up -d
  ```

- A variant with reset Docker environment:
    ```sh
    # Stop the Docker containers and remove containers, images and networks
    # Can be run even if Docker has already been terminated
    docker compose down --rmi all --remove-orphans
    # Update the project source
    git pull
    # Start Docker with newly created containers, images and networks
    sudo docker compose up -d
    ```
    > **Warning**
    > With an additional `--volume` in `docker compose down --rmi all --volumes --remove-orphans` also volumes with important data will be removed!

### Deinstall

1. Go to the project folder:
    ```sh
    cd <project_folder>
    ```

2. Stop Docker with:
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

5. Remove project folder
   ```sh
   cd ..
   rm -rf <project_folder>
   ```

### Backup & Restore

Simply stop Docker and save or restore the configuration and data manually. Docker can then be restarted.
- **Configuration**: All settings are in the text file `.env`
- **Data**: All data are in the Sqlite database file `src/backend/db.sqlite3`

