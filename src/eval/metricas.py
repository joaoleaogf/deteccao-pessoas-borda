"""Métricas de qualidade da detecção de pessoas: mAP@50 (pycocotools) e precisão, revocação e F1.

O que faz: recebe as detecções de uma combinação (normalizadas 0..1, por image_id) e o gabarito
data/teste_coco/gabarito_pessoa.json e calcula:
  map50       AP da classe pessoa com IoU 0,5 (COCOeval, área "all", até 100 detecções)
  precisao, revocacao, f1   com limiar de pontuação 0,5 e IoU 0,5 (casamento guloso por pontuação)
Não gera arquivos; é importado por validar_decodificadores.py e pela análise.
Roda onde houver pycocotools (contêiner borda-prep).
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import numpy as np

LIMIAR_F1 = 0.5


def carregar_gabarito(caminho: Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def para_coco(deteccoes: dict[int, np.ndarray], gabarito: dict) -> list[dict]:
    """deteccoes[image_id] = array (k, 5) normalizado -> lista no formato de resultados do COCO."""
    tam = {im["id"]: (im["width"], im["height"]) for im in gabarito["images"]}
    saida = []
    for iid, d in deteccoes.items():
        w, h = tam[iid]
        for x1, y1, x2, y2, s in np.asarray(d).reshape(-1, 5):
            saida.append({"image_id": int(iid), "category_id": 1,
                          "bbox": [float(x1 * w), float(y1 * h), float((x2 - x1) * w), float((y2 - y1) * h)],
                          "score": float(s)})
    return saida


def map50(deteccoes: dict[int, np.ndarray], gabarito: dict) -> float:
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    with contextlib.redirect_stdout(io.StringIO()):
        gt = COCO()
        gt.dataset = gabarito
        gt.createIndex()
        res = para_coco(deteccoes, gabarito)
        if not res:
            return 0.0
        dt = gt.loadRes(res)
        ev = COCOeval(gt, dt, "bbox")
        ev.params.imgIds = sorted(int(i) for i in deteccoes)
        ev.evaluate()
        ev.accumulate()
        ev.summarize()
    return float(ev.stats[1])  # AP @ IoU 0,5


def _iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    ab = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(aa[:, None] + ab[None, :] - inter, 1e-12)


def precisao_revocacao_f1(deteccoes: dict[int, np.ndarray], gabarito: dict) -> tuple[float, float, float]:
    tam = {im["id"]: (im["width"], im["height"]) for im in gabarito["images"]}
    gts: dict[int, list] = {}
    for a in gabarito["annotations"]:
        x, y, w, h = a["bbox"]
        gts.setdefault(a["image_id"], []).append([x, y, x + w, y + h])
    vp = fp = fn = 0
    for iid in deteccoes:
        w, h = tam[iid]
        d = np.asarray(deteccoes[iid]).reshape(-1, 5)
        d = d[d[:, 4] >= LIMIAR_F1]
        d = d[np.argsort(-d[:, 4], kind="stable")]
        caixas = d[:, :4] * np.array([w, h, w, h])
        g = np.array(gts.get(iid, []), dtype=np.float64).reshape(-1, 4)
        usado = np.zeros(len(g), bool)
        if len(g) and len(caixas):
            iou = _iou(caixas, g)
            for i in range(len(caixas)):
                cand = np.where(~usado & (iou[i] >= 0.5))[0]
                if len(cand):
                    usado[cand[np.argmax(iou[i, cand])]] = True
                    vp += 1
                else:
                    fp += 1
        else:
            fp += len(caixas)
        fn += int((~usado).sum())
    p = vp / (vp + fp) if vp + fp else 0.0
    r = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f1
