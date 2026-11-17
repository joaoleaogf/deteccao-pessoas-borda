"""E5, nuvem: cliente do baseline de nuvem; mede as 9 combinações FP32 (modelo x resolução).

O que faz: para cada combinação, pede ao servidor que carregue o modelo e envia os 350 quadros do
conjunto de teste, um depois do outro (sem ritmo de câmera), por uma conexão HTTP/1.1 persistente.
O cliente só codifica e envia. Por quadro registra:
  t_codif_ms        quadro da fonte (res x res) -> JPEG qualidade 80
  bytes_jpeg        tamanho do quadro enviado
  t_transmissao_ms  do início do envio até o servidor terminar de receber
  t_srv_decod_ms, t_pre_ms, t_infer_ms, t_post_ms   medidos no servidor
  t_retorno_ms      do servidor enviar a resposta até o cliente terminar de ler
  t_e2e_ms          codificação + transmissão + servidor + retorno
O enlace é limitado com tc netem antes (veja e5.ps1): RTT e subida em configs/network.yaml.
Os cenários de 5, 15 e 30 FPS são derivados depois (src/analysis). Combinação com COMPLETO não roda
de novo.

O que gera, em results/e5/nuvem/<modelo>_fp32_<res>/: quadros.csv, deteccoes.json, manifesto.json, COMPLETO
Roda no contêiner borda-prep. Uso: python src/nuvem/cliente.py --servidor http://servidor:8000 [--quadros N]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import http.client
import io
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
from comum import DATA, RAIZ, RESULTS, ler_yaml  # noqa: E402
from deteccao import quadro_da_fonte  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--servidor", default="http://servidor:8000")
    ap.add_argument("--quadros", type=int, default=None, help="teste curto: limita os quadros")
    ap.add_argument("--saida", type=Path, default=RESULTS / "e5" / "nuvem")
    args = ap.parse_args()

    from PIL import Image

    rede = ler_yaml("network.yaml")
    if any(rede.get(k) is None for k in ("protocolo", "codec", "rtt_ms", "banda_subida_kbps", "servidor")):
        raise SystemExit("configs/network.yaml tem campo nulo: o baseline de nuvem não roda (decisão D5).")
    amostra = ler_yaml("scenarios.yaml")["amostragem"]
    f = ler_yaml("scenarios.yaml")["fatores"]
    with open(RAIZ / "configs" / "conjunto_teste.csv", encoding="utf-8") as fh:
        teste = list(csv.DictReader(fh))[: args.quadros or amostra["quadros_por_combinacao"]]
    u = urlparse(args.servidor)
    tc = subprocess.run(["tc", "qdisc", "show", "dev", "eth0"], capture_output=True, text=True).stdout.strip()

    for modelo in f["modelo"]:
        for res in f["resolucao"]:
            nome = f"{modelo}_fp32_{res}"
            pasta = args.saida / nome
            if (pasta / "COMPLETO").exists():
                print(f"já concluída: {nome}", flush=True)
                continue
            pasta.mkdir(parents=True, exist_ok=True)
            conn = http.client.HTTPConnection(u.hostname, u.port, timeout=300)
            conn.connect()
            conn.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # sem atraso de Nagle
            conn.request("GET", f"/carregar?modelo={modelo}&res={res}")
            carga = json.loads(conn.getresponse().read())
            quadros = [quadro_da_fonte(DATA / "teste_coco" / "imagens" / t["arquivo"], res) for t in teste]
            inicio = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            linhas, deteccoes = [], {}
            for i, (t, q) in enumerate(zip(teste, quadros)):
                a = time.perf_counter()
                buf = io.BytesIO()
                Image.fromarray(q).save(buf, format="JPEG", quality=rede["qualidade_jpeg"])
                dados = buf.getvalue()
                b = time.perf_counter()
                t_envio = time.time()
                conn.request("POST", "/inferir", body=dados, headers={"Content-Type": "image/jpeg"})
                r = json.loads(conn.getresponse().read())
                t_resp = time.time()
                deteccoes[t["image_id"]] = r["deteccoes"]
                linha = {
                    "frame_idx": i, "image_id": t["image_id"], "aquecimento": i < amostra["aquecimento_descartado"],
                    "t_codif_ms": round((b - a) * 1000, 3), "bytes_jpeg": len(dados),
                    "t_transmissao_ms": round((r["t_srv_recebido"] - t_envio) * 1000, 3),
                    "t_srv_decod_ms": round(r["t_srv_decod_ms"], 3), "t_pre_ms": round(r["t_pre_ms"], 3),
                    "t_infer_ms": round(r["t_infer_ms"], 3), "t_post_ms": round(r["t_post_ms"], 3),
                    "t_retorno_ms": round((t_resp - r["t_srv_enviado"]) * 1000, 3),
                }
                linha["t_e2e_ms"] = round(linha["t_codif_ms"] + (t_resp - t_envio) * 1000, 3)
                linha["deteccoes"] = len(r["deteccoes"])
                linhas.append(linha)
            conn.close()
            with open(pasta / "quadros.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
                w.writeheader()
                w.writerows(linhas)
            (pasta / "deteccoes.json").write_text(json.dumps(deteccoes), encoding="utf-8")
            man = {"combinacao": nome, "modelo": modelo, "precisao": "fp32", "resolucao_fonte": res,
                   "arquivo_modelo": carga["arquivo"], "quadros": len(linhas),
                   "aquecimento": amostra["aquecimento_descartado"], "rede": rede, "tc_cliente": tc,
                   "inicio_utc": inicio, "fim_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "arquitetura": platform.machine(), "ambiente": "nativo (x86-64) com rede emulada (tc netem)",
                   "observacao": os.environ.get("E5_OBSERVACAO", "")}
            (pasta / "manifesto.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
            (pasta / "COMPLETO").write_text(man["fim_utc"], encoding="utf-8")
            med = sorted(l["t_e2e_ms"] for l in linhas)[len(linhas) // 2]
            print(f"== {nome} concluída (mediana e2e {med:.0f} ms)", flush=True)
    print("Nuvem: todas as combinações concluídas.", flush=True)


if __name__ == "__main__":
    main()
