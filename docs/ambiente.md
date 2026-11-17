# Ambiente do experimento

Gerado por `src/prepare/registrar_ambiente.py` a partir de `results/ambiente/`. Não edite à mão:
rode a etapa de novo para atualizar.

## Host

Máquina que roda o Docker. Anotado por e4.sh ou e4.ps1.

```text
data (UTC): 2026-11-16T22:53:26Z
sistema do host: Microsoft Windows 11 Pro 10.0.26300 (64 bits)
docker (cliente): 29.4.1
docker (servidor): 29.4.1, linux/amd64
docker info: Docker Desktop (containerized), kernel 6.18.58.1-microsoft-standard-WSL2, 12 CPUs, 7982563328 bytes de memória
perfil do contêiner ARM64: rpi4b (--cpus=4 --memory=4g)
-- emuladores QEMU registrados (tonistiigi/binfmt --version):
binfmt/e29e7d7 qemu/v10.2.3 go/1.26.4
```

## Contêiner de preparação (linux/amd64)

Imagem borda-prep: exportação e quantização.

```text
sistema do contêiner: Debian GNU/Linux 13 (trixie) (x86_64)
python: Python 3.12.16
-- ambiente /opt/venv-export
ai-edge-litert         2.3.0
ai-edge-quantizer      0.10.1
litert-torch           0.10.0
numpy                  2.5.5
onnx                   1.23.2
pillow                 13.0.0
torch                  2.14.1+cpu
torchvision            0.29.2+cpu
ultralytics            8.4.215
-- ambiente /opt/venv-tf
keras              3.15.1
numpy              2.5.5
pillow             13.0.0
tensorflow         2.21.0
```

## Edge TPU Compiler (linux/amd64)

Imagem borda-edgetpu.

```text
Edge TPU Compiler version 14.1.317412892
```

## Contêiner de medição (linux/arm64, emulado por QEMU)

Imagem borda-arm64.

```text
arquitetura (platform.machine): aarch64
sistema: Linux-6.18.58.1-microsoft-standard-WSL2-aarch64-with-glibc2.41
python: 3.12.16
ai-edge-litert: 2.3.0
numpy: 2.5.5
pillow: 13.0.0
psutil: 7.2.2
```

## Máquina ARM64 nativa da coleta da E5 (Oracle A1)

VM criada só para a coleta da borda (decisão D10) e apagada depois. Anotado pela coleta.

```text
data (UTC): 2026-11-17T16:54:38Z
máquina: Oracle Cloud VM.Standard.A1.Flex (2 OCPU, 12 GB), região São Paulo, criada só para a coleta da E5 (D10)
sistema: Ubuntu 24.04.5 LTS, kernel 7.0.0-1013-oracle, aarch64
docker: 29.1.3
-- lscpu
Architecture:                            aarch64
CPU(s):                                  2
Vendor ID:                               ARM
Model name:                              Neoverse-N1
Thread(s) per core:                      1
Core(s) per socket:                      2
Socket(s):                               1
BogoMIPS:                                50.00
Flags:                                   fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid asimdrdm lrcpc dcpop asimddp
-- memória
               total        used        free      shared  buff/cache   available
Mem:            11Gi       617Mi       8.3Gi       5.3Mi       2.9Gi        11Gi
-- contêiner borda-arm64
aarch64 3.12.16 ai-edge-litert=2.3.0 numpy=2.5.5 pillow=13.0.0 psutil=7.2.2
```
