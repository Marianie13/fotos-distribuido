from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Servicio de Notificaciones")
clientes: set[WebSocket] = set()

@app.websocket("/ws")
async def conexion(websocket: WebSocket):
    await websocket.accept()
    clientes.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clientes.discard(websocket)

@app.post("/eventos")
async def publicar(evento: dict):
    for c in list(clientes):
        try:
            await c.send_json(evento)
        except Exception:
            clientes.discard(c)
    return {"enviado_a": len(clientes)}

@app.get("/salud")
def salud():
    return {"estado": "ok", "servicio": "notificaciones", "conectados": len(clientes)}