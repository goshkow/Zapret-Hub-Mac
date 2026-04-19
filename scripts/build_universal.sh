#!/bin/zsh
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <arm64_app_binary> <x64_app_binary> <output_binary>" >&2
  exit 1
fi

lipo -create "$1" "$2" -output "$3"

