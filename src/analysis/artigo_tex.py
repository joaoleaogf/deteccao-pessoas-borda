"""E6, passo 3: gera as tabelas LaTeX e as macros de números para o artigo, a partir dos CSVs.

O que faz: lê results/summary.csv, results/e5/qualidade.csv, results/stats/fp32_x_int8_borda.csv e
results/edgetpu_compile.csv e escreve tabelas prontas para \\input{} e um arquivo de macros com os
números citados no texto (nenhum número é digitado à mão no rascunho: o texto usa as macros).
Nomes das macros: \\<métrica><Modelo><Precisão><Resolução>, por exemplo \\mapYoloFpSeis
(mAP@50, YOLOv8n, FP32, fonte 640). Modelos: Yolo, Ssd, Effdet; precisão: Fp, Int; resolução:
Tres (320), Quatro (480), Seis (640). Valor ausente vira "--".

O que gera: docs/artigo/tabelas/*.tex e docs/artigo/numeros.tex
Roda no contêiner borda-prep (/opt/venv-export). Uso: python src/analysis/artigo_tex.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import RAIZ, RESULTS  # noqa: E402

SAIDA = RAIZ / "docs" / "artigo"
NOMES = {"yolov8n": "YOLOv8n", "ssd_mobilenet_v1": "SSD-MobileNet V1", "efficientdet_lite0": "EfficientDet-Lite0"}
MAC_M = {"yolov8n": "Yolo", "ssd_mobilenet_v1": "Ssd", "efficientdet_lite0": "Effdet"}
MAC_P = {"fp32": "Fp", "int8": "Int"}
MAC_R = {"320": "Tres", "480": "Quatro", "640": "Seis"}
MAC_F = {"5": "Cinco", "15": "Quinze", "30": "Trinta"}


def ler(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def br(v, casas: int = 1) -> str:
    """Número com vírgula decimal (artigo em português)."""
    if v in (None, ""):
        return "--"
    try:
        return f"{float(v):.{casas}f}".replace(".", ",")
    except ValueError:
        return str(v)


def tabela(nome: str, legenda: str, cabecalho: list[str], linhas: list[list[str]], alinhamento: str,
           nota: str = "") -> None:
    corpo = [r"\begin{table}[htbp]", r"\centering", r"\footnotesize", rf"\caption{{{legenda}}}",
             rf"\label{{tab:{nome}}}", rf"\begin{{tabular}}{{{alinhamento}}}", r"\hline",
             " & ".join(cabecalho) + r" \\", r"\hline"]
    corpo += [" & ".join(l) + r" \\" for l in linhas] or [r"\multicolumn{" + str(len(cabecalho)) + r"}{c}{(sem dados)} \\"]
    corpo += [r"\hline", r"\end{tabular}"]
    if nota:
        corpo += [rf"\par\smallskip\parbox{{0.95\linewidth}}{{\scriptsize {nota}}}"]
    corpo += [r"\end{table}", ""]
    (SAIDA / "tabelas").mkdir(parents=True, exist_ok=True)
    (SAIDA / "tabelas" / f"{nome}.tex").write_text("% Gerado por src/analysis/artigo_tex.py. Não edite à mão.\n"
                                                   + "\n".join(corpo), encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    summary = ler(RESULTS / "summary.csv")
    qual = ler(RESULTS / "e5" / "qualidade.csv")
    testes = [t for t in ler(RESULTS / "stats" / "fp32_x_int8_borda.csv") if t.get("metrica")]
    etpu = ler(RESULTS / "edgetpu_compile.csv")
    ordem = lambda l: (list(NOMES).index(l["modelo"]), l.get("precisao", ""), int(l["resolucao_fonte"]))  # noqa: E731
    s15 = sorted([l for l in summary if l["fps_fonte"] == "15"], key=ordem)
    macros: dict[str, str] = {}

    # Qualidade
    linhas = []
    for q in sorted(qual, key=lambda q: (q["parte"], *ordem(q))):
        linhas.append([q["parte"], NOMES[q["modelo"]], q["precisao"].upper(), q["resolucao_fonte"],
                       br(q["map50_pessoa"], 3), br(q["f1_050"], 3)])
        macros[f"map{MAC_M[q['modelo']]}{MAC_P[q['precisao']]}{MAC_R[q['resolucao_fonte']]}"
               + ("Nuvem" if q["parte"] == "nuvem" else "")] = br(q["map50_pessoa"], 3)
    tabela("qualidade", "Qualidade da detecção de pessoas (mAP@50 e F1 com limiar 0,5) nas 350 imagens do COCO val2017.",
           ["Parte", "Modelo", "Precisão", "Resolução", "mAP@50", "F1"], linhas, "llllrr")

    # Latência na borda
    linhas = []
    for m in NOMES:
        for r in ("320", "480", "640"):
            fp = next((l for l in s15 if l["parte"] == "borda" and l["modelo"] == m and l["resolucao_fonte"] == r
                       and l["precisao"] == "fp32"), None)
            it = next((l for l in s15 if l["parte"] == "borda" and l["modelo"] == m and l["resolucao_fonte"] == r
                       and l["precisao"] == "int8"), None)
            if not (fp or it):
                continue
            cel = lambda l: (f"{br(l['t_e2e_ms_media'], 1)} [{br(l['t_e2e_ms_ic95_inf'], 1)}; "  # noqa: E731
                             f"{br(l['t_e2e_ms_ic95_sup'], 1)}]") if l else "--"
            razao = br(float(fp["t_e2e_ms_media"]) / float(it["t_e2e_ms_media"]), 1) if (fp and it) else "--"
            linhas.append([NOMES[m], r, cel(fp), cel(it), razao])
            for l in (fp, it):
                if l:
                    k = f"{MAC_M[m]}{MAC_P[l['precisao']]}{MAC_R[r]}"
                    macros[f"etoe{k}"] = br(l["t_e2e_ms_media"], 1)
                    macros[f"fps{k}"] = br(l["fps_sustentavel"], 1)
                    macros[f"cpu{k}"] = br(l.get("cpu_pct_media"), 0)
                    macros[f"rss{k}"] = br(l.get("rss_mb_max_sem_quadros"), 0)
            macros[f"razao{MAC_M[m]}{MAC_R[r]}"] = razao
    tabela("latencia_borda", "Latência fim a fim por quadro na borda (ms; média e IC 95\\%), ARM64 nativo (VM Oracle A1, Neoverse-N1, 2 núcleos).",
           ["Modelo", "Resolução", "FP32", "INT8", "FP32/INT8"], linhas, "llccr",
           "Servidor ARM com 2 núcleos: os tempos servem para comparação relativa, não representam um Raspberry Pi. "
           "300 quadros válidos por combinação.")

    # Nuvem
    linhas = []
    for l in [l for l in s15 if l["parte"] == "nuvem"]:
        bandas = {f: next((s["banda_subida_kbps"] for s in summary if s["parte"] == "nuvem" and s["modelo"] == l["modelo"]
                           and s["resolucao_fonte"] == l["resolucao_fonte"] and s["fps_fonte"] == f), "") for f in MAC_F}
        linhas.append([NOMES[l["modelo"]], l["resolucao_fonte"], br(l["t_e2e_ms_media"], 0), br(l["t_transmissao_ms_media"], 0),
                       br(l["t_infer_ms_media"], 0), br(float(l["bytes_jpeg_media"]) / 1000, 1),
                       *[br(float(bandas[f]) / 1000, 1) if bandas[f] else "--" for f in MAC_F]])
        for f in MAC_F:
            if bandas[f]:
                macros[f"banda{MAC_R[l['resolucao_fonte']]}{MAC_F[f]}"] = br(float(bandas[f]) / 1000, 1)
        macros[f"etoe{MAC_M[l['modelo']]}Fp{MAC_R[l['resolucao_fonte']]}Nuvem"] = br(l["t_e2e_ms_media"], 0)
    tabela("nuvem", "Baseline de nuvem: latência média por quadro (ms), tamanho do quadro JPEG (kB) e banda de subida (Mbit/s) por taxa da fonte.",
           ["Modelo", "Res.", "e2e", "Transm.", "Infer.", "kB/quadro", "5 FPS", "15 FPS", "30 FPS"], linhas,
           "llrrrrrrr", "Rede emulada com tc netem (RTT 40 ms, subida 10 Mbit/s, valores assumidos); servidor x86-64 nativo. "
           "Na borda nenhum quadro de vídeo é enviado.")

    # Testes FP32 x INT8
    linhas = []
    for t in sorted(testes, key=lambda t: (list(NOMES).index(t["modelo"]), int(t["resolucao_fonte"]), t["metrica"])):
        if t["metrica"] != "t_e2e_ms":
            continue
        linhas.append([NOMES[t["modelo"]], t["resolucao_fonte"], t["n_pares"], br(t["shapiro_p"], 3), t["teste"],
                       "< 0,001" if float(t["p_valor"]) < 0.001 else br(t["p_valor"], 3)])
    tabela("testes_fp32_int8", "Testes pareados da latência fim a fim FP32 $\\times$ INT8 na borda (Shapiro-Wilk nas diferenças; $\\alpha = 0{,}05$).",
           ["Modelo", "Res.", "Pares", "Shapiro $p$", "Teste", "$p$"], linhas, "llrrlr")

    # Edge TPU
    linhas = [[NOMES[e["modelo"]], e["resolucao"], "sim" if e["compilou"] == "True" else "não",
               e["operacoes_na_tpu"] or "--", e["operacoes_total"] or "--", e["memoria_no_chip_usada"] or "--"] for e in etpu]
    tabela("edgetpu", "Compilação dos modelos INT8 para o Edge TPU (edgetpu\\_compiler 14.1).",
           ["Modelo", "Res.", "Compilou", "Op. na TPU", "Op. total", "Memória no chip"], linhas, "llcrrl")

    n_b = len({(l["modelo"], l["precisao"], l["resolucao_fonte"]) for l in summary if l["parte"] == "borda"})
    n_n = len({(l["modelo"], l["resolucao_fonte"]) for l in summary if l["parte"] == "nuvem"})
    macros.update({"nCombBorda": str(n_b), "nCombNuvem": str(n_n), "nCenarios": str(len(summary)),
                   "nQuadrosValidos": s15[0]["quadros_validos"] if s15 else "--"})
    corpo = ["% Gerado por src/analysis/artigo_tex.py a partir de results/. Não edite à mão."]
    corpo += [rf"\newcommand{{\{k}}}{{{v}}}" for k, v in sorted(macros.items())]
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "numeros.tex").write_text("\n".join(corpo) + "\n", encoding="utf-8")
    print(f"{len(macros)} macros -> docs/artigo/numeros.tex; tabelas em docs/artigo/tabelas/")


if __name__ == "__main__":
    main()
