import asyncio
import os
import time
import threading

import psutil
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="IO-bound app")

PROC = psutil.Process(os.getpid())
STARTED_AT = time.time()

_stats = {"proc_cpu": 0.0, "sys_cpu": 0.0, "rss_mb": 0.0}


def _sampler():
    PROC.cpu_percent(None)
    while True:
        time.sleep(0.5)
        _stats["proc_cpu"] = PROC.cpu_percent(None)
        _stats["sys_cpu"] = psutil.cpu_percent(None)
        _stats["rss_mb"] = PROC.memory_info().rss / (1024 * 1024)


threading.Thread(target=_sampler, daemon=True).start()

_DATA_DIR = os.getenv("IO_DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
os.makedirs(_DATA_DIR, exist_ok=True)
_IO_FILE = os.path.join(_DATA_DIR, "io_blob.bin")

MAX_DELAY_MS = int(os.getenv("MAX_DELAY_MS", "10000"))
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "512"))


def _ensure_blob(size_mb):
    path = f"{_IO_FILE}.{size_mb}"
    if not os.path.exists(path) or os.path.getsize(path) != size_mb * 1024 * 1024:
        with open(path, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
    return path


async def _io_work(delay_ms, file_mb):
    await asyncio.sleep(delay_ms / 1000.0)
    read = 0
    if file_mb > 0:
        path = await asyncio.to_thread(_ensure_blob, file_mb)
        chunk = await asyncio.to_thread(_read_file, path)
        read = len(chunk)
    return read


def _read_file(path):
    with open(path, "rb") as f:
        return f.read()


@app.get("/health")
def health():
    return {"status": "ok", "profile": "io-bound", "uptime_s": round(time.time() - STARTED_AT, 1)}


@app.get("/stats")
def stats():
    return {
        "proc_cpu_percent": round(_stats["proc_cpu"], 1),
        "sys_cpu_percent": round(_stats["sys_cpu"], 1),
        "rss_mb": round(_stats["rss_mb"], 1),
        "load_avg": [round(x, 2) for x in os.getloadavg()],
    }


@app.get("/work")
async def work(delay_ms: int = 50, file_mb: int = 0):
    delay_ms = max(0, min(delay_ms, MAX_DELAY_MS))
    file_mb = max(0, min(file_mb, MAX_FILE_MB))
    t0 = time.perf_counter()
    read = await _io_work(delay_ms, file_mb)
    return {
        "profile": "io-bound",
        "delay_ms": delay_ms,
        "file_mb": file_mb,
        "read_bytes": read,
        "compute_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8003")),
        workers=int(os.getenv("WORKERS", "1")),
    )
