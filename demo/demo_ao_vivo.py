"""Demonstração ao vivo: detecção de pessoas na webcam do Mac, com FP32 x INT8 e três resoluções.

O que faz: lê quadros da webcam (ou de um vídeo, ou de uma pasta de imagens), monta o "quadro da
fonte" como no experimento (imagem redimensionada para res x res, bilinear, sem manter a proporção;
decisão D1) e roda o detector com o MESMO código da coleta da E5 (src/bench/deteccao.py):
pré-processamento, Interpreter.invoke() do LiteRT e decodificação + NMS. Desenha as pessoas com
pontuação >= --limiar e mostra na tela o modelo, a precisão, a resolução, a latência por quadro
(média dos últimos quadros) e o FPS, todos medidos na hora, neste Mac. Para comparação, mostra
também a latência e o mAP@50 da mesma combinação lidos dos arquivos de resultados do artigo.

Teclas na janela:
  m        próximo modelo (YOLOv8n -> SSD-MobileNet V1 -> EfficientDet-Lite0)
  1 2 3    escolhe o modelo direto
  i        alterna FP32 / INT8
  r        próxima resolução da fonte (320 -> 480 -> 640)
  espaço   pausa / continua
  q, Esc   sai

Modo --benchmark: sem janela, mede as 18 combinações em poucos quadros do conjunto de teste do
COCO e imprime a tabela de latência deste Mac ao lado da do artigo. Os números do Mac NÃO
substituem os do artigo (outro processador, outro sistema).

Uso:
  python demo/demo_ao_vivo.py                         # webcam (câmera 0)
  python demo/demo_ao_vivo.py --camera 1              # outra câmera
  python demo/demo_ao_vivo.py --imagens               # reserva: imagens COCO do projeto
  python demo/demo_ao_vivo.py --imagens PASTA         # reserva: qualquer pasta de imagens
  python demo/demo_ao_vivo.py --video arquivo.mp4     # reserva: vídeo
  python demo/demo_ao_vivo.py --benchmark [--quadros 60]
Não gera arquivos (o --benchmark grava um CSV só com --salvar).
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_demo import (MODELOS, NOMES, PASTA_COCO, PRECISOES, RESOLUCOES, RESULTS, Detectores,  # noqa: E402
                        arquivo_modelo, conferir_modelos, lista_teste, quadro_da_fonte,
                        referencia_artigo)

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp"}
AQUECIMENTO_TELA = 5  # quadros descartados da média depois de cada troca de combinação


def descrever_mac() -> str:
    try:
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except OSError:
        chip = platform.processor()
    return f"{chip}, macOS {platform.mac_ver()[0]}, {platform.machine()}"


def medir(det, quadro: np.ndarray):
    """Uma passada do detector, cronometrada como em src/bench/medir_borda.py."""
    a = time.perf_counter()
    x = det.preprocessar(quadro)
    b = time.perf_counter()
    y = det.inferir(x)
    c = time.perf_counter()
    d = det.posprocessar(y)
    e = time.perf_counter()
    return d, {"pre": (b - a) * 1e3, "infer": (c - b) * 1e3, "post": (e - c) * 1e3, "e2e": (e - a) * 1e3}


# --------------------------------------------------------------------------- benchmark
def benchmark(args) -> None:
    teste = lista_teste()[: args.quadros]
    faltam = [t for t in teste if not (PASTA_COCO / t["arquivo"]).exists()]
    if faltam:
        raise SystemExit(f"Faltam {len(faltam)} imagens em {PASTA_COCO}. Rode scripts/setup_macos.sh.")
    aquec = min(args.aquecimento, len(teste) - 1)
    print("=" * 100)
    print("MEDIÇÃO NESTE MAC — números de demonstração, NÃO substituem os do artigo.")
    print(f"  Máquina: {descrever_mac()}; LiteRT com {args.threads} threads.")
    print(f"  {len(teste)} imagens do conjunto de teste COCO ({aquec} de aquecimento descartadas).")
    print("  O artigo mediu 350 quadros (50 de aquecimento) num servidor ARM64 Neoverse-N1 de 2 núcleos.")
    print("=" * 100)
    dets = Detectores(args.threads)
    linhas = []
    cab = (f"{'modelo':<19}{'prec.':<6}{'res':>4} {'entrada':>7} {'pré':>6} {'infer.':>7} {'pós':>6} "
           f"{'e2e':>7} {'p95':>7} {'FPS':>6} | {'artigo e2e':>10} {'artigo FPS':>10}")
    print(cab)
    print("-" * len(cab))
    for modelo in MODELOS:
        for res in RESOLUCOES:
            quadros = [quadro_da_fonte(PASTA_COCO / t["arquivo"], res) for t in teste]
            for precisao in PRECISOES:
                det = dets.obter(modelo, precisao, res)
                tempos = [medir(det, q)[1] for q in quadros][aquec:]
                e2e = [t["e2e"] for t in tempos]
                ref = referencia_artigo(modelo, precisao, res)
                l = {
                    "modelo": modelo, "precisao": precisao, "resolucao_fonte": res,
                    "resolucao_entrada": det.res_entrada, "quadros_validos": len(tempos),
                    "pre_ms": statistics.mean(t["pre"] for t in tempos),
                    "infer_ms": statistics.mean(t["infer"] for t in tempos),
                    "post_ms": statistics.mean(t["post"] for t in tempos),
                    "e2e_ms": statistics.mean(e2e), "e2e_p95_ms": float(np.percentile(e2e, 95)),
                    "artigo_e2e_ms": ref["e2e_ms"] if ref else None,
                }
                l["fps_sustentavel"] = 1000.0 / l["e2e_ms"]
                linhas.append(l)
                art = f"{l['artigo_e2e_ms']:>9.1f}  {1000 / l['artigo_e2e_ms']:>10.1f}" if ref else f"{'—':>10} {'—':>10}"
                print(f"{NOMES[modelo]:<19}{precisao.upper():<6}{res:>4} {det.res_entrada:>7} {l['pre_ms']:>6.2f} "
                      f"{l['infer_ms']:>7.2f} {l['post_ms']:>6.2f} {l['e2e_ms']:>7.2f} {l['e2e_p95_ms']:>7.2f} "
                      f"{l['fps_sustentavel']:>6.1f} | {art}")
    print("-" * len(cab))
    print("Tempos em ms por quadro (média dos quadros válidos). FPS = 1000 / e2e médio.")
    print("\nGanho da quantização (e2e FP32 / e2e INT8):")
    print(f"{'modelo':<19}{'res':>4}  {'Mac':>6}  {'artigo':>7}")
    for modelo in MODELOS:
        for res in RESOLUCOES:
            f32, i8 = (next(x for x in linhas if x["modelo"] == modelo and x["resolucao_fonte"] == res
                            and x["precisao"] == p) for p in PRECISOES)
            art = (f"{f32['artigo_e2e_ms'] / i8['artigo_e2e_ms']:>6.2f}x"
                   if f32["artigo_e2e_ms"] and i8["artigo_e2e_ms"] else f"{'—':>7}")
            print(f"{NOMES[modelo]:<19}{res:>4}  {f32['e2e_ms'] / i8['e2e_ms']:>5.2f}x  {art}")
    print("\nColuna 'artigo': média dos quadros válidos de results/e5/borda/<combinação>/quadros.csv "
          "(ARM64 nativo, Oracle A1, Neoverse-N1, 2 núcleos).")
    print("Lembrete: os números do Mac são de demonstração e não substituem os do artigo.")
    if args.salvar:
        pasta = RESULTS / "mac"
        pasta.mkdir(parents=True, exist_ok=True)
        arq = pasta / f"latencia_mac_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(arq, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0]) + ["maquina", "threads"])
            w.writeheader()
            for l in linhas:
                w.writerow({**{k: round(v, 3) if isinstance(v, float) else v for k, v in l.items()},
                            "maquina": descrever_mac(), "threads": args.threads})
        print(f"CSV gravado em {arq.relative_to(RESULTS.parent)}")


# --------------------------------------------------------------------------- fontes de quadros
class Fonte:
    """Entrega quadros RGB uint8 (H, W, 3) da webcam, de um vídeo ou de uma pasta de imagens."""

    def __init__(self, args):
        import cv2

        self.cv2 = cv2
        self.imagens = None
        self.cap = None
        if args.imagens is not None:
            pasta = Path(args.imagens)
            self.imagens = sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES) if pasta.is_dir() else []
            if not self.imagens:
                raise SystemExit(f"Nenhuma imagem em {pasta}. Rode scripts/setup_macos.sh ou passe outra pasta.")
            self.i = 0
            self.intervalo = args.intervalo
            self.descricao = f"pasta {pasta.name} ({len(self.imagens)} imagens)"
        else:
            if args.video:
                self.cap = cv2.VideoCapture(str(args.video))
                self.descricao = f"vídeo {Path(args.video).name}"
            else:
                self.cap = cv2.VideoCapture(args.camera, cv2.CAP_AVFOUNDATION)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.descricao = f"webcam {args.camera}"
            if not self.cap.isOpened():
                raise SystemExit(
                    f"Não consegui abrir a {self.descricao}.\n"
                    "Se for a webcam: Ajustes do Sistema > Privacidade e Segurança > Câmera, libere o Terminal\n"
                    "(ou o app de onde o comando foi rodado) e abra o terminal de novo.\n"
                    "Reserva: python demo/demo_ao_vivo.py --imagens   (imagens COCO do projeto)")
            self.video = bool(args.video)
        self._ultimo = 0.0
        self._atual = None

    def ler(self) -> np.ndarray | None:
        if self.imagens is not None:
            agora = time.perf_counter()
            if self._atual is None or agora - self._ultimo >= self.intervalo:
                from PIL import Image

                self._atual = np.asarray(Image.open(self.imagens[self.i % len(self.imagens)]).convert("RGB"))
                self.i += 1
                self._ultimo = agora
            return self._atual
        ok, bgr = self.cap.read()
        if not ok and self.video:  # vídeo: volta ao começo
            self.cap.set(self.cv2.CAP_PROP_POS_FRAMES, 0)
            ok, bgr = self.cap.read()
        if not ok:
            return None
        return bgr[:, :, ::-1].copy()

    def fechar(self) -> None:
        if self.cap is not None:
            self.cap.release()


# --------------------------------------------------------------------------- desenho
def fonte_texto(tamanho: int):
    from PIL import ImageFont

    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(f, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(tamanho)


def desenhar(rgb: np.ndarray, deteccoes: np.ndarray, linhas: list[str], limiar: float, fontes) -> np.ndarray:
    from PIL import Image, ImageDraw

    img = Image.fromarray(rgb)
    if img.width < 1280:  # imagens pequenas (COCO): amplia só para exibir; as caixas são normalizadas
        img = img.resize((1280, round(img.height * 1280 / img.width)), Image.BILINEAR)
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    f_grande, f_peq = fontes
    for x1, y1, x2, y2, s in deteccoes:
        if s < limiar:
            continue
        caixa = (x1 * w, y1 * h, x2 * w, y2 * h)
        d.rectangle(caixa, outline=(0, 230, 90), width=3)
        rot = f"pessoa {s:.2f}"
        tw = d.textlength(rot, font=f_peq)
        topo = caixa[1] - 22 if caixa[1] >= 22 else caixa[1]
        d.rectangle((caixa[0], topo, caixa[0] + tw + 8, topo + 22), fill=(0, 230, 90, 220))
        d.text((caixa[0] + 4, topo + 1), rot, fill=(0, 0, 0), font=f_peq)
    larg = max(d.textlength(t, font=f_grande if i == 0 else f_peq) for i, t in enumerate(linhas)) + 24
    alt = 16 + 34 + 24 * (len(linhas) - 1)
    d.rectangle((8, 8, 8 + larg, 8 + alt), fill=(0, 0, 0, 170))
    y = 16
    for i, t in enumerate(linhas):
        d.text((20, y), t, fill=(255, 255, 255) if i else (255, 220, 0), font=f_grande if i == 0 else f_peq)
        y += 34 if i == 0 else 24
    return np.asarray(img)


# --------------------------------------------------------------------------- laço ao vivo
def ao_vivo(args) -> None:
    import cv2

    faltam = conferir_modelos()
    if faltam:
        raise SystemExit("Modelos faltando: " + ", ".join(p.name for p in faltam) + ". Rode scripts/setup_macos.sh.")
    from PIL import Image

    fonte = Fonte(args)
    dets = Detectores(args.threads)
    im, ip, ir = MODELOS.index(args.modelo), PRECISOES.index(args.precisao), RESOLUCOES.index(args.res)
    janela = "Deteccao de pessoas na borda"
    if not args.sem_janela:
        cv2.namedWindow(janela, cv2.WINDOW_NORMAL)
    fontes = (fonte_texto(26), fonte_texto(18))
    mac = descrever_mac()
    hist = collections.deque(maxlen=30)
    tela = collections.deque(maxlen=30)
    contador = 0
    pausado = False
    processados = 0
    ultimo_rgb = None
    print(f"Fonte: {fonte.descricao}. Teclas: m/1/2/3 modelo, i FP32/INT8, r resolução, espaço pausa, q sai.")
    try:
        while True:
            modelo, precisao, res = MODELOS[im], PRECISOES[ip], RESOLUCOES[ir]
            if not pausado or ultimo_rgb is None:
                rgb = fonte.ler()
                if rgb is None:
                    print("A fonte não entregou quadro; encerrando.")
                    break
                ultimo_rgb = rgb
            rgb = ultimo_rgb
            det = dets.obter(modelo, precisao, res)
            # Quadro da fonte (fora da medição, como na coleta): res x res, bilinear, sem manter proporção.
            quadro = np.asarray(Image.fromarray(rgb).resize((res, res), Image.BILINEAR))
            deteccoes, t = medir(det, quadro)
            contador += 1
            if contador > AQUECIMENTO_TELA:
                hist.append(t)
            tela.append(time.perf_counter())
            processados += 1

            ref = referencia_artigo(modelo, precisao, res)
            pessoas = int((deteccoes[:, 4] >= args.limiar).sum())
            if hist:
                e2e = statistics.mean(x["e2e"] for x in hist)
                inf = statistics.mean(x["infer"] for x in hist)
                pre = statistics.mean(x["pre"] for x in hist)
                pos = statistics.mean(x["post"] for x in hist)
                lat = f"Latência por quadro: {e2e:.1f} ms  (pré {pre:.1f} + inferência {inf:.1f} + pós {pos:.1f})"
                fps_s = f"FPS sustentável (1000/latência): {1000 / e2e:.0f}"
            else:
                lat, fps_s = "Latência por quadro: aquecendo...", "FPS sustentável: aquecendo..."
            fps_tela = (len(tela) - 1) / (tela[-1] - tela[0]) if len(tela) > 1 and tela[-1] > tela[0] else 0.0
            linhas = [
                f"{NOMES[modelo]}  {precisao.upper()}  fonte {res}x{res} (entrada do modelo {det.res_entrada})",
                lat,
                f"{fps_s}   |   FPS na tela (inclui câmera e desenho): {fps_tela:.0f}",
                f"Pessoas (pontuação >= {args.limiar:.2f}): {pessoas}",
                f"Medido agora neste Mac: {mac}, {args.threads} threads",
            ]
            if ref:
                mp = f", mAP@50 {ref['map50']:.3f}" if ref["map50"] is not None else ""
                linhas.append(f"Artigo (ARM64 Neoverse-N1, 2 núcleos): {ref['e2e_ms']:.1f} ms{mp}")
            linhas.append("[m/1/2/3] modelo  [i] FP32/INT8  [r] resolução  [espaço] pausa  [q] sair")
            if pausado:
                linhas[0] += "   (PAUSADO)"

            if args.sem_janela:
                if processados % 10 == 0:
                    print(" | ".join(linhas[:4]))
                if args.quadros and processados >= args.quadros:
                    break
                continue
            saida = desenhar(rgb, deteccoes, linhas, args.limiar, fontes)
            cv2.imshow(janela, saida[:, :, ::-1])
            tecla = cv2.waitKey(1) & 0xFF
            trocou = False
            if tecla in (ord("q"), 27):
                break
            elif tecla == ord("m"):
                im, trocou = (im + 1) % len(MODELOS), True
            elif tecla in (ord("1"), ord("2"), ord("3")):
                im, trocou = tecla - ord("1"), True
            elif tecla == ord("i"):
                ip, trocou = (ip + 1) % len(PRECISOES), True
            elif tecla == ord("r"):
                ir, trocou = (ir + 1) % len(RESOLUCOES), True
            elif tecla == ord(" "):
                pausado = not pausado
            if trocou:
                hist.clear()
                contador = 0
                print(f"-> {NOMES[MODELOS[im]]} {PRECISOES[ip].upper()} {RESOLUCOES[ir]}")
            if args.quadros and processados >= args.quadros:
                break
    finally:
        fonte.fechar()
        if not args.sem_janela:
            cv2.destroyAllWindows()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fonte = ap.add_mutually_exclusive_group()
    fonte.add_argument("--camera", type=int, default=0, help="índice da câmera (padrão 0)")
    fonte.add_argument("--video", type=Path, help="arquivo de vídeo (reserva se a câmera falhar)")
    fonte.add_argument("--imagens", nargs="?", const=str(PASTA_COCO), default=None,
                       help="pasta de imagens (sem valor: as imagens COCO do conjunto de teste do projeto)")
    ap.add_argument("--intervalo", type=float, default=1.5, help="segundos por imagem no modo --imagens")
    ap.add_argument("--modelo", choices=MODELOS, default="yolov8n")
    ap.add_argument("--precisao", choices=PRECISOES, default="fp32")
    ap.add_argument("--res", type=int, choices=RESOLUCOES, default=320)
    ap.add_argument("--threads", type=int, default=2, help="threads do LiteRT (padrão 2, como na coleta do artigo)")
    ap.add_argument("--limiar", type=float, default=0.5, help="pontuação mínima para desenhar (padrão 0,5)")
    ap.add_argument("--benchmark", action="store_true", help="mede as 18 combinações e imprime a tabela")
    ap.add_argument("--quadros", type=int, default=None,
                    help="benchmark: imagens por combinação (padrão 60); ao vivo: para depois de N quadros")
    ap.add_argument("--aquecimento", type=int, default=10, help="benchmark: quadros iniciais descartados")
    ap.add_argument("--salvar", action="store_true", help="benchmark: grava CSV em results/mac/")
    ap.add_argument("--sem-janela", action="store_true", help="ao vivo sem abrir janela (teste)")
    args = ap.parse_args()
    if args.benchmark:
        args.quadros = args.quadros or 60
        benchmark(args)
    else:
        ao_vivo(args)


if __name__ == "__main__":
    main()
