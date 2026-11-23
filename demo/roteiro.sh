#!/usr/bin/env bash
# Roteiro da apresentação em aula: o fluxo do projeto em etapas que rodam uma a uma neste Mac.
#
#   1  Modelos pré-treinados: de onde vêm e conferência do sha256 (o projeto NÃO treina modelos)
#   2  Quantização pós-treinamento FP32 -> INT8, refeita aqui com o COCO128, com tamanhos antes/depois
#   3  Qualidade: mAP@50 da classe pessoa num subconjunto do conjunto de teste (COCO val2017)
#   4  Latência FP32 x INT8 medida neste Mac, ao lado da do artigo
#   5  Ao vivo: webcam
#   6  Ao vivo (reserva): imagens COCO do projeto, se a câmera falhar
#
# Sem argumentos abre um menu. Com o número roda só aquela etapa, por exemplo:
#   bash demo/roteiro.sh 2            quantização completa (3 modelos, ~1 min num M5)
#   bash demo/roteiro.sh 2 --rapido   só o EfficientDet-Lite0 (~15 s)
#   bash demo/roteiro.sh 3 --completo mAP com as 350 imagens nas 3 resoluções (~1 min)
# Antes, uma vez: bash scripts/setup_macos.sh
set -uo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then sed -n '2,17p' "$0"; exit 0; fi
cd "$(dirname "$0")/.."
PY=.venv/bin/python
export YOLO_CONFIG_DIR="$PWD/.venv-export/ultralytics-cfg" PYTHONUNBUFFERED=1 TF_CPP_MIN_LOG_LEVEL=2
[[ -x $PY ]] || { echo "Ambiente não encontrado. Rode antes: bash scripts/setup_macos.sh" >&2; exit 1; }

# O LiteRT imprime uma linha "INFO: Created TensorFlow Lite XNNPACK delegate" por modelo; escondemos.
py() { "$PY" "$@" 2> >(grep -v '^INFO: ' >&2); }
titulo() { echo; echo "================================================================================"; echo "  $*"; echo "================================================================================"; }
pausa() { [[ -n "${SEM_PAUSA:-}" ]] || read -r -p $'\n[Enter para continuar] ' _; }

etapa1() {
  titulo "Etapa 1 — Modelos pré-treinados (nenhum treinamento é feito no projeto)"
  echo "Baixando/conferindo as origens com o script do projeto (src/prepare/baixar.py):"
  .venv-export/bin/python src/prepare/baixar.py
  echo
  py demo/etapas.py origens
}

etapa2() {
  local modo=${1:-completo} bkp
  titulo "Etapa 2 — Quantização pós-treinamento FP32 -> INT8 (modo $modo)"
  echo "Os INT8 são refeitos AGORA, neste Mac, pelos scripts do projeto, calibrados nas 128 imagens do COCO128."
  bkp=$(mktemp -d)
  if [[ $modo == rapido ]]; then
    mv models/efficientdet_lite0_int8_*.tflite "$bkp"/ 2>/dev/null
  else
    mv models/*_int8_*.tflite "$bkp"/ 2>/dev/null
  fi
  echo; echo "ANTES (os INT8 foram retirados):"; py demo/etapas.py tamanhos
  local t0=$SECONDS ok=1
  echo; echo "-- EfficientDet-Lite0: ai-edge-quantizer (static_wi8_ai8)"
  .venv-export/bin/python src/prepare/quantizar_efficientdet.py 2>&1 | grep -E '^(OK|Original|Quantized|Quantization)|Error:|^Traceback' || ok=0
  echo "   $(( SECONDS - t0 )) s até aqui"
  if [[ $modo != rapido ]]; then
    echo "-- SSD-MobileNet V1: TFLiteConverter com representative_dataset (inteiro total, uint8)"
    .venv-tf/bin/python src/prepare/converter_ssd.py 2>&1 | grep -E '^OK|Error:|^Traceback' || ok=0
    echo "   $(( SECONDS - t0 )) s até aqui"
    echo "-- YOLOv8n: export oficial da Ultralytics, quantize=8, em 320, 480 e 640 (INT8 híbrido, D2)"
    .venv-export/bin/python src/prepare/exportar_yolo.py 2>&1 | grep -E '^OK|Error:|^Traceback' || ok=0
  fi
  echo; echo "Quantização: $(( SECONDS - t0 )) s neste Mac."
  # Se algo falhou, devolve o INT8 anterior para a demonstração continuar funcionando.
  for f in "$bkp"/*.tflite; do [[ -e $f && ! -e models/$(basename "$f") ]] && mv "$f" models/ && echo "restaurado: $(basename "$f")"; done
  rm -rf "$bkp"
  echo; echo "DEPOIS:"; py demo/etapas.py tamanhos
  echo
  echo "Obs.: os INT8 gerados neste Mac não são idênticos byte a byte aos usados no artigo (sha256 diferente),"
  echo "e o mAP@50 deles difere um pouco do publicado (etapa 3 mostra os dois lado a lado). Os FP32 do SSD"
  echo "e do EfficientDet saem idênticos aos do artigo (mesmo sha256 de results/modelos.csv)."
}

etapa3() {
  titulo "Etapa 3 — Qualidade: mAP@50 da classe pessoa"
  if [[ "${1:-}" == completo ]]; then
    for r in 320 480 640; do py demo/etapas.py map --imagens 350 --res "$r"; echo; done
  else
    py demo/etapas.py map --imagens 100 --res 320
  fi
}

etapa4() {
  titulo "Etapa 4 — Latência FP32 x INT8 medida neste Mac"
  py demo/demo_ao_vivo.py --benchmark --quadros 60
}

etapa5() {
  titulo "Etapa 5 — Ao vivo com a webcam"
  echo "Teclas: m ou 1/2/3 troca o modelo, i alterna FP32/INT8, r troca a resolução, espaço pausa, q sai."
  py demo/demo_ao_vivo.py "$@" || {
    echo; echo "A câmera falhou. Libere o Terminal em Ajustes do Sistema > Privacidade e Segurança > Câmera"
    echo "e abra o Terminal de novo, ou use a reserva: bash demo/roteiro.sh 6"; }
}

etapa6() {
  titulo "Etapa 6 — Ao vivo (reserva): imagens COCO do conjunto de teste"
  py demo/demo_ao_vivo.py --imagens "$@"
}

rodar() {
  local n=$1; shift
  case $n in
    1) etapa1 ;;
    2) if [[ "${1:-}" == "--rapido" ]]; then etapa2 rapido; else etapa2 completo; fi ;;
    3) if [[ "${1:-}" == "--completo" ]]; then etapa3 completo; else etapa3; fi ;;
    4) etapa4 ;;
    5) etapa5 "$@" ;;
    6) etapa6 "$@" ;;
    *) echo "Etapa inválida: $n" >&2; return 1 ;;
  esac
}

if [[ $# -gt 0 ]]; then rodar "$@"; exit $?; fi

while true; do
  titulo "Detecção de Pessoas na Borda — roteiro da demonstração"
  cat <<'MENU'
  1  Modelos pré-treinados (origem e sha256)              ~10 s
  2  Quantização FP32 -> INT8 ao vivo (3 modelos)         ~1 min
  2r Quantização rápida (só EfficientDet-Lite0)           ~15 s
  3  mAP@50 da classe pessoa (100 imagens, fonte 320)     ~5 s
  3c mAP@50 completo (350 imagens, 320/480/640)           ~1 min
  4  Latência FP32 x INT8 neste Mac (18 combinações)      ~10 s
  5  Ao vivo: webcam
  6  Ao vivo (reserva): imagens COCO
  q  Sair
MENU
  read -r -p "Etapa: " op || break
  case $op in
    1|4|5|6) rodar "$op"; pausa ;;
    2) rodar 2; pausa ;;
    2r) rodar 2 --rapido; pausa ;;
    3) rodar 3; pausa ;;
    3c) rodar 3 --completo; pausa ;;
    q|Q) break ;;
    *) echo "Opção inválida." ;;
  esac
done
