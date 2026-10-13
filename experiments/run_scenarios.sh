#!/usr/bin/env bash
#
# prquestracao de uma rodada de experimentos para 1 cenario de provisionamento.
#
#   APP=cpu URL=http://localhost:8001 SCENARIO=c1_1vcpu_1gb ./experiments/run_scenarios.sh
#   APP=mem URL=http://localhost:8002 SCENARIO=c2_2vcpu_2gb ./experiments/run_scenarios.sh
#   APP=io  URL=http://localhost:8003 SCENARIO=c3_2vcpu_4gb ./experiments/run_scenarios.sh
#
set -euo pipefail

APP="${APP:?defina APP=cpu|mem|io}"
URL="${URL:?defina URL=http://IP:PORTA da VM}"
SCENARIO="${SCENARIO:?defina SCENARIO=c1_1vcpu_1gb (identifica o provisionamento)}"
REQUESTS="${REQUESTS:-200}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PY:-python3}"

# perfis de demanda por aplicacao 
case "$APP" in
  cpu)
    DEMAND_KEY="size"
    DEMAND_VALUES="${DEMAND_VALUES:-100,200,300}"
    CONCURRENCY="${CONCURRENCY:-1,5,10,25,50}"
    SET_ARGS=()
    ;;
  mem)
    DEMAND_KEY="mb"
    DEMAND_VALUES="${DEMAND_VALUES:-64,128,256}"
    CONCURRENCY="${CONCURRENCY:-1,5,10,25}"
    SET_ARGS=()
    ;;
  io)
    DEMAND_KEY="delay_ms"
    DEMAND_VALUES="${DEMAND_VALUES:-50,100,200}"
    CONCURRENCY="${CONCURRENCY:-1,10,50,100}"
    SET_ARGS=(--set file_mb="${FILE_MB:-4}")
    ;;
  *)
    echo "APP invalido: $APP (use cpu|mem|io)"; exit 1 ;;
esac

OUT="$ROOT/results/$APP"
mkdir -p "$OUT"

echo "=============================================="
echo " APP=$APP  SCENARIO=$SCENARIO"
echo " URL=$URL  demanda($DEMAND_KEY)=$DEMAND_VALUES  conc=$CONCURRENCY"
echo " requisicoes/nivel=$REQUESTS  saida=$OUT"
echo "=============================================="

"$PY" "$ROOT/loadtest/loadtest.py" \
  --url "$URL" \
  --path /work \
  --label "$SCENARIO" \
  --demand-key "$DEMAND_KEY" \
  --demand-values "$DEMAND_VALUES" \
  --concurrency "$CONCURRENCY" \
  --requests "$REQUESTS" \
  "${SET_ARGS[@]}" \
  --out "$OUT"

echo "[ok] cenario '$SCENARIO' concluido. CSVs em $OUT"
echo "     graficos com: $PY analysis/plot.py --results $OUT"
