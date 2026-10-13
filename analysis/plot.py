# python analysis/plot.py --results results/cpu --out results/cpu/figs

import argparse
import csv
import glob
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

METRICS = [
    ("throughput_rps", "Vazao x demanda", "Vazao (req/s)"),
    ("p95_ms", "Latencia (p95) x demanda", "Latencia p95 (ms)"),
    ("avg_ms", "Latencia media x demanda", "Latencia media (ms)"),
    ("sys_cpu_avg", "CPU do sistema x demanda", "CPU media (%)"),
    ("rss_mb_max", "Memoria (RSS) x demanda", "RSS maximo (MB)"),
    ("errors", "Erros x demanda", "Erros"),
]


def load_rows(results_dir):
    rows = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*_summary.csv"))):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows.append(r)
    return rows


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def plot_metric(rows, metric, title, ylabel, out_dir):
    by_demand = defaultdict(lambda: defaultdict(list))
    for r in rows:
        y = to_float(r.get(metric))
        conc = to_float(r.get("concurrency"))
        if y is None or conc is None:
            continue
        demand = r.get("demand_value") or "-"
        scenario = r.get("label") or "cenario"
        by_demand[demand][scenario].append((conc, y))

    for demand, scenarios in sorted(by_demand.items()):
        fig, ax = plt.subplots(figsize=(8, 5))
        for scenario, pts in sorted(scenarios.items()):
            pts.sort()
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            ax.plot(xs, ys, marker="o", label=scenario)
        dk = rows[0].get("demand_key") or "demanda"
        ax.set_title(f"{title}  ({dk}={demand})")
        ax.set_xlabel("Concorrencia (clientes simultaneos)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(title="Cenario")
        fig.tight_layout()
        safe_demand = str(demand).replace("/", "_")
        out_path = os.path.join(out_dir, f"{metric}_demand-{safe_demand}.png")
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        print(f"[plot] {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Gera graficos dos experimentos.")
    ap.add_argument("--results", required=True, help="diretorio com os *_summary.csv")
    ap.add_argument("--out", default=None, help="diretorio de saida (default: <results>/figs)")
    args = ap.parse_args()

    out_dir = args.out or os.path.join(args.results, "figs")
    os.makedirs(out_dir, exist_ok=True)

    rows = load_rows(args.results)
    if not rows:
        print(f"[erro] nenhum *_summary.csv encontrado em {args.results}")
        return

    scenarios = sorted({r.get("label") for r in rows})
    print(f"[plot] {len(rows)} linhas, cenarios: {', '.join(scenarios)}")
    for metric, title, ylabel in METRICS:
        if any(to_float(r.get(metric)) is not None for r in rows):
            plot_metric(rows, metric, title, ylabel, out_dir)


if __name__ == "__main__":
    main()
