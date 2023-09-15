#!/usr/bin/env bash
#
# Start docker environment
#
# Options (first only):
#   --build     ... start with new build images
#   --update    ... start with updated base images
#   --reset     ... fresh start with removed containers, images and networks
#   --reset-all ... fresh start with removed containers, images, networks and volumes
# Options (second only):
#   --no-start  ... run script with no Docker start

# Clean up notes:
# sudo docker system prune --all
# sudo docker system prune --all --volumes

# cd & check
if ! cd "$(dirname "$0")"; then exit; fi

# Need root for Linux
if [[ "$(uname -s)" == "Linux" && "$(id -u)" -ne 0 ]]; then
  printf "Please run this script as root\nsudo %s\n" "$0" >&2
  exit 1
fi

# Remove containers, images, networks and
# with argument 'all' also volumes
reset() {
  echo "This removes containers, images and networks!"
  [[ $1 == "all" ]] && echo "This also removes volumes. Important data can be lost!"

  read -p "Are you sure you want to continue? [y/N] " -r -n 1 answer
  echo ""
  [[ "$answer" != "y" && "$answer" != "Y" ]] && exit 0

  if [[ $1 == "all" ]]; then
    docker compose down --rmi all --volumes --remove-orphans
  else
    docker compose down --rmi all --remove-orphans
  fi
}

# Parse script options
if [[ "$1" == "--build" ]]; then
  # Build images
  docker compose build
elif [[ "$1" == "--update" ]]; then
  # Pull newer images and build images
  docker compose build --pull
elif [[ "$1" == "--reset" ]]; then
  # Remove containers, images and networks
  reset
elif [[ "$1" == "--reset-all" ]]; then
  # Remove containers, images, networks and volumes
  reset all
fi

# Exit without start
[[ "$2" == "--no-start" ]] && exit 0

# Start docker environment
docker compose up -d