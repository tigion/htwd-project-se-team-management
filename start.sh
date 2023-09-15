#!/usr/bin/env bash
#
# Start docker environment
#
# Options:
#   --build|-b  ... start with new build images
#   --update|-u ... start with updated base images
#   --reset|-r  ... fresh start with removed containers, images and networks
#   --reset-all ... fresh start with removed containers, images, networks and volumes

# Clean up notes:
# sudo docker system prune --all
# sudo docker system prune --all --volumes

# Need root for Linux
if [[ "$(uname -s)" == "Linux" && "$(id -u)" -ne 0 ]]; then
  print "Please run this script as root\nsudo %s\n" "$0" >&2
  exit 1
fi

# cd & check
if ! cd "$(dirname "$0")"; then exit; fi

if [[ "$1" == "--build" || "$1" == "-b" ]]; then
  # build images
  docker compose build
elif [[ "$1" == "--update" || "$1" == "-u" ]]; then
  # pull newer images and build images
  docker compose build --pull
elif [[ "$1" == "--reset" || "$1" == "-r" ]]; then
  echo "This removes containers, images and networks!"
  read -p "Are you sure you want to continue? [y/N] " -r -n 1 answer
  echo ""
  if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    # remove containers, images and networks
    docker compose down --rmi all --remove-orphans
  fi
elif [[ "$1" == "--reset-all" ]]; then
  echo "This removes containers, images and networks!"
  echo "This also removes volumes. Important data can be lost!"
  read -p "Are you sure you want to continue? [y/N] " -r -n 1 answer
  echo ""
  if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    # remove containers, images, networks and volumes
    docker compose down --rmi all --volumes --remove-orphans
  fi
fi

# start docker environment
docker compose up -d