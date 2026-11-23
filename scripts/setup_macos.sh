#!/usr/bin/env bash
# Instalação no macOS (Apple Silicon), sem Docker: ambientes Python, modelos e conjunto de teste.
#
# O que faz, em ordem:
#   1. confere o sistema (macOS, arm64, git, python3 do sistema para iniciar);
#   2. instala o uv 0.11.32 num ambiente próprio (.venv-uv) e, com ele, o Python 3.12 (na pasta do
#      usuário, ~/.local/share/uv; nada é instalado no sistema e não pede senha);
#   3. cria três ambientes com as versões exatas de requirements/macos-*.lock.txt:
#        .venv         inferência e demonstração (LiteRT, OpenCV, pycocotools)
#        .venv-export  preparação do YOLOv8n e do EfficientDet-Lite0 (Ultralytics, ai-edge-quantizer)
#        .venv-tf      preparação do SSD-MobileNet V1 (TensorFlow)
#      (dois ambientes de preparação, como no Dockerfile.host: as dependências não convivem bem);
#   4. roda os scripts do próprio projeto (src/prepare/): baixa as origens conferindo o sha256,
#      gera os modelos FP32 e INT8 e monta o conjunto de teste (350 imagens do COCO val2017).
# Com --do-zero apaga antes os ambientes e os modelos .tflite (os downloads conferidos ficam).
# Com --so-ambiente para depois do passo 3.
#
# O que gera: .venv*, models/*.tflite, models/fontes/, data/calibracao/, data/teste/, data/teste_coco/.
# Tempo medido num MacBook M5: ~5 min na primeira vez (download do COCO incluído); ~2 min refazendo.
# Uso: bash scripts/setup_macos.sh [--do-zero] [--so-ambiente]
set -euo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then sed -n '2,22p' "$0"; exit 0; fi

cd "$(dirname "$0")/.."
DO_ZERO=0; SO_AMBIENTE=0
for a in "$@"; do
  case "$a" in
    --do-zero) DO_ZERO=1 ;;
    --so-ambiente) SO_AMBIENTE=1 ;;
    *) echo "Opção desconhecida: $a" >&2; exit 2 ;;
  esac
done
INICIO=$SECONDS
passo() { echo; echo "== $* ($(( SECONDS - INICIO )) s)"; }

passo "1/4 Conferindo o sistema"
[[ "$(uname -s)" == "Darwin" ]] || { echo "Este script é para macOS." >&2; exit 1; }
echo "macOS $(sw_vers -productVersion), $(uname -m), $(sysctl -n machdep.cpu.brand_string)"
[[ "$(uname -m)" == "arm64" ]] || echo "AVISO: testado só em Apple Silicon (arm64)."
command -v git >/dev/null || { echo "Falta o git. Instale as Command Line Tools: xcode-select --install" >&2; exit 1; }
if ! /usr/bin/python3 -c 'import venv' 2>/dev/null; then
  echo "Falta o python3 do sistema (vem com as Command Line Tools: xcode-select --install)." >&2; exit 1
fi

if [[ $DO_ZERO == 1 ]]; then
  echo "Apagando ambientes e modelos .tflite (downloads conferidos são mantidos)"
  rm -rf .venv .venv-uv .venv-export .venv-tf models/*.tflite
fi

passo "2/4 uv 0.11.32 e Python 3.12"
if [[ ! -x .venv-uv/bin/uv ]]; then
  /usr/bin/python3 -m venv .venv-uv
  .venv-uv/bin/python -m pip install -q --disable-pip-version-check uv==0.11.32
fi
UV=.venv-uv/bin/uv
$UV --version
$UV python install 3.12

passo "3/4 Ambientes Python com versões fixadas"
for par in ".venv:macos-demo" ".venv-export:macos-export" ".venv-tf:macos-tf"; do
  venv=${par%%:*}; lock=requirements/${par##*:}.lock.txt
  [[ -x $venv/bin/python ]] || $UV venv -q --python 3.12 "$venv"
  echo "-- $venv <- $lock"
  $UV pip sync -q --python "$venv/bin/python" "$lock"
done
.venv/bin/python -c 'import ai_edge_litert, cv2, numpy, pycocotools; print("ambiente .venv OK, OpenCV", cv2.__version__)'
[[ $SO_AMBIENTE == 1 ]] && { echo "Pronto (só ambientes)."; exit 0; }

passo "4/4 Modelos e conjunto de teste (scripts de src/prepare/)"
export YOLO_CONFIG_DIR="$PWD/.venv-export/ultralytics-cfg" PYTHONUNBUFFERED=1
echo "-- origens (sha256 conferido)";            .venv-export/bin/python src/prepare/baixar.py
echo "-- EfficientDet-Lite0 FP32 e INT8";        .venv-export/bin/python src/prepare/quantizar_efficientdet.py 2>&1 | grep -E '^(OK|Quantized)|Error:|^Traceback' || true
echo "-- SSD-MobileNet V1 FP32 e INT8";          .venv-tf/bin/python src/prepare/converter_ssd.py 2>&1 | grep -E '^OK|Error:|^Traceback' || true
echo "-- YOLOv8n FP32 e INT8 (320, 480, 640)";   .venv-export/bin/python src/prepare/exportar_yolo.py 2>&1 | grep -E '^OK|Error:|^Traceback' || true
echo "-- conjunto de teste (350 imagens COCO)";  .venv/bin/python src/prepare/montar_teste.py
.venv/bin/python demo/etapas.py tamanhos 2>&1 | grep -v '^INFO'
FALTAM=$(.venv/bin/python -c 'import sys; sys.path.insert(0,"demo"); from comum_demo import conferir_modelos; print(" ".join(p.name for p in conferir_modelos()))')
if [[ -n "$FALTAM" ]]; then echo "ERRO: faltam modelos: $FALTAM" >&2; exit 1; fi

echo
echo "Instalação concluída em $(( SECONDS - INICIO )) s. Próximo passo: bash demo/roteiro.sh"
