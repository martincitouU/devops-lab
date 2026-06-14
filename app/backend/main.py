"""
devops-lab — Task Manager API
Backend: FastAPI + PostgreSQL

Endpoints:
  GET    /health        → estado del servidor (útil para K8s health checks)
  GET    /tasks         → listar todas las tareas
  POST   /tasks         → crear una tarea
  PUT    /tasks/{id}    → marcar tarea como completada
  DELETE /tasks/{id}    → eliminar una tarea
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
import psycopg2.extras
import os

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="devops-lab API", version="1.0.0")

# Permite que el frontend (servido por Nginx) llame a esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Conexión a PostgreSQL ──────────────────────────────────────────────────────
# Las variables de entorno se inyectan desde Docker / Kubernetes
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "tasksdb"),
        user=os.getenv("DB_USER", "taskuser"),
        password=os.getenv("DB_PASSWORD", "taskpass"),
    )

# ── Modelos ────────────────────────────────────────────────────────────────────
class TaskIn(BaseModel):
    title: str
    description: Optional[str] = None

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool

# ── Inicialización de tabla ────────────────────────────────────────────────────
@app.on_event("startup")
def create_table():
    """Crea la tabla tasks si no existe. Se ejecuta al arrancar el servidor."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          SERIAL PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            completed   BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Health check — Kubernetes lo usa para saber si el pod está listo."""
    return {"status": "ok"}


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM tasks ORDER BY id DESC")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return tasks


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskIn):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING *",
        (task.title, task.description),
    )
    new_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_task


@app.put("/tasks/{task_id}", response_model=Task)
def complete_task(task_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "UPDATE tasks SET completed = TRUE WHERE id = %s RETURNING *",
        (task_id,),
    )
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not updated:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return updated


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")