"""Funções compartilhadas pelos scripts da etapa E4.

O que faz: localiza a raiz do repositório, lê os arquivos de configuração, calcula sha256,
lista as imagens de calibração em ordem fixa e prepara uma imagem no formato que cada
modelo espera. Não gera nenhum arquivo sozinho; é importado pelos outros scripts.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELS = RAIZ / "models"
DATA = RAIZ / "data"
RESULTS = RAIZ / "results"
FONTES = MODELS / "fontes"  # arquivos baixados, antes da conversão


def ler_yaml(nome: str) -> dict:
    """Lê um arquivo de configs/ (ex.: 'models.yaml')."""
    import yaml

    with open(RAIZ / "configs" / nome, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def nome_modelo(modelo: str, precisao: str, resolucao: int) -> str:
    """Nome padronizado do arquivo, ex.: yolov8n_int8_640.tflite."""
    return f"{modelo}_{precisao}_{resolucao}.tflite"


def partes_do_nome(arquivo: Path) -> tuple[str, str, int]:
    """Inverso de nome_modelo: devolve (modelo, precisão, resolução)."""
    modelo, precisao, resolucao = arquivo.stem.rsplit("_", 2)
    return modelo, precisao, int(resolucao)


def imagens_calibracao() -> list[Path]:
    """Imagens de calibração em ordem fixa (nome do arquivo). Falha se o conjunto estiver incompleto."""
    cfg = ler_yaml("models.yaml")["calibracao"]
    pasta = DATA / "calibracao" / cfg["pasta_imagens"]
    arquivos = sorted(pasta.glob("*.jpg"))
    if len(arquivos) != cfg["n_imagens"]:
        raise SystemExit(
            f"Esperava {cfg['n_imagens']} imagens de calibração em {pasta}, achei {len(arquivos)}. "
            "Rode src/prepare/baixar.py."
        )
    return arquivos


def preprocessar(caminho_imagem: Path, modelo: str, resolucao: int):
    """Carrega uma imagem e devolve um array float32 NHWC (1, H, W, 3) na escala do modelo.

    - yolov8n:            valores de 0 a 1
    - ssd_mobilenet_v1:   valores de -1 a 1  (x / 127,5 - 1)
    - efficientdet_lite0: valores de -1 a 1  ((x - 127,5) / 127,5)
    O redimensionamento é direto (bilinear), sem manter proporção. Serve para calibração e para
    o teste de formato da E4; o pré-processamento definitivo de avaliação é da E5.
    """
    import numpy as np
    from PIL import Image

    img = Image.open(caminho_imagem).convert("RGB").resize((resolucao, resolucao), Image.BILINEAR)
    x = np.asarray(img, dtype=np.float32)
    if modelo == "yolov8n":
        x = x / 255.0
    elif modelo in ("ssd_mobilenet_v1", "efficientdet_lite0"):
        x = x / 127.5 - 1.0
    else:
        raise ValueError(f"Modelo desconhecido: {modelo}")
    return x[None]
