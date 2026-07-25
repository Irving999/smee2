# smee2

Simple FastAPI webhook server that broadcasts incoming webhook payloads to connected WebSocket clients.

## Install

### bash
```sh
python -m venv .venv

source ./.venv/bin/activate

python -m pip install -r requirements.txt
```

### windows
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```sh
# add -vvv for verbose logging
python server.py
```

The server runs at `http://127.0.0.1:5000`.

## Test

In one terminal, connect to the WebSocket tunnel:

```powershell
websocat ws://127.0.0.1:5000/tunnel
```

In another terminal, send a webhook payload:

### bash
```sh
curl -X POST http://127.0.0.1:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"message":"hello from webhook"}'
```

### windows, powershell
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/webhook -ContentType "application/json" -Body '{"message":"hello from webhook"}'
```

The connected WebSocket client should receive the JSON payload.
