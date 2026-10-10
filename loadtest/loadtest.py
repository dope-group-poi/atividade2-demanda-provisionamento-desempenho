import argparse
import asyncio
import csv
import os
import statistics
import time

import httpx


def percentiles(samples, ps=(50, 95, 99)):
    out = {}
    if not samples:
        return {f"p{p}_ms": 0.0 for p in ps}
    s = sorted(samples)
    for p in ps:
        idx = min(len(s) - 1, int(round((p / 100) * (len(s) - 1))))
        out[f"p{p}_ms"] = round(s[idx], 2)
    return out


async def _poll_stats(client, stats_url, stop, samples, interval=1.0):
    while not stop.is_set():
        try:
            r = await client.get(stats_url, timeout=5)
            d = r.json()
            samples.append(
                (
                    round(time.time(), 2),
                    d.get("proc_cpu_percent", 0.0),
                    d.get("sys_cpu_percent", 0.0),
                    d.get("rss_mb", 0.0),
                )
            )
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def run_level(url, path, params, requests, concurrency):
    latencies = []
    errors = 0
    counter = {"n": 0}
    stats_samples = []

    limits = httpx.Limits(max_connections=concurrency + 5, max_keepalive_connections=concurrency + 5)
    timeout = httpx.Timeout(300.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        target = url.rstrip("/") + path
        stop = asyncio.Event()
        poller = asyncio.create_task(_poll_stats(client, url.rstrip("/") + "/stats", stop, stats_samples))

        async def worker():
            nonlocal errors
            while True:
                i = counter["n"]
                if i >= requests:
                    return
                counter["n"] = i + 1
                t0 = time.perf_counter()
                try:
                    r = await client.get(target, params=params)
                    r.raise_for_status()
                    latencies.append((time.perf_counter() - t0) * 1000)
                except Exception:
                    errors += 1

        started = time.perf_counter()
        await asyncio.gather(*[worker() for _ in range(concurrency)])
        elapsed = time.perf_counter() - started
        stop.set()
        await poller

    proc_cpus = [s[1] for s in stats_samples]
    sys_cpus = [s[2] for s in stats_samples]
    rss = [s[3] for s in stats_samples]
    summary = {
        "requests": requests,
        "errors": errors,
        "ok": len(latencies),
        "elapsed_s": round(elapsed, 3),
        "throughput_rps": round(len(latencies) / elapsed, 2) if elapsed > 0 else 0.0,
        "avg_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "min_ms": round(min(latencies), 2) if latencies else 0.0,
        "max_ms": round(max(latencies), 2) if latencies else 0.0,
        "proc_cpu_avg": round(statistics.mean(proc_cpus), 1) if proc_cpus else 0.0,
        "sys_cpu_avg": round(statistics.mean(sys_cpus), 1) if sys_cpus else 0.0,
        "rss_mb_max": round(max(rss), 1) if rss else 0.0,
    }
    summary.update(percentiles(latencies))
    return summary, stats_samples


async def main():
    ap = argparse.ArgumentParser(description="Load generator + resource collector for the POI apps.")
    ap.add_argument("--url", required=True, help="ex: http://192.168.56.10:8001")
    ap.add_argument("--path", default="/work")
    ap.add_argument("--label", default="run")
    ap.add_argument("--set", action="append", default=[], metavar="k=v", help="param fixo (pode repetir)")
    ap.add_argument("--demand-key", default=None, help="nome do parametro que varia a demanda")
    ap.add_argument("--demand-values", default="", help="valores separados por virgula")
    ap.add_argument("--concurrency", default="1,5,10,25")
    ap.add_argument("--requests", type=int, default=200, help="requisicoes por nivel (demanda x concorrencia)")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    fixed = {}
    for kv in args.set:
        k, v = kv.split("=", 1)
        fixed[k] = v

    demand_values = [d.strip() for d in args.demand_values.split(",") if d.strip()] or [None]
    concurrency_levels = [int(c) for c in args.concurrency.split(",") if c.strip()]

    os.makedirs(args.out, exist_ok=True)
    rows = []

    for dv in demand_values:
        for conc in concurrency_levels:
            params = dict(fixed)
            if args.demand_key and dv is not None:
                params[args.demand_key] = dv
            print(f"[load] demand {args.demand_key}={dv} concurrency={conc} ...", flush=True)
            summary, ts = await run_level(args.url, args.path, params, args.requests, conc)
            row = {
                "label": args.label,
                "url": args.url,
                "path": args.path,
                "demand_key": args.demand_key or "",
                "demand_value": dv if dv is not None else "",
                "concurrency": conc,
            }
            row.update(summary)
            rows.append(row)
            print(
                f"        rps={row['throughput_rps']} avg={row['avg_ms']}ms p95={row['p95_ms']}ms "
                f"err={row['errors']} cpu={row['proc_cpu_avg']}% mem={row['rss_mb_max']}MB",
                flush=True,
            )
            ts_path = os.path.join(args.out, f"{args.label}_{args.demand_key or 'fixed'}_{dv}_c{conc}_timeseries.csv")
            with open(ts_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "proc_cpu_percent", "sys_cpu_percent", "rss_mb"])
                w.writerows(ts)

    summary_path = os.path.join(args.out, f"{args.label}_summary.csv")
    fields = [
        "label", "url", "path", "demand_key", "demand_value", "concurrency", "requests",
        "ok", "errors", "elapsed_s", "throughput_rps", "avg_ms", "min_ms", "max_ms",
        "p50_ms", "p95_ms", "p99_ms", "proc_cpu_avg", "sys_cpu_avg", "rss_mb_max",
    ]
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"[done] resumo em {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
