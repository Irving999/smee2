from fastapi import FastAPI, WebSocket, Request, Response, HTTPException
import prometheus_client
import uvicorn
import logging

logging.basicConfig(
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

app = FastAPI()

clients: dict[str, list[WebSocket]] = {}
subscribers = {}

connected_clients = prometheus_client.Gauge(
    "connected_clients",
    "Number of clients connected to a tunnel",
    labelnames=["subscription_id"],
)

webhook_requests_total = prometheus_client.Counter(
    "webhook_requests_total",
    "Total incoming HTTP requests to /webhook",
)

invalid_webhook_requests_total = prometheus_client.Counter(
    "invalid_requests_total",
    "Total invalid HTTP requests to /webhook",
)

webhook_payload_size = prometheus_client.Histogram(
    "webhook_payload_size",
    "Size of incoming webhook payloads in bytes",
    buckets=(100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, float("inf")),
)

@app.post("/webhook/{subscription_id}")
async def webhook(subscription_id: str, request: Request):
    webhook_requests_total.inc()

    if subscription_id is not None:
        header_val = request.headers.get("X-API-Key")

        if (header_val != "hello"):
            invalid_webhook_requests_total.inc()
            raise HTTPException(status_code=403, detail="API key is not valid ")

        data = await request.json()
        event_type = request.headers.get("X-GitHub-Event")
        
        raw_body = await request.body()
        webhook_payload_size.observe(len(raw_body))

        logging.info("Webhook received: %s", data)

        subscribers[subscription_id] = data
        client_list = clients.get(subscription_id)

        if not client_list:
            invalid_webhook_requests_total.inc()
            raise HTTPException(status_code=404, detail="No connected clients found")

        for client in client_list:
            await client.send_json({"event": event_type, "payload": data}) 
            print("Data sent to websocket client")
        return {"message":"received"}  
     
    else:   
        print("Invalid endpoint, connection not accepted")
        return
    
    
@app.websocket("/tunnel/{subscription_id}")
async def websocket_endpoint(subscription_id: str, websocket: WebSocket):
    await websocket.accept()

    clients.setdefault(subscription_id, []).append(websocket)
    connected_clients.labels(subscription_id=subscription_id).inc()
    
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_text("Message received")
    except:
        clients[subscription_id].remove(websocket)
        connected_clients.labels(subscription_id=subscription_id).dec()

        if not clients[subscription_id]:
            del clients[subscription_id]

@app.get("/metrics")
def get_metrics():
    return Response(
        media_type="text/plain",
        content=prometheus_client.generate_latest(),
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000) 