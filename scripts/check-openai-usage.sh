#!/usr/bin/env bash
set -euo pipefail

openclaw models status --agent main | awk '/openai-codex usage/{print; if(getline){print}}'
