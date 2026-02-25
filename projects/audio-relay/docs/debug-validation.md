# Audio Relay Debug Validation Checklist

- [ ] Restart stack
  - `./projects/audio-relay/scripts/control.sh stop && ./projects/audio-relay/scripts/control.sh start`
- [ ] Speak a test phrase
- [ ] Confirm newest transcript exists
  - `python3 projects/audio-relay/scripts/inspect_latest_transcript.py`
- [ ] Confirm newest event exists
  - `ls -1t /tmp/audio-relay/events/*.json | head -n1`
- [ ] Main-app handoff dry run
  - `DRY_RUN=1 projects/audio-relay/scripts/forward_events_to_openclaw.sh`
- [ ] Main-app handoff live
  - `projects/audio-relay/scripts/forward_events_to_openclaw.sh`
- [ ] Confirm OpenClaw response in Telegram

## Expected debug mode behavior
- Worker emits events with `gate_passed` and `delivery.status`.
- Worker does not directly call OpenClaw (`AUDIO_RELAY_EVENT_ONLY=1`, `ROUTE_TO_OPENCLAW_AGENT=0`).
- Main app (or forwarder script) performs the only OpenClaw handoff.
