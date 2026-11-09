from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os, uuid

DIR = "/data"
PERMITIDAS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
app = FastAPI(title="Servicio de Almacenamiento")

@app.post("/archivos")
async def guardar(archivo: UploadFile = File(...)):
    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in PERMITIDAS:
        raise HTTPException(400, "Formato no permitido")
    nombre = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(DIR, nombre), "wb") as f:
        f.write(await archivo.read())
    return {"nombre": nombre}

@app.get("/archivos/{nombre}")
def obtener(nombre: str):
    ruta = os.path.join(DIR, os.path.basename(nombre))
    if not os.path.exists(ruta):
        raise HTTPException(404, "No existe")
    return FileResponse(ruta)

@app.get("/salud")
def salud():
    return {"estado": "ok", "servicio": "almacenamiento"}