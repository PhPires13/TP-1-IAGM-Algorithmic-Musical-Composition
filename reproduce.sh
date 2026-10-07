#!/usr/bin/env bash
# Reproduz todos os resultados do trabalho: peças de exemplo, experimento e figura
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python}

# 1) Mesma configuração, sementes diferentes (ordem 3, T = 1.0)
$PY generate.py --order 3 --temperature 1.0 --n 2 --seed 0 --outdir music
# 2) Variando a ordem da cadeia (hiperparâmetro principal)
$PY generate.py --order 1 --temperature 1.0 --n 1 --seed 0 --outdir music
$PY generate.py --order 5 --temperature 1.0 --n 1 --seed 0 --outdir music
# 3) Variando a temperatura
$PY generate.py --order 3 --temperature 1.5 --n 1 --seed 0 --outdir music
# 4) Modo menor com 6 frases
$PY generate.py --order 3 --temperature 1.0 --n 1 --seed 0 --mode minor --phrases 6 --outdir music

# Experimento do trade-off ordem baixa x ordem alta (tabela + figura do resumo)
$PY experiment.py
