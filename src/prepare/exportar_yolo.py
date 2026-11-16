"""E4, passos 2 e 3: exporta o YOLOv8n para .tflite em FP32 e INT8, em cada resolução.

O que faz: carrega os pesos PyTorch (yolov8n.pt) e usa o exportador da Ultralytics com
format="litert". A resolução de entrada é fixada no export (imgsz). O INT8 depende de
"int8_modo" em configs/models.yaml:
  ultralytics    quantize=8 com calibração no COCO128 (corpo int8; entrada/saída/cabeça float32)
  inteiro_total  quantiza o .tflite FP32 com ai-edge-quantizer (tudo em int8)

O que gera: models/yolov8n_fp32_<res>.tflite e models/yolov8n_int8_<res>.tflite.
Roda no ambiente /opt/venv-export. Modelo já existente não é refeito (use --refazer).
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import DATA, FONTES, MODELS, imagens_calibracao, ler_yaml, nome_modelo  # noqa: E402


def yaml_calibracao(pasta_tmp: Path) -> Path:
    """Cria o arquivo de dataset que a Ultralytics exige, apontando para o nosso COCO128 local."""
    import yaml
    from ultralytics.utils import ROOT

    nomes = yaml.safe_load((ROOT / "cfg/datasets/coco128.yaml").read_text(encoding="utf-8"))["names"]
    imagens_calibracao()  # garante que o conjunto está completo
    cfg = ler_yaml("models.yaml")["calibracao"]
    destino = pasta_tmp / "calibracao.yaml"
    destino.write_text(
        yaml.safe_dump(
            {
                "path": str((DATA / "calibracao" / "coco128").resolve()),
                "train": "images/train2017",
                "val": "images/train2017",
                "names": nomes,
            }
        ),
        encoding="utf-8",
    )
    assert cfg["pasta_imagens"] == "coco128/images/train2017"
    return destino


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refazer", action="store_true", help="refaz modelos que já existem")
    args = ap.parse_args()

    from ultralytics import YOLO

    cfg = ler_yaml("models.yaml")["modelos"]["yolov8n"]
    modo = cfg["int8_modo"]
    if modo not in ("ultralytics", "inteiro_total"):
        raise SystemExit(f"int8_modo inválido: {modo}")
    MODELS.mkdir(exist_ok=True)

    for res in cfg["resolucoes"]:
        fp32 = MODELS / nome_modelo("yolov8n", "fp32", res)
        int8 = MODELS / nome_modelo("yolov8n", "int8", res)
        # A Ultralytics grava o resultado ao lado do .pt; trabalhamos em pasta temporária.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pt = tmp / "yolov8n.pt"
            if args.refazer or not fp32.exists():
                shutil.copy(FONTES / cfg["arquivo"], pt)
                saida = YOLO(pt).export(format="litert", imgsz=res)
                shutil.move(saida, fp32)
                print(f"OK {fp32.name}")
            if args.refazer or not int8.exists():
                if modo == "ultralytics":
                    shutil.copy(FONTES / cfg["arquivo"], pt)
                    saida = YOLO(pt).export(
                        format="litert", imgsz=res, quantize=8, data=str(yaml_calibracao(tmp)), fraction=1.0
                    )
                    shutil.move(saida, int8)
                else:
                    from quantizar import quantizar_inteiro_total

                    quantizar_inteiro_total(fp32, int8, "yolov8n", res)
                print(f"OK {int8.name} (modo {modo})")


if __name__ == "__main__":
    main()
