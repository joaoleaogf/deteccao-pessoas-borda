"""E6, passo 2: testes de hipótese, figuras e results/RESUMO.md, a partir dos dados da E5.

O que faz (determinístico: rodar duas vezes dá os mesmos arquivos):
  - Comparações pareadas por frame_idx (quadros válidos), na métrica t_e2e_ms e em t_infer_ms:
      FP32 x INT8 na borda (mesmo modelo e resolução da fonte)
      borda x nuvem (mesmo modelo FP32 e resolução da fonte; ATENÇÃO: servidor ARM de 2 núcleos x servidor
      x86; não representa um Raspberry Pi, a diferença absoluta é só registrada)
    Shapiro-Wilk nas diferenças; t pareado se p >= 0,05, senão Wilcoxon pareado; alfa = 0,05.
  - Figuras em PDF e PNG: latência por combinação (borda, ARM64 nativo), ganho do INT8, banda de subida,
    mAP@50 por combinação e fila média por taxa da fonte (derivada).
  - results/RESUMO.md com as tabelas, os testes e as limitações, tudo gerado dos CSVs.

O que gera: results/stats/*.csv, figures/*.pdf e *.png, results/RESUMO.md
Roda no contêiner borda-prep (/opt/venv-export). Uso: python src/analysis/estatistica.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import RAIZ, RESULTS  # noqa: E402

FIG = RAIZ / "figures"
STATS = RESULTS / "stats"
ALFA = 0.05
NOMES = {"yolov8n": "YOLOv8n", "ssd_mobilenet_v1": "SSD-MobileNet V1", "efficientdet_lite0": "EfficientDet-Lite0"}
AVISO = ("Tempos de borda medidos em ARM64 nativo (VM Oracle A1, Neoverse-N1, 2 núcleos); "
         "não representam um Raspberry Pi.")


def ler(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def gravar(caminho: Path, linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    campos = []
    for l in linhas:
        campos += [k for k in l if k not in campos]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, restval="")
        w.writeheader()
        w.writerows(linhas)


def quadros(parte: str, combo: str) -> dict[int, dict] | None:
    p = RESULTS / "e5" / parte / combo
    if not (p / "COMPLETO").exists():
        return None
    return {int(l["frame_idx"]): l for l in ler(p / "quadros.csv") if l["aquecimento"] == "False"}


def testar(a: np.ndarray, b: np.ndarray) -> dict:
    """Teste pareado de a - b."""
    from scipy import stats

    d = a - b
    sw = stats.shapiro(d)
    if sw.pvalue >= ALFA:
        t = stats.ttest_rel(a, b)
        teste, est, p = "t pareado", float(t.statistic), float(t.pvalue)
    else:
        w = stats.wilcoxon(a, b)
        teste, est, p = "Wilcoxon pareado", float(w.statistic), float(w.pvalue)
    return {"n_pares": len(d), "media_a": round(float(a.mean()), 3), "media_b": round(float(b.mean()), 3),
            "mediana_a": round(float(np.median(a)), 3), "mediana_b": round(float(np.median(b)), 3),
            "diferenca_media": round(float(d.mean()), 3), "diferenca_mediana": round(float(np.median(d)), 3),
            "razao_medias_a_sobre_b": round(float(a.mean() / b.mean()), 4),
            "shapiro_W": round(float(sw.statistic), 4), "shapiro_p": float(f"{sw.pvalue:.4g}"),
            "teste": teste, "estatistica": round(est, 4), "p_valor": float(f"{p:.4g}"),
            "significativo_005": p < ALFA}


def comparacoes(summary: list[dict]) -> tuple[list[dict], list[dict]]:
    combos = sorted({(l["modelo"], l["resolucao_fonte"]) for l in summary})
    fp_int, borda_nuvem = [], []
    for modelo, res in combos:
        for metrica in ("t_e2e_ms", "t_infer_ms"):
            a, b = quadros("borda", f"{modelo}_fp32_{res}"), quadros("borda", f"{modelo}_int8_{res}")
            if a and b:
                k = sorted(set(a) & set(b))
                r = testar(np.array([float(a[i][metrica]) for i in k]), np.array([float(b[i][metrica]) for i in k]))
                fp_int.append({"modelo": modelo, "resolucao_fonte": res, "metrica": metrica,
                               "a": "borda FP32", "b": "borda INT8", **r})
            a, b = quadros("borda", f"{modelo}_fp32_{res}"), quadros("nuvem", f"{modelo}_fp32_{res}")
            if a and b:
                k = sorted(set(a) & set(b))
                r = testar(np.array([float(a[i][metrica]) for i in k]), np.array([float(b[i][metrica]) for i in k]))
                borda_nuvem.append({"modelo": modelo, "resolucao_fonte": res, "metrica": metrica,
                                    "a": "borda FP32 (ARM64 nativo, 2 núcleos)", "b": "nuvem FP32 (x86 nativo)", **r,
                                    "observacao": "servidor ARM x servidor x86; não representa um Raspberry Pi"})
    return fp_int, borda_nuvem


def salvar(fig, nome: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / f"{nome}.pdf", metadata={"CreationDate": None, "ModDate": None}, bbox_inches="tight")
    fig.savefig(FIG / f"{nome}.png", dpi=200, metadata={"Software": None}, bbox_inches="tight")


def figuras(summary: list[dict], qual: list[dict]) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "svg.hashsalt": "e6", "figure.dpi": 100})
    feitas = []
    cores = {"fp32": "#1f5f8b", "int8": "#e07b39"}
    base = [l for l in summary if l["fps_fonte"] == "15"]  # e2e não depende da taxa (derivado)

    borda = [l for l in base if l["parte"] == "borda"]
    if borda:
        rot = sorted({(l["modelo"], int(l["resolucao_fonte"])) for l in borda},
                     key=lambda t: (list(NOMES).index(t[0]), t[1]))
        fig, ax = plt.subplots(figsize=(7.5, 3.4))
        x = np.arange(len(rot))
        for j, prec in enumerate(("fp32", "int8")):
            med, lo, hi = [], [], []
            for m, r in rot:
                l = next((l for l in borda if l["modelo"] == m and int(l["resolucao_fonte"]) == r
                          and l["precisao"] == prec), None)
                v = float(l["t_e2e_ms_media"]) if l else np.nan
                med.append(v)
                lo.append(v - float(l["t_e2e_ms_ic95_inf"]) if l else 0)
                hi.append(float(l["t_e2e_ms_ic95_sup"]) - v if l else 0)
            ax.bar(x + (j - 0.5) * 0.38, med, 0.38, yerr=[lo, hi], capsize=2, color=cores[prec], label=prec.upper())
        ax.set_xticks(x, [f"{NOMES[m]}\n{r}" for m, r in rot], fontsize=7)
        ax.set_ylabel("t_e2e médio por quadro (ms)")
        ax.set_title("Borda: latência fim a fim por combinação (média, IC 95%)\n" + AVISO, fontsize=8)
        ax.legend()
        salvar(fig, "e6_borda_latencia")
        plt.close(fig)
        feitas.append("e6_borda_latencia")

    nuvem = [l for l in summary if l["parte"] == "nuvem"]
    if nuvem:
        from comum import ler_yaml

        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        # Os quadros JPEG são os mesmos para os três modelos: a banda depende só da resolução.
        for r, est in ((320, ":"), (480, "--"), (640, "-")):
            ls = [l for l in nuvem if int(l["resolucao_fonte"]) == r]
            if ls:
                fps = sorted({int(l["fps_fonte"]) for l in ls})
                v = [np.mean([float(l["banda_subida_kbps"]) for l in ls if int(l["fps_fonte"]) == f]) / 1000 for f in fps]
                ax.plot(fps, v, est, marker="o", label=f"nuvem, quadro {r}x{r}")
        lim = ler_yaml("network.yaml")["banda_subida_kbps"] / 1000
        ax.axhline(lim, color="gray", ls="-.", lw=1, label=f"enlace emulado ({lim:g} Mbit/s, valor assumido)")
        ax.axhline(0, color="k", lw=1.5, label="borda (nenhum vídeo enviado)")
        ax.set_xlabel("taxa da fonte (FPS)")
        ax.set_ylabel("banda de subida (Mbit/s)")
        ax.set_xticks([5, 15, 30])
        ax.set_title("Banda de subida necessária: nuvem (JPEG q80) x borda", fontsize=8)
        ax.legend(fontsize=6, ncol=2)
        salvar(fig, "e6_banda_subida")
        plt.close(fig)
        feitas.append("e6_banda_subida")

    if qual:
        fig, ax = plt.subplots(figsize=(7.5, 3.2))
        grupos = [("borda", "fp32"), ("borda", "int8"), ("nuvem", "fp32")]
        rot = sorted({(q["modelo"], int(q["resolucao_fonte"])) for q in qual},
                     key=lambda t: (list(NOMES).index(t[0]), t[1]))
        x = np.arange(len(rot))
        for j, (parte, prec) in enumerate(grupos):
            v = []
            for m, r in rot:
                q = next((q for q in qual if q["parte"] == parte and q["precisao"] == prec and q["modelo"] == m
                          and int(q["resolucao_fonte"]) == r), None)
                v.append(float(q["map50_pessoa"]) if q else np.nan)
            ax.bar(x + (j - 1) * 0.27, v, 0.27, label=f"{parte} {prec.upper()}")
        ax.set_xticks(x, [f"{NOMES[m]}\n{r}" for m, r in rot], fontsize=7)
        ax.set_ylabel("mAP@50 (pessoa)")
        ax.set_ylim(0, 1)
        ax.set_title("Qualidade da detecção de pessoas (350 imagens COCO val2017)", fontsize=8)
        ax.legend(fontsize=7)
        salvar(fig, "e6_map50")
        plt.close(fig)
        feitas.append("e6_map50")

    if borda:
        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        for l in sorted({(l["modelo"], l["precisao"], l["resolucao_fonte"]) for l in summary if l["parte"] == "borda"}):
            ls = sorted([s for s in summary if s["parte"] == "borda" and (s["modelo"], s["precisao"],
                         s["resolucao_fonte"]) == l], key=lambda s: int(s["fps_fonte"]))
            ax.plot([int(s["fps_fonte"]) for s in ls], [float(s["taxa_descarte_se_ocupado"]) * 100 for s in ls],
                    marker="o", lw=1, label=f"{NOMES[l[0]]} {l[1].upper()} {l[2]}")
        ax.set_xlabel("taxa da fonte (FPS)")
        ax.set_ylabel("quadros descartados se ocupado (%)")
        ax.set_xticks([5, 15, 30])
        ax.set_title("Borda: quadros que seriam descartados (cenários DERIVADOS)\n" + AVISO, fontsize=8)
        ax.legend(fontsize=5, ncol=2)
        salvar(fig, "e6_borda_descarte")
        plt.close(fig)
        feitas.append("e6_borda_descarte")
    return feitas


def tabela_md(linhas: list[dict], campos: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(t for _, t in campos) + " |", "|" + "---|" * len(campos)]
    for l in linhas:
        out.append("| " + " | ".join(str(l.get(c, "")) for c, _ in campos) + " |")
    return "\n".join(out)


def resumo_md(summary, qual, fp_int, borda_nuvem, figs) -> str:
    n_borda = len({(l["modelo"], l["precisao"], l["resolucao_fonte"]) for l in summary if l["parte"] == "borda"})
    n_nuvem = len({(l["modelo"], l["resolucao_fonte"]) for l in summary if l["parte"] == "nuvem"})
    base15 = [l for l in summary if l["fps_fonte"] == "15"]
    p = ["# Resumo dos resultados (E5 e E6)", "",
         "Gerado por `src/analysis/estatistica.py` a partir de `results/summary.csv` e `results/e5/`. Não edite à mão.", "",
         f"Combinações medidas: borda {n_borda} de 18; nuvem {n_nuvem} de 9. "
         f"Cenários em `results/summary.csv`: {len(summary)}.", "",
         "## Como ler estes números", "",
         f"- {AVISO}",
         "- **Amostragem reduzida (decisão D8, altera o desenho da ATV 04):** cada combinação modelo × precisão × "
         "resolução foi medida uma vez, com 350 quadros (50 de aquecimento + 300 válidos). Os cenários de 5, 15 e 30 FPS "
         "são **derivados** dessas medições (quadro i disponível em i/fps), não medidos em execução própria.",
         "- A latência borda × nuvem compara um servidor ARM de 2 núcleos com um servidor x86 e **não representa um Raspberry Pi**. O resultado "
         "sólido da QP2 é a **banda de subida**: a nuvem precisa enviar o vídeo; a borda não envia nenhum quadro.",
         "- Nuvem: rede emulada com `tc netem` (RTT 40 ms, subida 10 Mbit/s): valores assumidos que a equipe precisa "
         "justificar com fonte. Executada no PC ao mesmo tempo que a coleta emulada da borda, depois substituída (D10).",
         "- Memória: `rss_mb_max` inclui os 350 quadros da fonte pré-carregados; `rss_mb_max_sem_quadros` desconta "
         "esse volume (350 × res × res × 3 bytes).",
         "- Energia: não calculada (sem potência de referência com fonte verificável em `configs/energia.yaml`).", "",
         "## Qualidade (mAP@50 da classe pessoa, 350 imagens)", "",
         tabela_md(qual, [("parte", "parte"), ("modelo", "modelo"), ("precisao", "precisão"),
                          ("resolucao_fonte", "resolução da fonte"), ("map50_pessoa", "mAP@50"),
                          ("precisao_050", "precisão@0,5"), ("revocacao_050", "revocação@0,5"), ("f1_050", "F1@0,5")]),
         "", "## Latência por combinação (quadros válidos; média, IC 95% e p95, em ms)", "",
         tabela_md(base15, [("parte", "parte"), ("modelo", "modelo"), ("precisao", "precisão"),
                            ("resolucao_fonte", "res."), ("t_e2e_ms_media", "e2e média"),
                            ("t_e2e_ms_ic95_inf", "IC inf"), ("t_e2e_ms_ic95_sup", "IC sup"),
                            ("t_e2e_ms_p95", "e2e p95"), ("t_infer_ms_media", "inferência média"),
                            ("fps_sustentavel", "FPS sustentável")]),
         "", "## Banda de subida e fila por taxa da fonte (cenários derivados)", "",
         tabela_md(summary, [("parte", "parte"), ("modelo", "modelo"), ("precisao", "precisão"),
                             ("resolucao_fonte", "res."), ("fps_fonte", "FPS"), ("banda_subida_kbps", "subida (kbit/s)"),
                             ("t_fila_ms_media", "fila média (ms)"),
                             ("taxa_descarte_se_ocupado", "descarte se ocupado")]),
         "", "## Testes pareados FP32 × INT8 na borda", ""]
    p.append(tabela_md(fp_int, [("modelo", "modelo"), ("resolucao_fonte", "res."), ("metrica", "métrica"),
                                ("n_pares", "n"), ("media_a", "média FP32"), ("media_b", "média INT8"),
                                ("razao_medias_a_sobre_b", "FP32/INT8"), ("shapiro_p", "Shapiro p"),
                                ("teste", "teste"), ("p_valor", "p"), ("significativo_005", "p < 0,05")])
             if fp_int else "_Sem pares completos ainda (faltam combinações FP32 da borda)._")
    p += ["", "## Testes pareados borda × nuvem (servidor ARM × servidor x86; não representa um Raspberry Pi)", ""]
    p.append(tabela_md(borda_nuvem, [("modelo", "modelo"), ("resolucao_fonte", "res."), ("metrica", "métrica"),
                                     ("n_pares", "n"), ("media_a", "média borda"), ("media_b", "média nuvem"),
                                     ("teste", "teste"), ("p_valor", "p")])
             if borda_nuvem else "_Sem pares completos ainda (faltam combinações FP32 da borda)._")
    p += ["", "## Figuras", ""] + [f"- `figures/{f}.pdf` e `.png`" for f in figs]
    p += ["", "## Limitações", "",
          "- Borda em ARM64 nativo num servidor Neoverse-N1 com 2 núcleos (D10): os tempos servem para comparação relativa "
          "(FP32 × INT8, entre modelos e resoluções), não como tempo de um Raspberry Pi (Cortex-A72/A76, 4 núcleos). "
          "Uma coleta parcial anterior sob emulação QEMU fica em `results/e5/anexo_emulado/` só como comparação (D9).",
          "- Cenários de FPS derivados e amostragem reduzida (D8).",
          "- Conjunto de teste do COCO val2017; não há gravações residenciais (D6).",
          "- INT8 do YOLOv8n é híbrido (D2); Edge TPU avaliado só pelo relatório do compilador (E4).",
          "- Rede da nuvem emulada com valores assumidos (D5); protocolo JPEG/HTTP no lugar de RTSP/WebRTC.", ""]
    return "\n".join(p)


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    summary = ler(RESULTS / "summary.csv")
    qual = ler(RESULTS / "e5" / "qualidade.csv")
    fp_int, borda_nuvem = comparacoes(summary)
    gravar(STATS / "fp32_x_int8_borda.csv", fp_int or [{"situacao": "sem pares completos"}])
    gravar(STATS / "borda_x_nuvem.csv", borda_nuvem or [{"situacao": "sem pares completos"}])
    desc = [{k: l[k] for k in l if k.startswith(("parte", "modelo", "precisao", "resolucao", "fps_fonte",
                                                   "natureza", "quadros_validos", "t_e2e", "t_infer"))} for l in summary]
    gravar(STATS / "descritiva.csv", desc)
    figs = figuras(summary, qual)
    (RESULTS / "RESUMO.md").write_text(resumo_md(summary, qual, fp_int, borda_nuvem, figs), encoding="utf-8")
    print(f"stats: {len(fp_int)} FP32xINT8, {len(borda_nuvem)} borda x nuvem; figuras: {', '.join(figs)}")
    print("-> results/stats/, figures/, results/RESUMO.md")


if __name__ == "__main__":
    main()
