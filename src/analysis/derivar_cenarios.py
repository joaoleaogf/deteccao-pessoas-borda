"""E6, passo 1: deriva os cenários de 5, 15 e 30 FPS e escreve results/summary.csv.

O que faz: lê as medições da E5 (results/e5/borda/* e results/e5/nuvem/*), usa só os quadros
válidos (sem os 50 de aquecimento) e, para cada taxa da fonte, simula a chegada dos quadros:
  - o quadro k fica disponível em k/fps; o processamento começa no maior valor entre a
    disponibilidade e o fim do quadro anterior; t_fila_ms é a espera; nenhum quadro é descartado
    (o pareamento é por frame_idx); t_fila_ms fica fora de t_e2e_ms;
  - à parte, conta os quadros que uma política "descartar se ocupado" teria perdido (ao ficar livre,
    o sistema pega o quadro mais recente e descarta os anteriores ainda não processados).
Os cenários são DERIVADOS (natureza=derivado), não medidos em execução própria (decisão D8).
Calcula também, por combinação, mAP@50 e F1 da classe pessoa a partir das detecções salvas na
própria coleta (todas as 350 imagens) e a banda de subida (nuvem: bytes JPEG x fps; borda: zero,
porque nenhum vídeo sai do dispositivo). Energia só se configs/energia.yaml tiver potência com fonte.

O que gera:
  results/e5/cenarios/<parte>_<combinação>_<fps>fps.csv   uma linha por quadro válido
  results/summary.csv                                     uma linha por cenário (54 + 27 quando completos)
  results/e5/qualidade.csv                                mAP@50, precisão, revocação e F1 por combinação

Roda no contêiner borda-prep (/opt/venv-export). Uso: python src/analysis/derivar_cenarios.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
from comum import DATA, RESULTS, ler_yaml  # noqa: E402

FPS = [5, 15, 30]


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def combinacoes(parte: str) -> list[Path]:
    base = RESULTS / "e5" / parte
    return sorted(p for p in base.glob("*") if (p / "COMPLETO").exists()) if base.exists() else []


def simular(servico_ms: np.ndarray, fps: int) -> tuple[np.ndarray, int]:
    """Devolve (t_fila_ms por quadro, quadros descartados na política 'descartar se ocupado')."""
    intervalo = 1000.0 / fps
    disp = np.arange(len(servico_ms)) * intervalo
    fila = np.zeros(len(servico_ms))
    fim = 0.0
    for k, s in enumerate(servico_ms):
        inicio = max(disp[k], fim)
        fila[k] = inicio - disp[k]
        fim = inicio + s
    # política com descarte: ao ficar livre, processa o quadro mais recente já disponível
    processados, livre, k = 0, 0.0, 0
    n = len(servico_ms)
    while k < n:
        livre = max(livre, disp[k])
        ultimo = min(n - 1, int(math.floor(livre / intervalo + 1e-9)))
        k = max(k, ultimo)
        livre += servico_ms[k]
        processados += 1
        k += 1
    return fila, n - processados


def ic95(x: np.ndarray) -> tuple[float, float]:
    from scipy import stats

    if len(x) < 2:
        return float("nan"), float("nan")
    m, ep = float(np.mean(x)), float(stats.sem(x))
    h = ep * float(stats.t.ppf(0.975, len(x) - 1))
    return m - h, m + h


def descrever(prefixo: str, x: np.ndarray) -> dict:
    lo, hi = ic95(x)
    return {f"{prefixo}_media": round(float(np.mean(x)), 3), f"{prefixo}_dp": round(float(np.std(x, ddof=1)), 3),
            f"{prefixo}_mediana": round(float(np.median(x)), 3), f"{prefixo}_p95": round(float(np.percentile(x, 95)), 3),
            f"{prefixo}_ic95_inf": round(lo, 3), f"{prefixo}_ic95_sup": round(hi, 3)}


def qualidade(pasta: Path, gab: dict) -> dict:
    from metricas import map50, precisao_revocacao_f1

    dets = {int(k): np.array(v, dtype=np.float32).reshape(-1, 5)
            for k, v in json.loads((pasta / "deteccoes.json").read_text(encoding="utf-8")).items()}
    p, r, f1 = precisao_revocacao_f1(dets, gab)
    return {"map50_pessoa": round(map50(dets, gab), 4), "precisao_050": round(p, 4),
            "revocacao_050": round(r, 4), "f1_050": round(f1, 4), "imagens_avaliadas": len(dets)}


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    from metricas import carregar_gabarito

    gab = carregar_gabarito(DATA / "teste_coco" / "gabarito_pessoa.json")
    energia = ler_yaml("energia.yaml")["placas"]["rpi4b"]
    potencia = energia["potencia_w"] if energia.get("fonte") else None
    pasta_cen = RESULTS / "e5" / "cenarios"
    pasta_cen.mkdir(parents=True, exist_ok=True)

    resumo, qual = [], []
    for parte in ("borda", "nuvem"):
        for pasta in combinacoes(parte):
            man = json.loads((pasta / "manifesto.json").read_text(encoding="utf-8"))
            linhas = [l for l in ler_csv(pasta / "quadros.csv") if l["aquecimento"] == "False"]
            q = qualidade(pasta, gab)
            qual.append({"parte": parte, "combinacao": pasta.name, "modelo": man["modelo"],
                         "precisao": man["precisao"], "resolucao_fonte": man["resolucao_fonte"], **q})
            e2e = np.array([float(l["t_e2e_ms"]) for l in linhas])
            infer = np.array([float(l["t_infer_ms"]) for l in linhas])
            for fps in FPS:
                fila, descartados = simular(e2e, fps)
                saida = []
                for l, fl in zip(linhas, fila):
                    saida.append({**l, "fps_fonte": fps, "t_fila_ms": round(float(fl), 3), "natureza": "derivado"})
                with open(pasta_cen / f"{parte}_{pasta.name}_{fps}fps.csv", "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(saida[0]))
                    w.writeheader()
                    w.writerows(saida)
                linha = {"parte": parte, "modelo": man["modelo"], "precisao": man["precisao"],
                         "resolucao_fonte": man["resolucao_fonte"], "fps_fonte": fps, "natureza": "derivado",
                         "ambiente": man.get("ambiente", ""), "quadros_validos": len(linhas)}
                linha.update(descrever("t_e2e_ms", e2e))
                linha.update(descrever("t_infer_ms", infer))
                if parte == "borda":
                    linha["t_pre_ms_media"] = round(float(np.mean([float(l["t_pre_ms"]) for l in linhas])), 3)
                    linha["t_post_ms_media"] = round(float(np.mean([float(l["t_post_ms"]) for l in linhas])), 3)
                    linha["cpu_pct_media"] = round(float(np.mean([float(l["cpu_pct"]) for l in linhas])), 1)
                    linha["rss_mb_max"] = round(float(max(float(l["rss_mb"]) for l in linhas)), 1)
                    linha["banda_subida_kbps"] = 0.0
                else:
                    by = np.array([float(l["bytes_jpeg"]) for l in linhas])
                    linha["bytes_jpeg_media"] = round(float(np.mean(by)), 1)
                    linha["t_transmissao_ms_media"] = round(float(np.mean([float(l["t_transmissao_ms"]) for l in linhas])), 3)
                    linha["t_retorno_ms_media"] = round(float(np.mean([float(l["t_retorno_ms"]) for l in linhas])), 3)
                    linha["banda_subida_kbps"] = round(float(np.mean(by)) * 8 * fps / 1000, 1)
                linha["t_fila_ms_media"] = round(float(np.mean(fila)), 3)
                linha["t_fila_ms_final"] = round(float(fila[-1]), 3)
                linha["fps_sustentavel"] = round(1000.0 / float(np.mean(e2e)), 4)
                linha["quadros_descartados_se_ocupado"] = descartados
                linha["taxa_descarte_se_ocupado"] = round(descartados / len(linhas), 4)
                linha["energia_estimada_mj_por_quadro"] = (
                    round(potencia * float(np.mean(e2e)), 3) if (potencia and parte == "borda") else "")
                linha.update({k: q[k] for k in ("map50_pessoa", "f1_050")})
                resumo.append(linha)
            print(f"{parte}/{pasta.name}: {len(linhas)} quadros válidos; mAP@50 {q['map50_pessoa']}", flush=True)

    if not resumo:
        raise SystemExit("Nenhuma combinação concluída em results/e5/.")
    campos = []
    for l in resumo:
        campos += [k for k in l if k not in campos]
    with open(RESULTS / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, restval="")
        w.writeheader()
        w.writerows(resumo)
    with open(RESULTS / "e5" / "qualidade.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(qual[0]))
        w.writeheader()
        w.writerows(qual)
    print(f"{len(resumo)} cenários -> results/summary.csv; {len(qual)} combinações -> results/e5/qualidade.csv")


if __name__ == "__main__":
    main()
