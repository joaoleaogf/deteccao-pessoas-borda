"""Etapas do roteiro de aula (demo/roteiro.sh) que mostram informações dos modelos e da qualidade.

O que faz, conforme o subcomando:
  origens    de onde vem cada modelo (pesos pré-treinados no COCO; o projeto não treina nada) e se
             os arquivos baixados conferem com o sha256 de configs/models.yaml
  tamanhos   tamanho de cada modelo FP32 e INT8, tipo da entrada e da saída e quantos tensores
             float32 sobraram (lido do próprio .tflite com o LiteRT)
  map        mAP@50 da classe pessoa, precisão, revocação e F1 num subconjunto das 350 imagens do
             conjunto de teste, com o mesmo código da E5 (src/bench/deteccao.py e src/eval/metricas.py),
             ao lado do valor do artigo (350 imagens, results/e5/qualidade.csv)
Não grava nada em results/ (o results/modelos.csv do projeto não é tocado).

Uso: python demo/etapas.py origens | tamanhos | map [--imagens 100] [--res 320]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_demo import (DATA, MODELOS, MODELS, NOMES, PASTA_COCO, PRECISOES, RESOLUCOES,  # noqa: E402
                        Detectores, arquivo_modelo, lista_teste, quadro_da_fonte, referencia_artigo)

COMO_INT8 = {
    "yolov8n": "export oficial da Ultralytics (quantize=8), calibrado no COCO128; INT8 'híbrido': "
               "entrada, saída e cabeça ficam em float32 (decisão D2)",
    "ssd_mobilenet_v1": "quantização pós-treinamento do TensorFlow Lite (inteiro total), calibrada no COCO128",
    "efficientdet_lite0": "quantização pós-treinamento com ai-edge-quantizer (inteiro total), calibrada no COCO128",
}
COMO_FP32 = {
    "yolov8n": "pesos PyTorch yolov8n.pt (Ultralytics, treinados no COCO) exportados para .tflite em 320, 480 e 640",
    "ssd_mobilenet_v1": "grafo congelado do TF1 Detection Model Zoo (treinado no COCO) convertido para .tflite (300x300)",
    "efficientdet_lite0": "arquivo .tflite float32 publicado pelo MediaPipe (treinado no COCO), usado sem alteração (320x320)",
}


def origens(_args) -> None:
    from comum import FONTES, ler_yaml, sha256

    cfg = ler_yaml("models.yaml")
    print("ORIGEM DOS MODELOS")
    print("O projeto NÃO treina nenhum modelo: os três vêm pré-treinados no COCO (80 classes, inclusive")
    print("pessoa). O trabalho do projeto é converter, quantizar (FP32 -> INT8), medir e avaliar.\n")
    for nome, m in cfg["modelos"].items():
        arq = FONTES / m["arquivo"]
        estado = "não baixado"
        if arq.exists():
            estado = "sha256 confere" if sha256(arq) == m["sha256"] else "sha256 DIFERENTE"
        print(f"{NOMES[nome]}")
        print(f"  origem:  {m['url']}")
        print(f"  arquivo: models/fontes/{m['arquivo']} ({estado})")
        print(f"  FP32:    {COMO_FP32[nome]}")
        print(f"  INT8:    {COMO_INT8[nome]}\n")
    cal = cfg["calibracao"]
    n = len(list((DATA / "calibracao" / cal["pasta_imagens"]).glob("*.jpg")))
    print(f"Calibração da quantização: COCO128 ({n} imagens em data/calibracao/{cal['pasta_imagens']}),")
    print("as mesmas e na mesma ordem para os três modelos. Não se sobrepõe ao conjunto de teste (COCO val2017).")
    reg = FONTES / "origens.json"
    if reg.exists():
        print(f"Baixado em (UTC): {json.loads(reg.read_text(encoding='utf-8')).get('_baixado_em_utc')}")


def _descrever(arq: Path) -> dict:
    from ai_edge_litert.interpreter import Interpreter

    it = Interpreter(model_path=str(arq))
    it.allocate_tensors()
    tipos = Counter(t["dtype"].__name__ for t in it.get_tensor_details())
    return {
        "bytes": arq.stat().st_size,
        "entrada": it.get_input_details()[0]["dtype"].__name__,
        "saida": ",".join(sorted({s["dtype"].__name__ for s in it.get_output_details()})),
        "float32": tipos.get("float32", 0),
        "total": sum(tipos.values()),
    }


def tamanhos(_args) -> None:
    print("TAMANHO DOS MODELOS: FP32 (antes) x INT8 (depois da quantização)")
    cab = (f"{'modelo':<19}{'entrada':>8}  {'FP32 MB':>8}  {'INT8 MB':>8}  {'redução':>8}  "
           f"{'INT8 entrada/saída':<20}{'tensores float32 no INT8':>25}")
    print(cab)
    print("-" * len(cab))
    vistos = set()
    for modelo in MODELOS:
        for res in RESOLUCOES:
            f32, i8 = arquivo_modelo(modelo, "fp32", res), arquivo_modelo(modelo, "int8", res)
            if f32 in vistos:
                continue
            vistos.add(f32)
            a = _descrever(f32) if f32.exists() else None
            b = _descrever(i8) if i8.exists() else None
            ent = f32.stem.rsplit("_", 1)[1]
            ta = f"{a['bytes'] / 2**20:8.2f}" if a else f"{'falta':>8}"
            tb = f"{b['bytes'] / 2**20:8.2f}" if b else f"{'—':>8}"
            red = f"{a['bytes'] / b['bytes']:7.2f}x" if a and b else f"{'—':>8}"
            es = f"{b['entrada']}/{b['saida']}" if b else "—"
            fl = f"{b['float32']} de {b['total']}" if b else "—"
            print(f"{NOMES[modelo]:<19}{ent:>8}  {ta}  {tb}  {red}  {es:<20}{fl:>25}")
    print("\nINT8 'inteiro total' = nenhum tensor float32. O YOLOv8n INT8 é híbrido de propósito (decisão D2).")


def avaliar_map(args) -> None:
    from metricas import carregar_gabarito, map50, precisao_revocacao_f1

    gab_arq = DATA / "teste_coco" / "gabarito_pessoa.json"
    if not gab_arq.exists():
        raise SystemExit("Falta o conjunto de teste. Rode scripts/setup_macos.sh.")
    gab = carregar_gabarito(gab_arq)
    teste = lista_teste()[: args.imagens]
    print(f"mAP@50 DA CLASSE PESSOA — {len(teste)} das 350 imagens do conjunto de teste (COCO val2017),")
    print(f"fonte {args.res}x{args.res}, mesmo pré/pós-processamento e NMS da coleta (src/bench/deteccao.py).")
    print("Coluna 'artigo': valor da borda em results/e5/qualidade.csv, sempre com as 350 imagens;")
    print("com menos imagens o número do Mac é uma amostra e pode diferir.\n")
    quadros = [quadro_da_fonte(PASTA_COCO / t["arquivo"], args.res) for t in teste]
    dets = Detectores(args.threads)
    cab = f"{'modelo':<19}{'prec.':<6}{'mAP@50':>8}{'precisão':>10}{'revocação':>11}{'F1':>7}  {'artigo mAP@50':>14}  {'tempo':>6}"
    print(cab)
    print("-" * len(cab))
    for modelo in MODELOS:
        for precisao in PRECISOES:
            t0 = time.perf_counter()
            det = dets.obter(modelo, precisao, args.res)
            res = {int(t["image_id"]): det.posprocessar(det.inferir(det.preprocessar(q)))
                   for t, q in zip(teste, quadros)}
            m = map50(res, gab)
            p, r, f1 = precisao_revocacao_f1(res, gab)
            ref = referencia_artigo(modelo, precisao, args.res)
            art = f"{ref['map50']:.4f}" if ref and ref["map50"] is not None else "—"
            print(f"{NOMES[modelo]:<19}{precisao.upper():<6}{m:>8.4f}{p:>10.4f}{r:>11.4f}{f1:>7.4f}  {art:>14}  "
                  f"{time.perf_counter() - t0:>5.1f}s")
    print("\nPrecisão, revocação e F1 com pontuação >= 0,5 e IoU 0,5 (como no artigo).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("origens")
    sub.add_parser("tamanhos")
    m = sub.add_parser("map")
    m.add_argument("--imagens", type=int, default=100, help="quantas das 350 imagens (padrão 100)")
    m.add_argument("--res", type=int, choices=RESOLUCOES, default=320)
    m.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()
    {"origens": origens, "tamanhos": tamanhos, "map": avaliar_map}[args.cmd](args)


if __name__ == "__main__":
    _ = MODELS
    main()
