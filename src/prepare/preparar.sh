#!/usr/bin/env bash
# E4, passos 2 e 3: roda, em ordem, toda a preparação dos modelos dentro do contêiner borda-prep.
#
# O que faz: baixa as origens, exporta o YOLOv8n, quantiza o EfficientDet-Lite0, converte o
# SSD-MobileNet V1 e confere os tipos dos tensores. Cada script Python usa o ambiente em que
# suas dependências estão instaladas (/opt/venv-export ou /opt/venv-tf).
# Com --do-zero, apaga antes os modelos e os resultados da E4 (os downloads são mantidos,
# porque são conferidos por sha256).
#
# O que gera: models/*.tflite, results/modelos.csv e results/ambiente/prep.txt.
# Uso: bash src/prepare/preparar.sh [--do-zero]
set -euo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then sed -n '2,11p' "$0"; exit 0; fi

cd "$(dirname "$0")/../.."
EXPORT=/opt/venv-export/bin/python
TF=/opt/venv-tf/bin/python

if [[ "${1:-}" == "--do-zero" ]]; then
  echo "== Apagando modelos e resultados da E4"
  rm -rf models/*.tflite models/edgetpu results/modelos.csv results/edgetpu_logs results/edgetpu_compile.csv \
         results/edgetpu_operadores.csv results/validacao_arm64.csv results/benchmark_fumaca \
         results/benchmark_fumaca.csv results/ambiente/prep.txt results/ambiente/edgetpu.txt results/ambiente/arm64.txt
fi

mkdir -p results/ambiente
{
  echo "sistema do contêiner: $(. /etc/os-release && echo "$PRETTY_NAME") ($(uname -m))"
  echo "python: $($EXPORT --version 2>&1)"
  echo "-- ambiente /opt/venv-export"
  uv pip list --python $EXPORT 2>/dev/null | grep -iE '^(ultralytics|torch|torchvision|litert-torch|ai-edge-litert|ai-edge-quantizer|onnx|numpy|pillow) '
  echo "-- ambiente /opt/venv-tf"
  uv pip list --python $TF 2>/dev/null | grep -iE '^(tensorflow|keras|numpy|pillow) '
} > results/ambiente/prep.txt

echo "== 1/5 Download das origens";            $EXPORT src/prepare/baixar.py
echo "== 2/5 YOLOv8n (FP32 e INT8)";           $EXPORT src/prepare/exportar_yolo.py
echo "== 3/5 EfficientDet-Lite0 (FP32 e INT8)"; $EXPORT src/prepare/quantizar_efficientdet.py
echo "== 4/5 SSD-MobileNet V1 (FP32 e INT8)";  $TF src/prepare/converter_ssd.py
echo "== 5/5 Conferência dos tensores";        $EXPORT src/prepare/conferir_modelos.py
