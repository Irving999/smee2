from fastapi import FastAPI, WebSocket, Request, HTTPException, Response
import uvicorn
import collections
import logging
import prometheus_client
from args import get_args

args = get_args()

logging.basicConfig(
    # in mondo we trust
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.ERROR - (args.verbose * 10),
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI()

connected_clients = prometheus_client.Gauge(
    "connected_clients",
    "Number of connected websocket clients per subscription",
    ["subscription_id"],
)

failed_connections = prometheus_client.Counter(
    "failed_connections",
    "Number of failed connection attempts to /tunnel",
    ["subscription_id", "reason"],
)

clients = collections.defaultdict(list)

subscribers = {}

@app.post("/webhook/{subscription_id}")
async def webhook(subscription_id: str, request: Request):
    if subscription_id is not None:
        header_val = request.headers.get("X-API-Key")
        if (header_val != "hello"):
            raise HTTPException(status_code=403, detail="API key is not valid ")

        data = await request.json()
        logger.debug("Data pushed to webhook %s, received: %s", subscription_id, data)

        subscribers[subscription_id] = data
        
        for client in clients.get(subscription_id, []):
            await client.send_json(data)
        
        logger.error("Data sent to websocket client")
        return {"message":"received"}  
    
    else:   
        logger.error("Invalid subscription '%s', connection not accepted", subscription_id)
        return
    
    
@app.websocket("/tunnel/{subscription_id}")
async def websocket_endpoint(subscription_id: str, websocket: WebSocket):
    api_key = websocket.headers.get("X-API-Key")
    
    if (api_key != "hello"):
        failed_connections.labels(
            subscription_id=subscription_id,
            reason="bad_api_key",
        ).inc()
        await websocket.close(code=1008)
        return

    await websocket.accept()
    
    connected_clients.labels(subscription_id).inc()
    
    clients[subscription_id].append(websocket)

    logger.debug(f"Websocket connection successfully established at id: {subscription_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text("Message received")
    except Exception as e:
        failed_connections.labels(
            subscription_id=subscription_id,
            reason="websocket_receive_failed",
        ).inc()
        connected_clients.labels(subscription_id).dec()
        clients[subscription_id].remove(websocket)
        if not clients[subscription_id]:
            clients.pop(subscription_id, None)

        logger.debug(f"Websocket connection disconnected at id: {subscription_id}")
            

@app.get("/metrics")
def get_metrics():
    return Response(
        content=prometheus_client.generate_latest(),
        media_type="text/plain",
    )

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=5000)
