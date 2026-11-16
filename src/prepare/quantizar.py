"""Quantização pós-treinamento (PTQ) de um .tflite FP32 com ai-edge-quantizer.

O que faz: recebe um modelo .tflite em float32 e gera a versão INT8 "inteira total": pesos,
ativações, entrada e saída em int8. Os intervalos das ativações são calibrados rodando o
modelo FP32 sobre as 128 imagens de calibração, sempre na mesma ordem.

Não é chamado direto: é usado por exportar_yolo.py (modo inteiro_total) e por
quantizar_efficientdet.py. Roda no ambiente /opt/venv-export.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import imagens_calibracao, preprocessar  # noqa: E402


def quantizar_inteiro_total(fp32: Path, int8: Path, modelo: str, resolucao: int) -> None:
    import numpy as np
    from ai_edge_litert.interpreter import Interpreter
    from ai_edge_quantizer import quantizer, recipe

    # Descobre o nome e o layout da entrada (NHWC ou NCHW) no próprio modelo.
    it = Interpreter(model_path=str(fp32))
    assinatura = next(iter(it.get_signature_list()))
    nome_entrada = next(iter(it.get_signature_list()[assinatura]["inputs"]))
    canais_primeiro = it.get_input_details()[0]["shape"][1] == 3

    amostras = []
    for img in imagens_calibracao():
        x = preprocessar(img, modelo, resolucao)
        if canais_primeiro:
            x = np.ascontiguousarray(x.transpose(0, 3, 1, 2))
        amostras.append({nome_entrada: x})

    qt = quantizer.Quantizer(str(fp32))
    qt.load_quantization_recipe(recipe.static_wi8_ai8())  # pesos int8 + ativações int8
    calibracao = qt.calibrate({assinatura: amostras})
    qt.quantize(calibration_result=calibracao).export_model(str(int8), overwrite=True)
