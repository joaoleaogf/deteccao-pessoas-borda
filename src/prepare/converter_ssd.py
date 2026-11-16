"""E4, passos 2 e 3: converte o SSD-MobileNet V1 para .tflite em FP32 e INT8.

O que faz: parte do grafo congelado do TensorFlow 1 (frozen_inference_graph.pb). Esse grafo
inclui pré e pós-processamento que o conversor não aceita, então recortamos só a rede:
  entrada  "Preprocessor/sub"  imagem 300x300 já normalizada para -1..1
  saídas   "concat"            deslocamentos das caixas, 1917 âncoras x 4
           "concat_1"          pontuações brutas (antes da sigmoide), 1917 âncoras x 91 classes
O FP32 é a conversão direta. O INT8 é quantização pós-treinamento inteira total (pesos,
ativações, entrada e saída em inteiros), calibrada nas 128 imagens do COCO128.
A decodificação das âncoras e a NMS ficam fora do modelo, a cargo dos scripts da E5.

O que gera: models/ssd_mobilenet_v1_fp32_300.tflite e models/ssd_mobilenet_v1_int8_300.tflite.
Roda no ambiente /opt/venv-tf. Modelo já existente não é refeito (use --refazer).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import FONTES, MODELS, imagens_calibracao, ler_yaml, nome_modelo, preprocessar  # noqa: E402

ENTRADA = "Preprocessor/sub"
SAIDAS = ["concat", "concat_1"]


def conversor(res: int):
    import tensorflow as tf

    gd = tf.compat.v1.GraphDef()
    gd.ParseFromString((FONTES / "ssd_mobilenet_v1_frozen_inference_graph.pb").read_bytes())
    # Mantém só os nós necessários para calcular as duas saídas (descarta o pós-processamento).
    gd = tf.compat.v1.graph_util.extract_sub_graph(gd, SAIDAS)

    def importar(x):
        return tf.compat.v1.import_graph_def(
            gd, input_map={f"{ENTRADA}:0": x}, return_elements=[f"{s}:0" for s in SAIDAS]
        )

    funcao = tf.compat.v1.wrap_function(importar, [tf.TensorSpec([1, res, res, 3], tf.float32)])
    return tf.lite.TFLiteConverter.from_concrete_functions([funcao], funcao)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refazer", action="store_true", help="refaz modelos que já existem")
    args = ap.parse_args()

    import tensorflow as tf

    cfg = ler_yaml("models.yaml")["modelos"]["ssd_mobilenet_v1"]
    MODELS.mkdir(exist_ok=True)
    for res in cfg["resolucoes"]:
        fp32 = MODELS / nome_modelo("ssd_mobilenet_v1", "fp32", res)
        int8 = MODELS / nome_modelo("ssd_mobilenet_v1", "int8", res)
        if args.refazer or not fp32.exists():
            fp32.write_bytes(conversor(res).convert())
            print(f"OK {fp32.name}")
        if args.refazer or not int8.exists():
            imagens = imagens_calibracao()

            def representativo():
                for img in imagens:
                    yield [preprocessar(img, "ssd_mobilenet_v1", res)]

            c = conversor(res)
            c.optimizations = [tf.lite.Optimize.DEFAULT]
            c.representative_dataset = representativo
            c.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]  # recusa operador em float
            c.inference_input_type = tf.uint8
            c.inference_output_type = tf.uint8
            int8.write_bytes(c.convert())
            print(f"OK {int8.name}")


if __name__ == "__main__":
    main()
