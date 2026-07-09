from fastapi import FastAPI, WebSocket, Request, Response, HTTPException
import prometheus_client
import uvicorn

app = FastAPI()

clients: dict[str, list[WebSocket]] = {}

connected_clients = prometheus_client.Gauge(
    "connected_clients",
    "Number of clients connected to tunnel",
    labelnames=["id"],
)

webhook_requests_total = prometheus_client.Counter(
    "webhook_requests_total",
    "Total incoming HTTP requests to /webhook",
)

invalid_webhook_requests_total = prometheus_client.Counter(
    "invalid_requests_total",
    "Total invalid HTTP requests to /webhook",
)

@app.get("/")
def root():
    return({ "message": "Welcome to the server!" })

@app.post("/webhook/{id}")
async def webhook(id: str, body: dict, request: Request):
    webhook_requests_total.inc()
    if request.headers.get("X-API-Key") != "hello":
        invalid_webhook_requests_total.inc()
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    client_list = clients.get(id)

    if not client_list:
        invalid_webhook_requests_total.inc()
        raise HTTPException(status_code=404, detail="No connected clients found")
    
    for client in client_list:
        await client.send_json(body)
    
    return ({ "status": "ok" })

@app.websocket("/tunnel/{id}")
async def tunnel(id: str, websocket: WebSocket):
    await websocket.accept()

    clients.setdefault(id, []).append(websocket)
    connected_clients.labels(id=id).inc()

    try:
        while True:
            await websocket.receive_text()
    except:
            clients[id].remove(websocket)
            connected_clients.labels(id=id).dec()
            if not clients[id]:
                del clients[id]

@app.get("/metrics")
def get_metrics():
    return Response(
        media_type="text/plain",
        content=prometheus_client.generate_latest(),
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
