# Manual of the scripts

## The start/stop scripts

The start/stop scripts are used to start and stop the Docker environment easily.

> [!NOTE]
> Depending on the OS, the start/stop scripts need to be started with `sudo`.

### start.sh

Starts the Docker containers with `docker compose up -d`.

| Option        | Description                                                                                                                                                                    |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--build`     | Starts with newly build base images.<br />`docker compose build`<br />`docker compose up -d`                                                                                   |
| `--update`    | Starts with newly pulled and build base images.<br />`docker compose build --pull`<br />`docker compose up -d`                                                                 |
| `--reset`     | Starts with removed containers, images and networks and newly build ones.<br />`docker compose down --rmi all --remove-orphans`<br />`docker compose up -d`                    |
| `--reset-all` | Starts with removed containers, images, networks and volumes and newly build ones.<br />`docker compose down --rmi all --volumes --remove-orphans`<br />`docker compose up -d` |
| `--no-start`  | Runs the script with the given option without starting the Docker containers with `docker compose up -d` at the end.                                                           |

> [!IMPORTANT]
> Only one of the options `--build`, `--update`, `--reset` or `--reset-all` can
> be used as the first option.
>
> When `--no-start` is used, it must be the second option.

### stop.sh

Stops the Docker containers with `docker compose down`.
