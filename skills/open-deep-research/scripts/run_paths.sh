#!/usr/bin/env bash
set -euo pipefail

python3 -m open_deep_research.cli research --stdin --format paths "$@"
