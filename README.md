# Voice Interface with Pipecat

## Overview

This project is a real‑time voice interaction system using **Pipecat**, **WebRTC over WebSocket**, **Groq LLM**, **Cartesia TTS**, and **Deepgram STT**. The frontend (`index.html`) connects to a Python WebSocket server (`main.py`) enabling full duplex speech‑to‑LLM‑to‑speech conversation with low latency.

## Features

* Live microphone streaming with adjustable buffer size
* Real‑time STT → LLM → TTS response pipeline
* Volume meter + noise reduction + gain + echo cancel controls
* Timeout auto‑hangup with graceful TTS farewell
* Configurable via `.env` environment secrets

## Tech Stack

* **Frontend:** Vanilla JS + Web Audio API + Protobuf over WebSocket
* **Backend:** Python + Pipecat pipeline (asyncio)
* **LLM:** Groq (default) or OpenAI (switchable)
* **STT:** Deepgram
* **TTS:** Cartesia (default), Deepgram or Google optional

## Project Structure

```
├── index.html   # Frontend voice UI
├── main.py      # WebSocket pipeline server
├── req.txt      # Python dependencies
├── .env         # API keys and credentials
```

## Setup Instructions

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or venv\\Scripts\\activate
pip install -r req.txt
```

### 2. Create `.env` file

Required keys (example):

```
GROQ_API_KEY=...
CARTESIA_API_KEY=...
DEEPGRAM_API_KEY=...
OPENAI_API_KEY=...  # optional
```

### 3. Run WebSocket Backend

```bash
python main.py
```

### 4. Launch Frontend

Open **index.html** in Chrome (HTTPS or localhost only — mic permission needed).

## Usage

1. Wait for status → "Ready!"
2. Click **Start Conversation**
3. Speak — live bot reply via TTS
4. Click **End Conversation** or let session timeout (auto TTS farewell)

## Switching LLM or TTS

`main.py` contains commented alternatives — simply uncomment your desired service:

```python
# llm = OpenAILLMService(...)
# tts = DeepgramTTSService(...)
# tts = GoogleTTSService(...)
```

## Notes

* Works best on Chrome Desktop
* Do NOT expose .env or run without HTTPS in production
* Low latency tuning via buffer size + sample rate

## License

MIT — attribution preferred but not required
