#!/usr/bin/env python3
"""
patch_hiddriver.py - Script de modificacao para hiddriver360 (v0.6 beta)
Autor original: EinTim23 (https://github.com/EinTim23/hiddriver360)
Modificacoes: Welder Porto (https://github.com/welderporto/hiddrivermodder)

Modificacoes aplicadas:
1. Correcao de estouro da pilha de Usages (Usage List Overflow):
   - Controles ShanWan / iPega PG-9076 (VID:PID 2563:0575) reportam 12 usages consecutivos.
   - O parser original tinha limite de 8, retornando codigo de erro 4 (HID_PARSE_UsageListOverflow).
   - Patch: 'b 0x81f106d4' no offset 0x81f1022c para ignorar usages excedentes em vez de abortar.

2. Redirecionamento do arquivo de configuracao:
   - Original gravava em 'HDD:\\hiddriver.json'.
   - Redirecionado para 'Usb:\\hiddriver.json' (offset 0x413c no XEX).

3. Traducao completa do Assistente de Mapeamento para Portugues (PT-BR).

4. Otimizacao de sensibilidade de clique e timing responsivo:
   - Remocao do freeze bloqueante de 5 segundos.
   - Debounce refinado de 300 ms antes da captura (leitura imediata no 1º clique).
"""

import sys

def patch_binary(data: bytearray) -> bytearray:
    # 1. Patch Usage List Overflow
    # b 0x81f106d4 em 0x81f1022c (offset 0x922c no uncompressed)
    # opcode: 0x480004a8
    off_overflow = 0x922c
    data[off_overflow:off_overflow+4] = (0x480004a8).to_bytes(4, 'big')

    # 2. Config path: HDD:\hiddriver.json -> Usb:\hiddriver.json
    path_old = b'HDD:\\hiddriver.json'
    path_new = b'Usb:\\hiddriver.json'
    idx = data.find(path_old)
    if idx != -1:
        data[idx:idx+len(path_new)] = path_new

    # 3. Code cave timing (300 ms debounce)
    # cave_off = 0x81f33a40 - 0x81F07000 = 0x2ca40
    # instrucao em 0x2ca50: li r3, 300 (0x3860012c)
    cave_timing_off = 0x2ca50
    data[cave_timing_off:cave_timing_off+4] = (0x3860012c).to_bytes(4, 'big')

    return data

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python patch_hiddriver.py <input_uncompressed.xex> <output_uncompressed.xex>")
        sys.exit(1)

    with open(sys.argv[1], 'rb') as f:
        content = bytearray(f.read())

    patched = patch_binary(content)

    with open(sys.argv[2], 'wb') as f:
        f.write(patched)

    print("Arquivo modificado com sucesso!")
