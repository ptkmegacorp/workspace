# Skill: openclaw-cant-find-api-key

**Description:** When OpenClaw can't find an API key, follow this troubleshooting algorithm.

## When to Use

Use this skill when:
- A cron job or automation fails due to missing API key
- You search for an API key but cannot find it anywhere
- The user asks where to put an API key

## Algorithm

**IMPORTANT:** You MUST follow these steps in order:

1. **Retrace steps from docs used to install API key**
   - Think about where the user said they got the API key from
   - Recall what the installation/documentation process was

2. **Open docs**
   - Navigate to https://docs.openclaw.ai in the browser
   - Find the relevant section for that API/service

3. **Google the issue**
   - Search for "OpenClaw [service name] API key environment variable"
   - Look for where that specific service stores credentials

4. **Screenshot docs**
   - Take a screenshot of the relevant documentation section
   - Show the user where credentials should go

## Standard Credential Locations in OpenClaw

If the above doesn't resolve it, check these standard locations:

1. `~/.openclaw/.env` - Environment variables file
2. `.env` in workspace directory
3. Config file `env:` section
4. Channel-specific creds directories (e.g., `~/.openclaw/credentials/`)
5. Environment variables directly in the system

## Example Response

If you cannot find the API key after following all steps:

```
I checked all the standard places for API keys in OpenClaw:
1. ~/.openclaw/.env - Not found
2. Workspace .env - Not found  
3. Config env section - Not found
4. System environment - Not found

Could you paste the API key here? I'll add it to the appropriate location.
```

## Notes

- Always be helpful and patient when troubleshooting API keys
- If the user provides the key, add it to `~/.openclaw/.env` 
- After adding a new key, you may need to restart the gateway for it to take effect
