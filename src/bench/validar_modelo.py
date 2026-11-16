"""E4, passo 6: valida cada modelo dentro do contêiner ARM64.

O que faz: para cada models/*.tflite, carrega o modelo com o Interpreter do LiteRT, prepara a
imagem de teste no formato da entrada (layout NHWC ou NCHW, float ou inteiro quantizado),
roda UMA inferência e confere formato e tipo dos tensores e se a saída é válida (sem NaN e
não constante). O tempo dessa inferência é anotado só como referência: é de ambiente
emulado, inclui efeitos de primeira execução e NÃO é medição do experimento.

O que gera:
  results/validacao_arm64.csv     uma linha por modelo
  results/ambiente/arm64.txt      arquitetura e versões dentro do contêiner

Termina com erro se a arquitetura não for aarch64 ou se algum modelo falhar.
Roda no contêiner borda-arm64.
"""
from __future__ import annotations

import argparse
import csv
import platform
import sys
import time
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import DATA, MODELS, RESULTS, ler_yaml, partes_do_nome, preprocessar  # noqa: E402


def entrada_para(detalhe: dict, modelo: str, res: int, imagem: Path):
    """Monta o tensor de entrada: ajusta o layout e, se a entrada for inteira, quantiza."""
    import numpy as np

    x = preprocessar(imagem, modelo, res)  # float32, NHWC
    if detalhe["shape"][1] == 3:  # modelo espera NCHW (caso do YOLOv8n exportado)
        x = np.ascontiguousarray(x.transpose(0, 3, 1, 2))
    tipo = detalhe["dtype"]
    if np.issubdtype(tipo, np.integer):
        escala, zero = detalhe["quantization"]
        info = np.iinfo(tipo)
        x = np.clip(np.round(x / escala + zero), info.min, info.max)
    return x.astype(tipo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--qualquer-arquitetura", action="store_true", help="não exige aarch64 (só para depurar)")
    args = ap.parse_args()

    import numpy as np
    from ai_edge_litert.interpreter import Interpreter

    arq_maquina = platform.machine()
    if arq_maquina != "aarch64" and not args.qualquer_arquitetura:
        raise SystemExit(f"Arquitetura {arq_maquina}: este script deve rodar no contêiner ARM64 (aarch64).")

    (RESULTS / "ambiente").mkdir(parents=True, exist_ok=True)
    (RESULTS / "ambiente" / "arm64.txt").write_text(
        f"arquitetura (platform.machine): {arq_maquina}\n"
        f"sistema: {platform.platform()}\n"
        f"python: {platform.python_version()}\n"
        + "".join(f"{p}: {version(p)}\n" for p in ("ai-edge-litert", "numpy", "pillow", "psutil")),
        encoding="utf-8",
    )

    imagem = DATA / "teste" / ler_yaml("models.yaml")["imagem_teste"]["arquivo"]
    linhas, falhas = [], []
    for arq in sorted(MODELS.glob("*.tflite")):
        modelo, precisao, res = partes_do_nome(arq)
        linha = {"arquivo": arq.name, "modelo": modelo, "precisao": precisao, "resolucao": res,
                 "arquitetura": arq_maquina, "ok": False, "erro": ""}
        try:
            it = Interpreter(model_path=str(arq))
            it.allocate_tensors()
            ent = it.get_input_details()[0]
            it.set_tensor(ent["index"], entrada_para(ent, modelo, res, imagem))
            t0 = time.perf_counter()
            it.invoke()
            ms = (time.perf_counter() - t0) * 1000
            saidas = [(s, it.get_tensor(s["index"])) for s in it.get_output_details()]
            valida = all(np.isfinite(v).all() and v.min() != v.max() for _, v in saidas)
            linha.update(
                entrada_formato="x".join(map(str, ent["shape"])),
                entrada_tipo=ent["dtype"].__name__,
                saidas_formato=";".join("x".join(map(str, v.shape)) for _, v in saidas),
                saidas_tipo=";".join(v.dtype.name for _, v in saidas),
                saida_valida=valida,
                primeira_inferencia_ms_emulado=f"{ms:.1f}",
                ok=valida,
            )
            if not valida:
                linha["erro"] = "saída com NaN/infinito ou constante"
        except Exception as e:  # registra a falha e segue para o próximo modelo
            linha["erro"] = f"{type(e).__name__}: {e}"
        if not linha["ok"]:
            falhas.append(arq.name)
        print(("OK   " if linha["ok"] else "FALHA"), arq.name, linha["erro"])
        linhas.append(linha)

    if not linhas:
        raise SystemExit("Nenhum modelo em models/.")
    campos = ["arquivo", "modelo", "precisao", "resolucao", "arquitetura", "ok", "erro", "entrada_formato",
              "entrada_tipo", "saidas_formato", "saidas_tipo", "saida_valida", "primeira_inferencia_ms_emulado"]
    with open(RESULTS / "validacao_arm64.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} modelos -> results/validacao_arm64.csv")
    if falhas:
        raise SystemExit(f"{len(falhas)} modelo(s) falharam: {', '.join(falhas)}")


if __name__ == "__main__":
    main()
