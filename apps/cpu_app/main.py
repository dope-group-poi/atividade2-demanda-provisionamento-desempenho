import os
import time
import threading

import psutil
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="CPU-bound app")

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


def _matmul(n):
    a = [[float((i + j) % 7 + 1) for j in range(n)] for i in range(n)]
    b = [[float((i * j) % 5 + 1) for j in range(n)] for i in range(n)]
    c = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ai = a[i]
        ci = c[i]
        for k in range(n):
            aik = ai[k]
            bk = b[k]
            for j in range(n):
                ci[j] += aik * bk[j]
    return c[0][0]


@app.get("/health")
def health():
    return {"status": "ok", "profile": "cpu-bound", "uptime_s": round(time.time() - STARTED_AT, 1)}


@app.get("/stats")
def stats():
    return {
        "proc_cpu_percent": round(_stats["proc_cpu"], 1),
        "sys_cpu_percent": round(_stats["sys_cpu"], 1),
        "rss_mb": round(_stats["rss_mb"], 1),
        "load_avg": [round(x, 2) for x in os.getloadavg()],
    }


MAX_SIZE = int(os.getenv("MAX_SIZE", "800"))


@app.get("/work")
def work(size: int = 150):
    size = max(1, min(size, MAX_SIZE))
    t0 = time.perf_counter()
    _matmul(size)
    return {"profile": "cpu-bound", "size": size, "compute_ms": round((time.perf_counter() - t0) * 1000, 2)}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        workers=int(os.getenv("WORKERS", "1")),
    )
