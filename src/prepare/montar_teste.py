"""E5, preparação: monta o conjunto de teste (350 imagens do COCO val2017 com pessoa).

O que faz: baixa as anotações do COCO 2017, escolhe as imagens pela regra de configs/teste.yaml
(1, 2 e 3+ pessoas, primeiras por id, sem anotação "iscrowd" de pessoa), baixa cada imagem e
grava o gabarito só da classe pessoa no formato COCO. Na primeira execução anota o sha256 do
zip de anotações em configs/teste.yaml; nas seguintes confere. Se configs/conjunto_teste.csv já
existir, a lista é refeita e comparada com ele: se mudar, para com erro.

O que gera:
  configs/conjunto_teste.csv            ordem, id, arquivo, largura, altura, pessoas, grupo, sha256
  data/teste_coco/imagens/<id>.jpg      as 350 imagens (fora do git)
  data/teste_coco/gabarito_pessoa.json  anotações de pessoa das 350 imagens (formato COCO)

Roda no contêiner borda-prep (/opt/venv-export). Uso: python src/prepare/montar_teste.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import DATA, RAIZ, ler_yaml, sha256  # noqa: E402

PASTA = DATA / "teste_coco"
LISTA = RAIZ / "configs" / "conjunto_teste.csv"


def baixar(url: str, destino: Path) -> None:
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        while bloco := r.read(1 << 20):
            f.write(bloco)
    tmp.replace(destino)


def grupo(n: int) -> str:
    return str(n) if n < 3 else "3+"


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg = ler_yaml("teste.yaml")
    PASTA.mkdir(parents=True, exist_ok=True)

    zip_anot = PASTA / "annotations_trainval2017.zip"
    if not zip_anot.exists():
        print("Baixando anotações do COCO 2017 (~240 MB)")
        baixar(cfg["anotacoes"]["url"], zip_anot)
    h = sha256(zip_anot)
    esperado = cfg["anotacoes"]["sha256"]
    if esperado is None:
        caminho = RAIZ / "configs" / "teste.yaml"
        texto = caminho.read_text(encoding="utf-8")
        texto = re.sub(r"sha256: null.*", f"sha256: {h}   # anotado por montar_teste.py", texto, count=1)
        caminho.write_text(texto, encoding="utf-8")
        print(f"sha256 das anotações anotado em configs/teste.yaml: {h}")
    elif h != esperado:
        raise SystemExit(f"sha256 das anotações mudou: esperado {esperado}, obtido {h}")

    with zipfile.ZipFile(zip_anot) as z:
        coco = json.loads(z.read(cfg["anotacoes"]["membro"]))
    pessoa = cfg["categoria_pessoa"]
    anots: dict[int, list] = {}
    crowd: set[int] = set()
    for a in coco["annotations"]:
        if a["category_id"] != pessoa:
            continue
        if a["iscrowd"]:
            crowd.add(a["image_id"])
        anots.setdefault(a["image_id"], []).append(a)
    imagens = {im["id"]: im for im in coco["images"]}

    escolhidas = []
    for g, n in cfg["por_grupo"].items():
        ids = sorted(i for i in anots if i not in crowd and grupo(len(anots[i])) == g)
        escolhidas += ids[:n]
    escolhidas.sort()
    print(f"{len(escolhidas)} imagens escolhidas")

    pasta_img = PASTA / "imagens"
    pasta_img.mkdir(exist_ok=True)

    def obter(i: int) -> None:
        arq = pasta_img / imagens[i]["file_name"]
        if not arq.exists():
            baixar(cfg["url_imagens"] + imagens[i]["file_name"], arq)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(obter, escolhidas))

    linhas = []
    for ordem, i in enumerate(escolhidas):
        im = imagens[i]
        linhas.append({"ordem": ordem, "image_id": i, "arquivo": im["file_name"], "largura": im["width"],
                       "altura": im["height"], "pessoas": len(anots[i]), "grupo": grupo(len(anots[i])),
                       "sha256": sha256(pasta_img / im["file_name"])})
    if LISTA.exists():
        with open(LISTA, encoding="utf-8") as f:
            antigas = list(csv.DictReader(f))
        if [{k: str(v) for k, v in l.items()} for l in linhas] != antigas:
            raise SystemExit("A lista refeita difere de configs/conjunto_teste.csv. Confira antes de seguir.")
        print("Lista confere com configs/conjunto_teste.csv")
    else:
        with open(LISTA, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0]))
            w.writeheader()
            w.writerows(linhas)
        print(f"Lista gravada em {LISTA.relative_to(RAIZ)}")

    gab = {
        "info": {"descricao": "COCO val2017, só pessoa, 350 imagens da E5"},
        "images": [imagens[i] for i in escolhidas],
        "annotations": [a for i in escolhidas for a in anots[i]],
        "categories": [c for c in coco["categories"] if c["id"] == pessoa],
    }
    (PASTA / "gabarito_pessoa.json").write_text(json.dumps(gab), encoding="utf-8")
    contagem = {g: sum(1 for l in linhas if l["grupo"] == g) for g in cfg["por_grupo"]}
    print(f"Gabarito: {len(gab['annotations'])} pessoas; grupos {contagem}")


if __name__ == "__main__":
    main()
