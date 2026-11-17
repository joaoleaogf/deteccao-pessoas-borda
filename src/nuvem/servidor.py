"""E5, nuvem: servidor de inferência (linux/amd64 nativo) do baseline de nuvem.

O que faz: servidor HTTP/1.1 de uma conexão por vez. Recebe um quadro em JPEG e devolve as
detecções de pessoa e os tempos medidos no servidor. Usa o mesmo código da borda
(src/bench/deteccao.py), com os modelos FP32.
  GET  /carregar?modelo=<m>&res=<r>   carrega o modelo (Detector novo) para a resolução da fonte r
  POST /inferir                        corpo = JPEG; resposta JSON com:
       t_srv_recebido   relógio de parede (time.time) quando o corpo terminou de chegar
       t_srv_decod_ms   decodificação do JPEG
       t_pre_ms, t_infer_ms, t_post_ms
       t_srv_enviado    relógio de parede logo antes de enviar a resposta
       deteccoes        lista (k, 5) normalizada
O relógio de parede é o mesmo nos dois contêineres (mesmo kernel), o que permite separar ida e volta.
Não gera arquivos. Roda no contêiner borda-prep. Uso: python src/nuvem/servidor.py [--porta 8000]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
from comum import MODELS  # noqa: E402
from deteccao import Detector, resolucao_entrada  # noqa: E402

ESTADO: dict = {}


class Tratador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True  # TCP_NODELAY: sem isso o ACK atrasado soma ~40 ms ao retorno

    def log_message(self, *a):  # silencioso
        pass

    def _responder(self, corpo: dict, codigo: int = 200) -> None:
        dados = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/carregar":
            return self._responder({"erro": "rota"}, 404)
        q = parse_qs(url.query)
        modelo, res = q["modelo"][0], int(q["res"][0])
        arq = MODELS / f"{modelo}_fp32_{resolucao_entrada(modelo, res)}.tflite"
        ESTADO["det"] = Detector(arq, modelo, num_threads=ESTADO["threads"])
        ESTADO["arquivo"] = arq.name
        self._responder({"ok": True, "arquivo": arq.name})

    def do_POST(self):
        import numpy as np
        from PIL import Image

        n = int(self.headers["Content-Length"])
        corpo = self.rfile.read(n)
        t_rec = time.time()
        det = ESTADO["det"]
        a = time.perf_counter()
        quadro = np.asarray(Image.open(io.BytesIO(corpo)).convert("RGB"))
        b = time.perf_counter()
        x = det.preprocessar(quadro)
        c = time.perf_counter()
        y = det.inferir(x)
        d = time.perf_counter()
        dets = det.posprocessar(y)
        e = time.perf_counter()
        resposta = {
            "t_srv_recebido": t_rec, "t_srv_decod_ms": (b - a) * 1000, "t_pre_ms": (c - b) * 1000,
            "t_infer_ms": (d - c) * 1000, "t_post_ms": (e - d) * 1000,
            "deteccoes": np.round(dets, 5).tolist(),
        }
        resposta["t_srv_enviado"] = time.time()
        self._responder(resposta)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--porta", type=int, default=8000)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    ESTADO["threads"] = args.threads
    print(f"servidor na porta {args.porta}", flush=True)
    HTTPServer(("0.0.0.0", args.porta), Tratador).serve_forever()


if __name__ == "__main__":
    main()
