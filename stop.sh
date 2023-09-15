#!/usr/bin/env bash
#
# Stop docker environment

# Need root for Linux
if [[ "$(uname -s)" == "Linux" && "$(id -u)" -ne 0 ]]; then
  printf "Please run this script as root:\nsudo %s\n" "$0" >&2
  exit 1
fi

# cd & check
if ! cd "$(dirname "$0")"; then exit; fi

docker compose down