import os
import time
import threading

import numpy as np
import psutil
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Memory-bound app")

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

_keep_alive = []


def _mem_work(mb):
    n = max(1, int(mb * 1024 * 1024 / 8))
    arr = np.empty(n, dtype=np.float64)
    arr.fill(1.2345)
    total = float(arr.sum())
    scaled = arr * 2.0
    total += float(scaled.sum())

    arena = np.empty(n, dtype=np.float64)
    arena[:] = arr
    total += float(arena[::64].sum())
    _keep_alive.append(arena)
    if len(_keep_alive) > 4:
        _keep_alive.pop(0)
    return total


@app.get("/health")
def health():
    return {"status": "ok", "profile": "memory-bound", "uptime_s": round(time.time() - STARTED_AT, 1)}


@app.get("/stats")
def stats():
    return {
        "proc_cpu_percent": round(_stats["proc_cpu"], 1),
        "sys_cpu_percent": round(_stats["sys_cpu"], 1),
        "rss_mb": round(_stats["rss_mb"], 1),
        "load_avg": [round(x, 2) for x in os.getloadavg()],
    }


@app.get("/work")
def work(mb: int = 128):
    mb = max(1, mb)
    t0 = time.perf_counter()
    _mem_work(mb)
    return {"profile": "memory-bound", "mb": mb, "compute_ms": round((time.perf_counter() - t0) * 1000, 2)}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8002")),
        workers=int(os.getenv("WORKERS", "1")),
    )
