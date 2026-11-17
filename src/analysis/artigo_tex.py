"""E6, passo 3: gera as tabelas, as figuras e as macros de números do artigo, a partir dos CSVs.

O que faz: lê results/summary.csv, results/e5/qualidade.csv, results/stats/fp32_x_int8_borda.csv e
results/edgetpu_compile.csv e escreve:
  - tabelas LaTeX com booktabs e siunitx (números alinhados pela vírgula, unidades no cabeçalho);
  - figuras em pgfplots (código .tex com os dados embutidos), compiladas junto com o artigo: saem
    vetoriais, na fonte e no tamanho do texto, no estilo das figuras da equipe. Cor fixa por modelo
    (paleta Okabe-Ito: YOLOv8n azul, SSD-MobileNet V1 laranja, EfficientDet-Lite0 verde) e FP32
    hachurado x INT8 sólido, o que funciona também impresso em preto e branco;
  - um arquivo de macros com os números citados no texto (nenhum número é digitado à mão).
Nomes das macros: \\<métrica><Modelo><Precisão><Resolução>, por exemplo \\mapYoloFpSeis
(mAP@50, YOLOv8n, FP32, fonte 640). Modelos: Yolo, Ssd, Effdet; precisão: Fp, Int; resolução:
Tres (320), Quatro (480), Seis (640); FPS: Cinco, Quinze, Trinta. Valor ausente vira "--".
As figuras e tabelas usam os estilos e cores definidos no configuracao.tex do artigo
(pacotes booktabs, siunitx, pgfplots com groupplots; cores cYolo, cSsd, cEff).

O que gera: docs/artigo/tabelas/*.tex, docs/artigo/figuras/*.tex e docs/artigo/numeros.tex
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
MODELOS = ["yolov8n", "ssd_mobilenet_v1", "efficientdet_lite0"]
RESOLUCOES = ["320", "480", "640"]
NOMES = {"yolov8n": "YOLOv8n", "ssd_mobilenet_v1": "SSD-MobileNet V1", "efficientdet_lite0": "EfficientDet-Lite0"}
TITULO = {"yolov8n": "YOLOv8n", "ssd_mobilenet_v1": r"SSD-\\MobileNet V1", "efficientdet_lite0": r"EfficientDet-\\Lite0"}
COR = {"yolov8n": "cYolo", "ssd_mobilenet_v1": "cSsd", "efficientdet_lite0": "cEff"}
MAC_M = {"yolov8n": "Yolo", "ssd_mobilenet_v1": "Ssd", "efficientdet_lite0": "Effdet"}
MAC_P = {"fp32": "Fp", "int8": "Int"}
MAC_R = {"320": "Tres", "480": "Quatro", "640": "Seis"}
MAC_F = {"5": "Cinco", "15": "Quinze", "30": "Trinta"}
CABECALHO = "% Gerado por src/analysis/artigo_tex.py a partir de results/. Não edite à mão.\n"


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


def pt(v, casas: int = 2) -> str:
    """Número com ponto decimal (coordenadas do pgfplots)."""
    return f"{float(v):.{casas}f}"


def gravar(pasta: str, nome: str, texto: str) -> None:
    (SAIDA / pasta).mkdir(parents=True, exist_ok=True)
    (SAIDA / pasta / f"{nome}.tex").write_text(CABECALHO + texto, encoding="utf-8")


def tabela(nome: str, legenda: str, colunas: str, cabecalho: list[str], linhas: list[str], nota: str = "",
           larga: bool = False) -> None:
    """Tabela com booktabs. `cabecalho` e `linhas` já vêm como linhas LaTeX (sem \\\\ no fim)."""
    amb = "table*" if larga else "table"
    corpo = [rf"\begin{{{amb}}}[t]", r"\centering", r"\footnotesize", rf"\caption{{{legenda}}}",
             rf"\label{{tab:{nome}}}", r"\setlength{\tabcolsep}{" + ("4pt" if larga else "3pt") + "}", rf"\begin{{tabular}}{{{colunas}}}", r"\toprule"]
    corpo += [c if "cmidrule" in c else c + r" \\" for c in cabecalho] + [r"\midrule"] + [l if l.startswith("\\") else l + r" \\" for l in linhas]
    corpo += [r"\bottomrule", r"\end{tabular}"]
    if nota:
        corpo += [r"\par\smallskip", rf"\parbox{{0.96\linewidth}}{{\scriptsize {nota}}}"]
    corpo += [rf"\end{{{amb}}}", ""]
    gravar("tabelas", nome, "\n".join(corpo))


def achar(lista, **filtro):
    return next((l for l in lista if all(l.get(k) == v for k, v in filtro.items())), None)


def figura_barras(nome: str, rotulo_y: str, ymax: float, valor, erro=None, referencias=(), casas_y: int = 0) -> None:
    """Três painéis (um por modelo), barras FP32 (hachurada) e INT8 (sólida) por resolução."""
    p = [r"\begin{tikzpicture}",
         r"\begin{groupplot}[dados, group style={group size=3 by 1, horizontal sep=4pt, y descriptions at=edge left},",
         rf"  width=0.385\columnwidth, height=4.4cm, ybar=0.6pt, /pgf/bar width=5.5pt, clip=false, ymin=0, ymax={ymax},",
         r"  symbolic x coords={320,480,640}, xtick=data, enlarge x limits=0.25,",
         rf"  ylabel={{{rotulo_y}}}, xlabel={{resolução (px)}},",
         rf"  y tick label style={{/pgf/number format/.cd, fixed, precision={casas_y}, use comma, 1000 sep={{}}}}]"]
    for i, m in enumerate(MODELOS):
        p.append(rf"\nextgroupplot[title={{{TITULO[m]}}}, title style={{align=center}}{', legend to name=leg' + nome if i == 0 else ''}]")
        for prec in ("fp32", "int8"):
            estilo = (rf"draw={COR[m]}, fill=white, postaction={{pattern=north east lines, pattern color={COR[m]}}}"
                      if prec == "fp32" else rf"draw={COR[m]}!70!black, fill={COR[m]}")
            barra_erro = ", error bars/.cd, y dir=plus, y explicit, error bar style={black, line width=0.4pt}" if erro else ""
            coords = []
            for r in RESOLUCOES:
                v = valor(m, prec, r)
                if v is None:
                    continue
                e = erro(m, prec, r) if erro else None
                coords.append(f"({r},{pt(v, 4)})" + (f" +- (0,{pt(e, 4)})" if e is not None else ""))
            p.append(rf"\addplot[{estilo}{barra_erro}] coordinates {{{' '.join(coords)}}};")
            if i == 0:
                p.append(r"\addlegendentry{" + prec.upper() + "}")
        for y, txt in referencias:
            p.append(rf"\draw[densely dashed, gray!70!black, shorten <=-9pt, shorten >=-9pt] (axis cs:320,{pt(y)}) -- (axis cs:640,{pt(y)});")
            if i == 2:
                p.append(rf"\node[font=\scriptsize, anchor=west, inner sep=1pt, xshift=9pt] at (axis cs:640,{pt(y)}) {{{txt}}};")
    p += [r"\end{groupplot}",
          rf"\node[anchor=south] at ($(group c2r1.north)+(0,24pt)$) {{\pgfplotslegendfromname{{leg{nome}}}}};",
          r"\end{tikzpicture}", ""]
    gravar("figuras", nome, "\n".join(p))


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    summary = ler(RESULTS / "summary.csv")
    qual = ler(RESULTS / "e5" / "qualidade.csv")
    testes = [t for t in ler(RESULTS / "stats" / "fp32_x_int8_borda.csv") if t.get("metrica")]
    etpu = ler(RESULTS / "edgetpu_compile.csv")
    b15 = [l for l in summary if l["fps_fonte"] == "15"]
    macros: dict[str, str] = {}

    def borda(m, prec, r):
        return achar(b15, parte="borda", modelo=m, precisao=prec, resolucao_fonte=r)

    def nuvem(m, r):
        return achar(b15, parte="nuvem", modelo=m, resolucao_fonte=r)

    def q(parte, m, prec, r):
        return achar(qual, parte=parte, modelo=m, precisao=prec, resolucao_fonte=r)

    # ---------------- macros ----------------
    for x in qual:
        macros[f"map{MAC_M[x['modelo']]}{MAC_P[x['precisao']]}{MAC_R[x['resolucao_fonte']]}"
               + ("Nuvem" if x["parte"] == "nuvem" else "")] = br(x["map50_pessoa"], 3)
    for m in MODELOS:
        for r in RESOLUCOES:
            fp, it = borda(m, "fp32", r), borda(m, "int8", r)
            for l in (fp, it):
                if l:
                    k = f"{MAC_M[m]}{MAC_P[l['precisao']]}{MAC_R[r]}"
                    macros[f"etoe{k}"] = br(l["t_e2e_ms_media"], 1)
                    macros[f"fps{k}"] = br(l["fps_sustentavel"], 1)
                    macros[f"cpu{k}"] = br(l.get("cpu_pct_media"), 0)
                    macros[f"rss{k}"] = br(l.get("rss_mb_max_sem_quadros"), 0)
            if fp and it:
                macros[f"razao{MAC_M[m]}{MAC_R[r]}"] = br(float(fp["t_e2e_ms_media"]) / float(it["t_e2e_ms_media"]), 1)
            nv = nuvem(m, r)
            if nv:
                macros[f"etoe{MAC_M[m]}Fp{MAC_R[r]}Nuvem"] = br(nv["t_e2e_ms_media"], 0)
    for l in summary:
        if l["parte"] == "borda":
            k = f"{MAC_M[l['modelo']]}{MAC_P[l['precisao']]}{MAC_R[l['resolucao_fonte']]}{MAC_F[l['fps_fonte']]}"
            macros[f"desc{k}"] = br(float(l["taxa_descarte_se_ocupado"]) * 100, 0)
        else:
            macros[f"banda{MAC_R[l['resolucao_fonte']]}{MAC_F[l['fps_fonte']]}"] = br(float(l["banda_subida_kbps"]) / 1000, 1)

    # ---------------- tabelas ----------------
    linhas = []
    for m in MODELOS:
        linhas.append(rf"\multicolumn{{6}}{{@{{}}l}}{{\textit{{{NOMES[m]}}}}} \\")
        for r in RESOLUCOES:
            v = [q("borda", m, "fp32", r), q("borda", m, "int8", r), q("nuvem", m, "fp32", r)]
            linhas.append(" & ".join([r] + [br(x["map50_pessoa"], 3) if x else "{--}" for x in v]
                                     + [br(x["f1_050"], 3) if x else "{--}" for x in v[:2]]))
    tabela("qualidade", "Qualidade da detecção de pessoas nas 350 imagens do COCO val2017 (mAP@50 e F1 com limiar de pontuação 0,5).",
           "@{}l*{5}{r}@{}",
           [r"& \multicolumn{3}{c}{mAP@50} & \multicolumn{2}{c}{F1} \\ \cmidrule(lr){2-4} \cmidrule(l){5-6}",
            r"{Res. (px)} & {FP32} & {INT8} & {Nuvem} & {FP32} & {INT8}"], linhas,
           "FP32 e INT8 medidos na borda; ``Nuvem'' é o FP32 no servidor, que recebe o quadro em JPEG (qualidade 80).")

    linhas = []
    for m in MODELOS:
        for r in RESOLUCOES:
            fp, it = borda(m, "fp32", r), borda(m, "int8", r)
            if not (fp or it):
                continue
            t = achar(testes, modelo=m, resolucao_fonte=r, metrica="t_e2e_ms")
            pval = ("{$<0{,}001$}" if float(t["p_valor"]) < 0.001 else br(t["p_valor"], 3)) if t else "{--}"
            cel = lambda l, c: br(l[c], 1) if l else "{--}"  # noqa: E731
            razao = br(float(fp["t_e2e_ms_media"]) / float(it["t_e2e_ms_media"]), 1) if (fp and it) else "{--}"
            linhas.append(" & ".join([NOMES[m] if r == "320" else "", r, cel(fp, "t_e2e_ms_media"), cel(fp, "t_e2e_ms_p95"),
                                      cel(it, "t_e2e_ms_media"), cel(it, "t_e2e_ms_p95"), razao, pval]))
    tabela("latencia_borda", "Latência fim a fim por quadro na borda (ARM64 nativo, Neoverse-N1, 2 núcleos).",
           "@{}ll*{4}{r}rr@{}",
           [r"& & \multicolumn{2}{c}{FP32 (ms)} & \multicolumn{2}{c}{INT8 (ms)} & & \\ \cmidrule(lr){3-4} \cmidrule(lr){5-6}",
            r"Modelo & {Res. (px)} & {média} & {p95} & {média} & {p95} & {FP32/INT8} & {$p$}"], linhas,
           "300 quadros válidos por combinação. $p$: teste de Wilcoxon pareado FP32 $\\times$ INT8 (o Shapiro-Wilk rejeitou a "
           "normalidade das diferenças em todos os pares; $\\alpha = 0{,}05$). Servidor ARM de 2 núcleos: os tempos servem "
           "para comparação relativa e não representam um Raspberry Pi.", larga=True)

    linhas = []
    for m in MODELOS:
        for r in RESOLUCOES:
            l = nuvem(m, r)
            if not l:
                continue
            bandas = [achar(summary, parte="nuvem", modelo=m, resolucao_fonte=r, fps_fonte=f) for f in MAC_F]
            linhas.append(" & ".join([NOMES[m] if r == "320" else "", r, br(l["t_e2e_ms_media"], 0), br(l["t_transmissao_ms_media"], 0),
                                      br(l["t_infer_ms_media"], 0), br(float(l["bytes_jpeg_media"]) / 1000, 1)]
                                     + [br(float(b["banda_subida_kbps"]) / 1000, 1) if b else "{--}" for b in bandas]))
    tabela("nuvem", "Baseline de nuvem: latência média por quadro, tamanho do quadro JPEG e banda de subida demandada por taxa da câmera.",
           "@{}llrrrr*{3}{r}@{}",
           [r"& & \multicolumn{3}{c}{Latência média (ms)} & & \multicolumn{3}{c}{Banda de subida (Mbit/s)} \\ "
            r"\cmidrule(lr){3-5} \cmidrule(l){7-9}",
            r"Modelo & {Res. (px)} & {fim a fim} & {transm.} & {infer.} & {kB/quadro} & {5 FPS} & {15 FPS} & {30 FPS}"], linhas,
           "Servidor x86-64 nativo, modelos FP32; enlace emulado com tc netem (RTT 40 ms, subida 10 Mbit/s). "
           "A banda demandada independe do enlace. Na borda nenhum quadro de vídeo é enviado.", larga=True)

    linhas = []
    for t in sorted(testes, key=lambda t: (MODELOS.index(t["modelo"]), int(t["resolucao_fonte"]))):
        if t["metrica"] == "t_e2e_ms":
            linhas.append(" & ".join([NOMES[t["modelo"]], t["resolucao_fonte"], t["n_pares"], br(t["shapiro_p"], 3), t["teste"],
                                      "{$<0{,}001$}" if float(t["p_valor"]) < 0.001 else br(t["p_valor"], 3)]))
    tabela("testes_fp32_int8", "Testes pareados da latência fim a fim FP32 $\\times$ INT8 na borda ($\\alpha = 0{,}05$).",
           "@{}llrrlr@{}",
           [r"Modelo & {Res. (px)} & Pares & {Shapiro $p$} & Teste & {$p$}"], linhas, larga=True)

    linhas = []
    for e in sorted(etpu, key=lambda e: (MODELOS.index(e["modelo"]), int(e["resolucao"]))):
        mem = br(int(e["memoria_no_chip_usada_bytes"]) / 2**20, 2) if e.get("memoria_no_chip_usada_bytes") else "{--}"
        ops = f"{e['operacoes_na_tpu']}/{e['operacoes_total']}" if e.get("operacoes_total") else "--"
        linhas.append(" & ".join([NOMES[e["modelo"]], e["resolucao"], "sim" if e["compilou"] == "True" else "não", ops, mem]))
    tabela("edgetpu", "Compilação dos modelos INT8 para o Edge TPU (edgetpu\\_compiler 14.1).",
           "@{}llccr@{}",
           [r"Modelo & {Res. (px)} & Compilou & {Op. na TPU} & {Mem. no chip (MiB)}"], linhas)

    # ---------------- figuras ----------------
    figura_barras("latencia", "latência fim a fim (ms)", 160,
                  lambda m, p, r: float(borda(m, p, r)["t_e2e_ms_mediana"]) if borda(m, p, r) else None,
                  erro=lambda m, p, r: float(borda(m, p, r)["t_e2e_ms_p95"]) - float(borda(m, p, r)["t_e2e_ms_mediana"]),
                  referencias=((1000 / 30, "30 FPS"), (1000 / 15, "15 FPS")))
    figura_barras("map", "mAP@50 (pessoa)", 0.85,
                  lambda m, p, r: float(q("borda", m, p, r)["map50_pessoa"]) if q("borda", m, p, r) else None, casas_y=1)

    p = [r"\begin{tikzpicture}",
         r"\begin{axis}[dados, width=\columnwidth, height=5.4cm, xmin=0, xmax=150, ymin=0.40, ymax=0.82,",
         r"  xlabel={latência fim a fim mediana na borda (ms)}, ylabel={mAP@50 (pessoa)},",
         r"  y tick label style={/pgf/number format/.cd, fixed, precision=2, use comma},",
         r"  legend style={at={(0.98,0.03)}, anchor=south east, legend columns=2, font=\scriptsize, fill=white, fill opacity=0.9,",
         r"    text opacity=1, /tikz/every even column/.append style={column sep=4pt}}]"]
    for m in MODELOS:
        for prec in ("int8", "fp32"):
            pts = [(float(borda(m, prec, r)["t_e2e_ms_mediana"]), float(q("borda", m, prec, r)["map50_pessoa"]), r)
                   for r in RESOLUCOES if borda(m, prec, r) and q("borda", m, prec, r)]
            marca = {"yolov8n": "*", "ssd_mobilenet_v1": "square*", "efficientdet_lite0": "triangle*"}[m]
            estilo = (rf"{COR[m]}, thick, mark={marca}, mark options={{fill={COR[m]}}}" if prec == "int8"
                      else rf"{COR[m]}, thick, densely dashed, mark={marca}, mark options={{solid, fill=white}}")
            p.append(rf"\addplot[{estilo}] coordinates {{{' '.join(f'({pt(x)},{pt(y, 4)})' for x, y, _ in pts)}}};")
            p.append(rf"\addlegendentry{{{NOMES[m].split()[0].split('-')[0]} {prec.upper()}}}")
            if m == "yolov8n":
                for x, y, r in pts:
                    p.append(rf"\node[font=\scriptsize, anchor={'north west' if prec == 'int8' else 'south east'}, inner sep=1.5pt]"
                             rf" at (axis cs:{pt(x)},{pt(y, 4)}) {{{r}}};")
    p += [r"\end{axis}", r"\end{tikzpicture}", ""]
    gravar("figuras", "compromisso", "\n".join(p))

    p = [r"\begin{tikzpicture}",
         r"\begin{axis}[dados, width=\columnwidth, height=5cm, xmin=3, xmax=44, ymin=0, ymax=20,",
         r"  xtick={5,15,30}, xlabel={taxa da câmera (FPS)}, ylabel={banda de subida (Mbit/s)}, clip=false,",
         r"  y tick label style={/pgf/number format/.cd, fixed, use comma}]"]
    estilos = {"320": "densely dotted, mark=triangle*", "480": "densely dashed, mark=square*", "640": "solid, mark=*"}
    for r in RESOLUCOES:
        pts = [(int(f), float(achar(summary, parte="nuvem", resolucao_fonte=r, fps_fonte=f)["banda_subida_kbps"]) / 1000)
               for f in MAC_F if achar(summary, parte="nuvem", resolucao_fonte=r, fps_fonte=f)]
        if pts:
            p.append(rf"\addplot[black, thick, {estilos[r]}] coordinates {{{' '.join(f'({x},{pt(y)})' for x, y in pts)}}};")
            p.append(rf"\node[font=\scriptsize, anchor=south west, inner sep=1.5pt] at (axis cs:{pts[-1][0]},{pt(pts[-1][1])}) {{nuvem, {r} px}};")
    p += [r"\draw[densely dashed, gray!70!black] (axis cs:3,10) -- (axis cs:44,10);",
          r"\node[font=\scriptsize, anchor=south west, inner sep=1pt] at (axis cs:3.3,10) {enlace emulado: 10 Mbit/s};",
          r"\draw[cYolo, line width=1.4pt] (axis cs:3,0) -- (axis cs:44,0);",
          r"\node[font=\scriptsize, anchor=south east, inner sep=1.5pt, text=cYolo!70!black] at (axis cs:44,0) {borda: nenhum vídeo enviado};",
          r"\end{axis}", r"\end{tikzpicture}", ""]
    gravar("figuras", "banda", "\n".join(p))

    # ---------------- macros ----------------
    n_b = len({(l["modelo"], l["precisao"], l["resolucao_fonte"]) for l in summary if l["parte"] == "borda"})
    n_n = len({(l["modelo"], l["resolucao_fonte"]) for l in summary if l["parte"] == "nuvem"})
    macros.update({"nCombBorda": str(n_b), "nCombNuvem": str(n_n), "nCenarios": str(len(summary)),
                   "nQuadrosValidos": b15[0]["quadros_validos"] if b15 else "--"})
    corpo = [CABECALHO.strip()] + [rf"\newcommand{{\{k}}}{{{v}}}" for k, v in sorted(macros.items())]
    (SAIDA / "numeros.tex").write_text("\n".join(corpo) + "\n", encoding="utf-8")
    print(f"{len(macros)} macros -> docs/artigo/numeros.tex; tabelas em docs/artigo/tabelas/; figuras em docs/artigo/figuras/")


if __name__ == "__main__":
    main()
