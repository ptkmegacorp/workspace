# Always-On Mic Pause Detection Pipeline

## Overview
- Custom pipeline monitors a microphone stream to detect pauses, triggers OpenClaw commands, and delivers safe responses.
- The Debian host runs the core CLI/skill stack, but the user may operate remotely via Tailscale SSH clients and needs the pipeline to accept remote-session commands and context.
- The Ubuntu client toggles capture by double-pressing Control (start/stop) so each spoken message is bounded by paired presses before it posts to OpenClaw/Telegram.
- Components coordinate in sequence: capture audio, transcribe it, detect a pause, enforce safety, notify OpenClaw, and deliver a response.

## Implementation Steps
1. **Setup audio capture (hosted on Debian)** – Keep a low-latency recording loop with VAD, buffering, and noise suppression. Expose a socket, FIFO, or service so remote clients can stream or inspect the audio data (e.g., via socat, PipeWire, or a microservice).
2. **Transcribe segments (local or remote-triggered)** – Route each speech segment through a transcription engine (Fast Whisper, Whisper.cpp, Tone API, etc.). Make the service accessible over the Tailscale network so remote computers can push audio snippets or pull transcripts for UI overlays.
3. **Detect pause events (coordinating host + remote)** – Use VAD metadata plus timing heuristics to flag intentional pauses. Share pause state over Tailscale so whichever client initiated the speech knows when the pipeline will trigger OpenClaw.
4. **Trigger OpenClaw (Debian CLI)** – When a pause occurs, invoke `openclaw prompt` or a custom webhook from the Debian host, stamping in the transcript, metadata, and remote session ID if relevant. Guard with rate limits and a deduplication checker.
5. **Deliver response (text via chat, optionally voice)** – Capture OpenClaw’s reply and send it back through the Telegram/CLI channel. If the remote user wants voice, route the text to the remote machine via Tailscale for TTS playback.
6. **Apply safety controls (host-level enforcement)** – Content filters, override controls, logging, and human-in-the-loop confirmation steps run on the host before any external response leaves the pipeline.

## Required Components
- **Audio capture + sharing** – Local mic + VAD, buffering, optional microservice or socket accessible over Tailscale, remote client awareness of recording state.
- **Transcription** – Fast, low-latency, fallback to Whisper/FastWhisper, optionally running on the host but accessible via Tailscale API for remote clients.
- **Pause detection + orchestration** – Heuristics comparing VAD span vs. silence, event bus or HTTP webhook for remote clients to know when the pipeline fires.
- **OpenClaw trigger** – CLI (`openclaw prompt`) or HTTP API with session metadata; runs on Debian host with access to your skill and scripts, ensuring remote client commands funnel there.
- **Response delivery** – Standard OpenClaw channels (Telegram) plus optional Tailscale stream back to remote workstation for display/audio.
- **Safety controls** – Built-in filters, command confirmation, muted states, and logging centralized on the host before responses exit to remote clients.

## Pipeline Diagram
```
Remote Client (Tailscale SSH)
       |
       v
 Audio Capture Service (Debian) ---> Transcription Engine ---> Pause Detection ---> Safety Layer
       |                                         |                                         |
       +-----------------------------------------v-----------------------------------------+
                                         |
                                         v
                                OpenClaw Trigger (CLI/Skill)
                                         |
                                         v
                                 Response Delivery (Chat/TTS)
```