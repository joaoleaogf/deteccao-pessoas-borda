"""E4, passos 2 e 3: prepara o EfficientDet-Lite0 em FP32 e INT8.

O que faz: o FP32 é o arquivo do MediaPipe, copiado sem alteração. O INT8 é gerado aqui por
quantização pós-treinamento com ai-edge-quantizer, calibrada no mesmo COCO128 dos outros
modelos (em vez de usar o INT8 pronto do MediaPipe, cuja calibração não é documentada).
Os dois modelos saem SEM a etapa de NMS: devolvem caixas e pontuações brutas por âncora.

O que gera: models/efficientdet_lite0_fp32_320.tflite e models/efficientdet_lite0_int8_320.tflite.
Roda no ambiente /opt/venv-export. Modelo já existente não é refeito (use --refazer).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import FONTES, MODELS, ler_yaml, nome_modelo  # noqa: E402
from quantizar import quantizar_inteiro_total  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refazer", action="store_true", help="refaz modelos que já existem")
    args = ap.parse_args()

    cfg = ler_yaml("models.yaml")["modelos"]["efficientdet_lite0"]
    MODELS.mkdir(exist_ok=True)
    for res in cfg["resolucoes"]:
        fp32 = MODELS / nome_modelo("efficientdet_lite0", "fp32", res)
        int8 = MODELS / nome_modelo("efficientdet_lite0", "int8", res)
        if args.refazer or not fp32.exists():
            shutil.copy(FONTES / cfg["arquivo"], fp32)
            print(f"OK {fp32.name}")
        if args.refazer or not int8.exists():
            quantizar_inteiro_total(fp32, int8, "efficientdet_lite0", res)
            print(f"OK {int8.name}")


if __name__ == "__main__":
    main()
