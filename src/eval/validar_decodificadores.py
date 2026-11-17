"""E5, validação: confere os decodificadores no x86 nativo antes da coleta emulada.

O que faz: roda os modelos FP32 (e, com --int8, também os INT8) sobre as 350 imagens do conjunto
de teste, em cada resolução da fonte (320, 480, 640), com o mesmo código da coleta
(src/bench/deteccao.py), e calcula mAP@50 e F1 da classe pessoa. Também conta as detecções na
imagem de teste bus.jpg (4 pessoas visíveis). Os números servem para validar a decodificação;
não são tempos e não entram na análise de desempenho.

O que gera: results/e5/validacao_decodificadores.csv
Roda no contêiner borda-prep (/opt/venv-export). Uso: python src/eval/validar_decodificadores.py [--int8]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
from comum import DATA, MODELS, RAIZ, RESULTS, ler_yaml  # noqa: E402
from deteccao import Detector, quadro_da_fonte, resolucao_entrada  # noqa: E402
from metricas import carregar_gabarito, map50, precisao_revocacao_f1  # noqa: E402

MODELOS = ["yolov8n", "ssd_mobilenet_v1", "efficientdet_lite0"]
RESOLUCOES = [320, 480, 640]


def lista_teste() -> list[dict]:
    with open(RAIZ / "configs" / "conjunto_teste.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int8", action="store_true", help="valida também os modelos INT8")
    args = ap.parse_args()

    gab = carregar_gabarito(DATA / "teste_coco" / "gabarito_pessoa.json")
    teste = lista_teste()
    bus = DATA / "teste" / ler_yaml("models.yaml")["imagem_teste"]["arquivo"]
    precisoes = ["fp32", "int8"] if args.int8 else ["fp32"]
    linhas = []
    for modelo in MODELOS:
        for precisao in precisoes:
            for res in RESOLUCOES:
                arq = MODELS / f"{modelo}_{precisao}_{resolucao_entrada(modelo, res)}.tflite"
                det = Detector(arq, modelo)
                dets = {}
                for item in teste:
                    q = quadro_da_fonte(DATA / "teste_coco" / "imagens" / item["arquivo"], res)
                    dets[int(item["image_id"])] = det.posprocessar(det.inferir(det.preprocessar(q)))
                d_bus = det.posprocessar(det.inferir(det.preprocessar(quadro_da_fonte(bus, res))))
                m = map50(dets, gab)
                p, r, f1 = precisao_revocacao_f1(dets, gab)
                linha = {"modelo": modelo, "precisao": precisao, "resolucao_fonte": res, "arquivo": arq.name,
                         "imagens": len(dets), "map50_pessoa": round(m, 4), "precisao_050": round(p, 4),
                         "revocacao_050": round(r, 4), "f1_050": round(f1, 4),
                         "bus_pessoas_pontuacao_050": int((d_bus[:, 4] >= 0.5).sum()),
                         "ambiente": "x86-64 nativo (validação)"}
                print(linha)
                linhas.append(linha)
    (RESULTS / "e5").mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "e5" / "validacao_decodificadores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print("-> results/e5/validacao_decodificadores.csv")


if __name__ == "__main__":
    main()
