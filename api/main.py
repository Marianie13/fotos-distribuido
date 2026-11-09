from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx, psycopg, os, socket

DB_URL = os.getenv("DB_URL", "postgresql://fotos:fotos123@db:5432/fotosdb")
ALMACEN = os.getenv("ALMACEN_URL", "http://almacenamiento:8000")
NOTIF = os.getenv("NOTIF_URL", "http://notificaciones:8000")
INSTANCIA = socket.gethostname()

def conectar():
    return psycopg.connect(DB_URL)

@asynccontextmanager
async def lifespan(app):
    with conectar() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS fotos (
            id SERIAL PRIMARY KEY,
            autor TEXT NOT NULL,
            descripcion TEXT,
            archivo TEXT NOT NULL,
            creada TIMESTAMP DEFAULT NOW())""")
    yield

app = FastAPI(title="API de Fotos", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.post("/fotos")
async def subir(autor: str = Form(...), descripcion: str = Form(""),
                archivo: UploadFile = File(...)):
    async with httpx.AsyncClient() as cliente:
        r = await cliente.post(f"{ALMACEN}/archivos", files={
            "archivo": (archivo.filename, await archivo.read(), archivo.content_type)})
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.json().get("detail", "Error en almacenamiento"))
    nombre = r.json()["nombre"]
    with conectar() as con:
        fila = con.execute(
            "INSERT INTO fotos (autor, descripcion, archivo) VALUES (%s, %s, %s) RETURNING id",
            (autor, descripcion, nombre)).fetchone()
        evento = {"tipo": "nueva_foto", "id": fila[0], "autor": autor,
              "descripcion": descripcion, "url": f"/imagenes/{nombre}",
              "atendido_por": INSTANCIA}
    try:
        async with httpx.AsyncClient(timeout=2) as cliente:
            await cliente.post(f"{NOTIF}/eventos", json=evento)
    except httpx.HTTPError:
        pass
        evento = {"tipo": "nueva_foto", "id": fila[0], "autor": autor,
              "descripcion": descripcion, "url": f"/imagenes/{nombre}",
              "atendido_por": INSTANCIA}
    try:
        async with httpx.AsyncClient(timeout=2) as cliente:
            await cliente.post(f"{NOTIF}/eventos", json=evento)
    except httpx.HTTPError:
        pass
    return {"id": fila[0], "archivo": nombre, "atendido_por": INSTANCIA}

@app.get("/fotos")
def listar():
    with conectar() as con:
        filas = con.execute(
            "SELECT id, autor, descripcion, archivo, creada FROM fotos ORDER BY id DESC").fetchall()
    return {"atendido_por": INSTANCIA, "fotos": [
        {"id": f[0], "autor": f[1], "descripcion": f[2],
         "url": f"/imagenes/{f[3]}", "creada": f[4].isoformat()} for f in filas]}

@app.get("/imagenes/{nombre}")
async def imagen(nombre: str):
    async with httpx.AsyncClient() as cliente:
        r = await cliente.get(f"{ALMACEN}/archivos/{nombre}")
    if r.status_code != 200:
        raise HTTPException(404, "No existe")
    return Response(r.content, media_type=r.headers.get("content-type"))

@app.get("/salud")
def salud():
    return {"estado": "ok", "servicio": "api", "instancia": INSTANCIA}

