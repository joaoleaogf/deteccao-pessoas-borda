#!/usr/bin/env bash
# E4, passo 4: compila cada modelo INT8 com o Edge TPU Compiler e guarda os relatórios.
#
# O que faz: para cada models/*_int8_*.tflite roda "edgetpu_compiler -s", que tenta mapear os
# operadores do modelo para o acelerador Edge TPU e informa o que ficaria na CPU.
#   -s  mostra a tabela de operadores      -o  pasta de saída
# Sem o acelerador físico o modelo compilado não é executado: só o relatório é usado.
# Se um modelo falhar na compilação, a falha fica registrada e os demais continuam.
#
# O que gera:
#   models/edgetpu/<modelo>_edgetpu.tflite     modelo compilado
#   results/edgetpu_logs/<modelo>.log          relatório gravado pelo compilador
#   results/edgetpu_logs/<modelo>.saida.txt    tudo o que o compilador imprimiu
#   results/ambiente/edgetpu.txt               versão do compilador
#
# Roda no contêiner borda-edgetpu (linux/amd64). Uso: bash src/prepare/compilar_edgetpu.sh
set -uo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then sed -n '2,17p' "$0"; exit 0; fi

cd "$(dirname "$0")/../.."
mkdir -p models/edgetpu results/edgetpu_logs results/ambiente
edgetpu_compiler --version > results/ambiente/edgetpu.txt 2>&1

shopt -s nullglob
modelos=(models/*_int8_*.tflite)
if (( ${#modelos[@]} == 0 )); then echo "Nenhum modelo INT8 em models/."; exit 1; fi

for m in "${modelos[@]}"; do
  nome="$(basename "$m" .tflite)"
  echo "== $nome"
  edgetpu_compiler -s -o models/edgetpu "$m" > "results/edgetpu_logs/$nome.saida.txt" 2>&1
  echo "codigo_de_saida=$?" >> "results/edgetpu_logs/$nome.saida.txt"
  if [[ -f "models/edgetpu/${nome}_edgetpu.log" ]]; then
    mv "models/edgetpu/${nome}_edgetpu.log" "results/edgetpu_logs/$nome.log"
  fi
  tail -n 3 "results/edgetpu_logs/$nome.saida.txt"
done
