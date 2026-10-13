# Demanda, Provisionamento e Desempenho

## Aplicacoes

| App                              | Perfil       | Porta | `/work` (demanda)                  |
|----------------------------------|--------------|-------|------------------------------------|
| [cpu_app](apps/cpu_app/main.py)       | CPU-bound    | 8001  | `?size=` (matriz NxN, mult. pura)  |
| [memory_app](apps/memory_app/main.py) | Memory-bound | 8002  | `?mb=` (MB alocados em NumPy)       |
| [io_app](apps/io_app/main.py)         | IO-bound     | 8003  | `?delay_ms=` e `?file_mb=` (async) |

- `/stats` retorna CPU do processo, CPU do sistema, RSS e load average.

## Execução local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python apps/cpu_app/main.py       
python apps/memory_app/main.py     
python apps/io_app/main.py         

curl "http://localhost:8001/work?size=150"
```

## Experimentos

1. Para cada cenario de provisionamento:

   ```bash
   APP=cpu URL=http://192.168.56.10:8001 SCENARIO=c1_1vcpu_1gb \
     ./experiments/run_scenarios.sh
   ```

   Os CSVs vao para `results/<app>/` (resumo + series temporais).
2. Geração de graficos:

   ```bash
   python analysis/plot.py --results results/cpu
   ```

## Estrutura

```
apps/            # as tres aplicacoes backend
loadtest/        # gerador de carga + coletor de metricas (um nivel por chamada)
experiments/     # orquestrador: varredura demanda x concorrencia por cenario
analysis/        # geracao de graficos a partir dos CSVs
deploy/          # systemd + env + roteiro de deploy/provisionamento na VM
results/         # saida dos experimentos (CSVs e figuras)
```
