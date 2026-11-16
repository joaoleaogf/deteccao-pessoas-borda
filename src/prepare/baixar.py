"""E4, passo 2 (parte 1): baixa os arquivos de origem e confere o sha256 de cada um.

O que faz: lê configs/models.yaml e baixa (a) os pesos/grafos originais dos 3 modelos,
(b) o conjunto de calibração COCO128 e (c) a imagem de teste. Arquivo já baixado e com
hash correto não é baixado de novo.

O que gera:
  models/fontes/<arquivos originais>      pesos e grafos como publicados
  models/fontes/origens.json              url, sha256 e data de cada download
  data/calibracao/coco128/...             128 imagens de calibração
  data/teste/bus.jpg                      imagem do teste de formato

Roda no contêiner de preparação (qualquer um dos dois ambientes Python).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import DATA, FONTES, ler_yaml, sha256  # noqa: E402


def baixar(url: str, destino: Path, hash_esperado: str) -> dict:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and sha256(destino) == hash_esperado:
        print(f"  já existe e confere: {destino.name}")
    else:
        print(f"  baixando {url}")
        tmp = destino.with_suffix(destino.suffix + ".parcial")
        with urllib.request.urlopen(url) as resp, open(tmp, "wb") as f:
            while bloco := resp.read(1 << 20):
                f.write(bloco)
        obtido = sha256(tmp)
        if obtido != hash_esperado:
            tmp.unlink()
            raise SystemExit(
                f"sha256 diferente para {url}\n  esperado: {hash_esperado}\n  obtido:   {obtido}\n"
                "O arquivo remoto mudou. Confira a origem antes de atualizar configs/models.yaml."
            )
        tmp.replace(destino)
    return {"url": url, "sha256": hash_esperado, "arquivo": destino.name}


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg = ler_yaml("models.yaml")
    origens = {}

    print("Modelos:")
    for nome, m in cfg["modelos"].items():
        origens[nome] = baixar(m["url"], FONTES / m["arquivo"], m["sha256"])
    # O SSD vem em .tar.gz; só o grafo congelado é usado.
    tgz = FONTES / cfg["modelos"]["ssd_mobilenet_v1"]["arquivo"]
    pb = FONTES / "ssd_mobilenet_v1_frozen_inference_graph.pb"
    if not pb.exists():
        with tarfile.open(tgz) as t:
            membro = next(m for m in t.getmembers() if m.name.endswith("frozen_inference_graph.pb"))
            pb.write_bytes(t.extractfile(membro).read())
    origens["ssd_mobilenet_v1"]["grafo_extraido"] = {"arquivo": pb.name, "sha256": sha256(pb)}

    print("Calibração:")
    cal = cfg["calibracao"]
    zip_cal = DATA / "calibracao" / "coco128.zip"
    origens["calibracao"] = baixar(cal["url"], zip_cal, cal["sha256"])
    if not (DATA / "calibracao" / cal["pasta_imagens"]).exists():
        with zipfile.ZipFile(zip_cal) as z:
            z.extractall(DATA / "calibracao")

    print("Imagem de teste:")
    t = cfg["imagem_teste"]
    origens["imagem_teste"] = baixar(t["url"], DATA / "teste" / t["arquivo"], t["sha256"])

    origens["_baixado_em_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (FONTES / "origens.json").write_text(json.dumps(origens, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Registro gravado em {FONTES / 'origens.json'}")


if __name__ == "__main__":
    main()
