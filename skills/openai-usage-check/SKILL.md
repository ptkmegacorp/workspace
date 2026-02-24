---
name: openai-usage-check
description: Reports OpenAI usage by running scripts/check-openai-usage.sh whenever the user asks to check OpenAI usage or model status.
---

## How to use this skill
1. Run the included script: `scripts/check-openai-usage.sh`.
2. Copy its output and return it to the user.

The script internally runs `openclaw models status --agent main` to gather the necessary data before reporting usage.
