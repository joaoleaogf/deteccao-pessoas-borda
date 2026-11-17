"""Pré-processamento, decodificação e NMS dos três modelos (classe pessoa), só com numpy e Pillow.

O que faz: transforma o quadro da fonte (RGB uint8, res x res) na entrada de cada modelo e
transforma as saídas brutas em detecções de pessoa. É usado igual na borda (contêiner ARM64),
na nuvem (servidor x86) e na validação dos decodificadores, para que as três partes meçam o
mesmo trabalho. Não gera arquivos.

Decodificadores:
  yolov8n             saída 1x84xN: cx, cy, w, h já normalizados (0..1) + 80 pontuações com sigmoide;
                      pessoa = classe 0.
  ssd_mobilenet_v1    saídas brutas do grafo do TF1 (caixas 1917x4 codificadas, logits 1917x91);
                      âncoras do pipeline.config (ssd_anchor_generator: 6 camadas, escalas 0,2 a 0,95,
                      razões 1, 2, 0,5, 3, 0,3333, reduce_boxes_in_lowest_layer), box coder
                      faster_rcnn (10, 10, 5, 5), sigmoide; pessoa = índice 1 (0 é o fundo).
  efficientdet_lite0  saídas do MediaPipe (caixas 19206x4 codificadas, 90 pontuações com sigmoide);
                      âncoras do EfficientDet, níveis 3 a 7, 3 escalas por oitava, razões 1, 2, 0,5,
                      anchor_scale 4; pessoa = índice 0.
NMS: só a classe pessoa, IoU 0,5, pontuação mínima 0,01, no máximo 100 detecções por quadro
(os mesmos valores para os três modelos).
"""
from __future__ import annotations

import math

import numpy as np

LIMIAR_PONTUACAO = 0.01
LIMIAR_IOU_NMS = 0.5
MAX_DETECCOES = 100
MAX_ANTES_NMS = 1000
ENTRADA_FIXA = {"ssd_mobilenet_v1": 300, "efficientdet_lite0": 320}


def resolucao_entrada(modelo: str, res_fonte: int) -> int:
    """Resolução da entrada do modelo: a da fonte no YOLOv8n; fixa nos outros dois (decisão D1)."""
    return ENTRADA_FIXA.get(modelo, res_fonte)


def quadro_da_fonte(caminho_imagem, res: int) -> np.ndarray:
    """Simula o quadro da câmera: a imagem redimensionada para res x res (bilinear), RGB uint8.

    Fica fora da medição de tempo: representa o quadro que a câmera entrega.
    """
    from PIL import Image

    img = Image.open(caminho_imagem).convert("RGB").resize((res, res), Image.BILINEAR)
    return np.asarray(img, dtype=np.uint8)


class Detector:
    """Envolve um modelo .tflite: pré-processamento, inferência e pós-processamento separados."""

    def __init__(self, caminho_modelo, modelo: str, num_threads: int = 4):
        from ai_edge_litert.interpreter import Interpreter

        self.modelo = modelo
        self.it = Interpreter(model_path=str(caminho_modelo), num_threads=num_threads)
        self.it.allocate_tensors()
        self.ent = self.it.get_input_details()[0]
        self.saidas = self.it.get_output_details()
        self.res_entrada = int(self.ent["shape"][2])  # NHWC: H; NCHW: C=3 em [1], então usa [2]
        if self.ent["shape"][1] != 3:
            self.res_entrada = int(self.ent["shape"][1])
        self.nchw = self.ent["shape"][1] == 3
        if modelo == "ssd_mobilenet_v1":
            self.ancoras = ancoras_ssd()
        elif modelo == "efficientdet_lite0":
            self.ancoras = ancoras_efficientdet(self.res_entrada)

    # ---- pré-processamento ----
    def preprocessar(self, quadro: np.ndarray) -> np.ndarray:
        from PIL import Image

        if quadro.shape[0] != self.res_entrada:
            quadro = np.asarray(
                Image.fromarray(quadro).resize((self.res_entrada, self.res_entrada), Image.BILINEAR)
            )
        x = quadro.astype(np.float32)
        x = x / 255.0 if self.modelo == "yolov8n" else x / 127.5 - 1.0
        x = x[None]
        if self.nchw:
            x = x.transpose(0, 3, 1, 2)
        tipo = self.ent["dtype"]
        if np.issubdtype(tipo, np.integer):
            escala, zero = self.ent["quantization"]
            info = np.iinfo(tipo)
            x = np.clip(np.round(x / escala + zero), info.min, info.max)
        return np.ascontiguousarray(x.astype(tipo))

    # ---- inferência ----
    def inferir(self, x: np.ndarray) -> list[np.ndarray]:
        self.it.set_tensor(self.ent["index"], x)
        self.it.invoke()
        return [self.it.get_tensor(s["index"]) for s in self.saidas]

    # ---- pós-processamento ----
    def _float(self, i: int, v: np.ndarray) -> np.ndarray:
        escala, zero = self.saidas[i]["quantization"]
        if np.issubdtype(v.dtype, np.integer) and escala:
            return (v.astype(np.float32) - zero) * escala
        return v.astype(np.float32)

    def posprocessar(self, saidas: list[np.ndarray]) -> np.ndarray:
        """Devolve um array (k, 5): x1, y1, x2, y2 normalizados (0..1) e pontuação de pessoa."""
        if self.modelo == "yolov8n":
            v = self._float(0, saidas[0])[0]  # 84 x N
            pont = v[4]
            sel = np.nonzero(pont >= LIMIAR_PONTUACAO)[0]
            cx, cy, w, h = v[0, sel], v[1, sel], v[2, sel], v[3, sel]
            caixas = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 1)
            pont = pont[sel]
        else:
            por_forma = {}
            for i, s in enumerate(saidas):
                por_forma[s.shape[-1]] = self._float(i, s).reshape(-1, s.shape[-1])
            cod = por_forma[4]
            if self.modelo == "ssd_mobilenet_v1":
                logit = por_forma[91][:, 1]
                pont = 1.0 / (1.0 + np.exp(-logit))
                sel = np.nonzero(pont >= LIMIAR_PONTUACAO)[0]
                caixas = decodificar_faster_rcnn(cod[sel], self.ancoras[sel], (10.0, 10.0, 5.0, 5.0))
            else:
                pont = por_forma[90][:, 0]
                sel = np.nonzero(pont >= LIMIAR_PONTUACAO)[0]
                caixas = decodificar_faster_rcnn(cod[sel], self.ancoras[sel], (1.0, 1.0, 1.0, 1.0))
            pont = pont[sel]
        return nms(caixas, pont)


def decodificar_faster_rcnn(cod: np.ndarray, anc: np.ndarray, escalas) -> np.ndarray:
    """cod = (ty, tx, th, tw); anc = (yc, xc, h, w) normalizados. Devolve x1, y1, x2, y2."""
    sy, sx, sh, sw = escalas
    yc = cod[:, 0] / sy * anc[:, 2] + anc[:, 0]
    xc = cod[:, 1] / sx * anc[:, 3] + anc[:, 1]
    h = np.exp(cod[:, 2] / sh) * anc[:, 2]
    w = np.exp(cod[:, 3] / sw) * anc[:, 3]
    return np.stack([xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2], 1)


def nms(caixas: np.ndarray, pont: np.ndarray) -> np.ndarray:
    """NMS gulosa de uma classe. Corta caixas em 0..1 antes."""
    if len(pont) == 0:
        return np.zeros((0, 5), np.float32)
    ordem = np.argsort(-pont, kind="stable")[:MAX_ANTES_NMS]
    caixas = np.clip(caixas[ordem], 0.0, 1.0)
    pont = pont[ordem]
    area = (caixas[:, 2] - caixas[:, 0]) * (caixas[:, 3] - caixas[:, 1])
    manter = []
    vivos = np.ones(len(pont), bool)
    for i in range(len(pont)):
        if not vivos[i]:
            continue
        manter.append(i)
        if len(manter) >= MAX_DETECCOES:
            break
        xx1 = np.maximum(caixas[i, 0], caixas[i + 1:, 0])
        yy1 = np.maximum(caixas[i, 1], caixas[i + 1:, 1])
        xx2 = np.minimum(caixas[i, 2], caixas[i + 1:, 2])
        yy2 = np.minimum(caixas[i, 3], caixas[i + 1:, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        iou = inter / np.maximum(area[i] + area[i + 1:] - inter, 1e-12)
        vivos[i + 1:] &= iou <= LIMIAR_IOU_NMS
    m = np.array(manter)
    return np.concatenate([caixas[m], pont[m, None]], 1).astype(np.float32)


def ancoras_ssd(num_camadas: int = 6, esc_min: float = 0.2, esc_max: float = 0.95,
                razoes=(1.0, 2.0, 0.5, 3.0, 0.3333), mapas=(19, 10, 5, 3, 2, 1)) -> np.ndarray:
    """Âncoras do ssd_anchor_generator do TF Object Detection API (yc, xc, h, w), normalizadas."""
    escalas = [esc_min + (esc_max - esc_min) * i / (num_camadas - 1) for i in range(num_camadas)] + [1.0]
    todas = []
    for camada, fm in enumerate(mapas):
        if camada == 0:  # reduce_boxes_in_lowest_layer
            formas = [(0.1, 1.0), (escalas[0], 2.0), (escalas[0], 0.5)]
        else:
            formas = [(escalas[camada], r) for r in razoes]
            formas.append((math.sqrt(escalas[camada] * escalas[camada + 1]), 1.0))
        for y in range(fm):
            for x in range(fm):
                for esc, r in formas:
                    todas.append(((y + 0.5) / fm, (x + 0.5) / fm, esc / math.sqrt(r), esc * math.sqrt(r)))
    return np.array(todas, np.float32)


def ancoras_efficientdet(res: int, nivel_min: int = 3, nivel_max: int = 7, escalas_por_oitava: int = 3,
                         razoes=(1.0, 2.0, 0.5), escala_ancora: float = 4.0) -> np.ndarray:
    """Âncoras multiescala do EfficientDet (yc, xc, h, w), normalizadas pela resolução de entrada.

    Mapa de cada nível = teto(res / 2^nível); centros em (i + 0,5) / tamanho do mapa.
    """
    todas = []
    for nivel in range(nivel_min, nivel_max + 1):
        passo = 2 ** nivel
        fm = math.ceil(res / passo)
        formas = []
        for oitava in range(escalas_por_oitava):
            base = escala_ancora * passo * 2 ** (oitava / escalas_por_oitava)
            for r in razoes:
                ax = math.sqrt(r)
                formas.append((base / ax / res, base * ax / res))  # (h, w)
        for y in range(fm):
            for x in range(fm):
                for h, w in formas:
                    todas.append(((y + 0.5) / fm, (x + 0.5) / fm, h, w))
    return np.array(todas, np.float32)
