"""Funções compartilhadas pela demonstração em aula (demo/).

O que faz: localiza os modelos e as imagens do projeto e cria os detectores. Toda a lógica de
pré-processamento, inferência, decodificação e NMS vem de src/bench/deteccao.py, a mesma usada na
coleta da E5; aqui só há a ligação com a câmera e a tela. Não gera arquivos.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
sys.path.insert(0, str(DEMO.parent / "src"))
sys.path.insert(0, str(DEMO.parent / "src" / "bench"))
sys.path.insert(0, str(DEMO.parent / "src" / "eval"))

from comum import DATA, MODELS, RAIZ, RESULTS, nome_modelo  # noqa: E402,F401
from deteccao import Detector, quadro_da_fonte, resolucao_entrada  # noqa: E402,F401

MODELOS = ["yolov8n", "ssd_mobilenet_v1", "efficientdet_lite0"]
PRECISOES = ["fp32", "int8"]
RESOLUCOES = [320, 480, 640]
NOMES = {"yolov8n": "YOLOv8n", "ssd_mobilenet_v1": "SSD-MobileNet V1", "efficientdet_lite0": "EfficientDet-Lite0"}
PASTA_COCO = DATA / "teste_coco" / "imagens"


def arquivo_modelo(modelo: str, precisao: str, res_fonte: int) -> Path:
    """Arquivo .tflite usado para a resolução da fonte (decisão D1: SSD 300 e EfficientDet 320 fixos)."""
    return MODELS / nome_modelo(modelo, precisao, resolucao_entrada(modelo, res_fonte))


def conferir_modelos() -> list[Path]:
    """Lista os modelos que faltam (deve estar vazia depois do scripts/setup_macos.sh)."""
    faltam = []
    for m in MODELOS:
        for p in PRECISOES:
            for r in RESOLUCOES:
                a = arquivo_modelo(m, p, r)
                if not a.exists() and a not in faltam:
                    faltam.append(a)
    return faltam


def lista_teste() -> list[dict]:
    """As 350 imagens do conjunto de teste da E5, na ordem do configs/conjunto_teste.csv."""
    with open(RAIZ / "configs" / "conjunto_teste.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Detectores:
    """Cache de detectores: trocar de modelo em aula não recarrega o que já foi aberto."""

    def __init__(self, threads: int):
        self.threads = threads
        self._cache: dict[Path, Detector] = {}

    def obter(self, modelo: str, precisao: str, res_fonte: int) -> Detector:
        arq = arquivo_modelo(modelo, precisao, res_fonte)
        if arq not in self._cache:
            if not arq.exists():
                raise SystemExit(f"Modelo não encontrado: {arq}. Rode scripts/setup_macos.sh.")
            self._cache[arq] = Detector(arq, modelo, num_threads=self.threads)
        return self._cache[arq]


def referencia_artigo(modelo: str, precisao: str, res_fonte: int) -> dict | None:
    """Números da coleta do artigo para a mesma combinação, lidos dos arquivos de resultados.

    Latência: média dos quadros válidos (sem aquecimento) de results/e5/borda/<comb>/quadros.csv.
    mAP@50: results/e5/qualidade.csv (parte borda, 350 imagens). Nada é calculado à parte.
    """
    import json

    comb = f"{modelo}_{precisao}_{res_fonte}"
    pasta = RESULTS / "e5" / "borda" / comb
    if not (pasta / "quadros.csv").exists():
        return None
    with open(pasta / "quadros.csv", encoding="utf-8") as f:
        validos = [l for l in csv.DictReader(f) if l["aquecimento"] == "False"]
    ref = {
        "e2e_ms": sum(float(l["t_e2e_ms"]) for l in validos) / len(validos),
        "infer_ms": sum(float(l["t_infer_ms"]) for l in validos) / len(validos),
        "ambiente": json.loads((pasta / "manifesto.json").read_text(encoding="utf-8")).get("ambiente", ""),
        "map50": None,
    }
    with open(RESULTS / "e5" / "qualidade.csv", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            if l["parte"] == "borda" and l["combinacao"] == comb:
                ref["map50"] = float(l["map50_pessoa"])
    return ref
