from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

connected_clients: dict[str, list[WebSocket]] = {}

@app.get("/")
def root():
    return({ "message": "Welcome to the server!" })

@app.post("/webhook/{id}")
async def webhook(id: str, body: dict):
    for client in connected_clients.get(id, []):
        await client.send_json(body)
    return ({ "status": "ok" })

@app.websocket("/tunnel/{id}")
async def tunnel(id: str, websocket: WebSocket):
    await websocket.accept()
    connected_clients.setdefault(id, []).append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
            connected_clients[id].remove(websocket)
            if not connected_clients[id]:
                del connected_clients[id] 


if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, reload=True)
