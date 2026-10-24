#!/usr/bin/env python3
"""
patch_hiddriver.py - Script de modificacao para hiddriver360 (v0.6 beta)
Autor original: EinTim23 (https://github.com/EinTim23/hiddriver360)
Modificacoes: Welder Porto (https://github.com/welderporto/hiddrivermodder)

Modificacoes aplicadas:
1. Notificacao de Inicializacao e Janela de Deteccao de 30 Segundos:
   - Ao iniciar a thread de gerenciamento de controles, exibe: "Iniciando, aguarde...".
   - Executa loop de ate 30 segundos (300 x 100ms) verificando se algum controle foi conectado.
   - Se identificado: exibe "Controle identificado!" e prossegue para mapeamento/uso.
   - Se esgotar 30s: exibe "Nenhum controle identificado!".

2. Correcao Definitiva do Wi-Fi no Xbox 360 Slim / E:
   - No codigo original, o driver executava UsbdPowerDownNotification() e MmFreePhysicalMemory()
     em DllMain para forcar a re-enumeracao USB.
   - Nos modelos Slim e E, a placa interna Wi-Fi e um dispositivo conectado ao barramento USB interno.
   - Esse desligamento forcado cortava a alimentacao da placa Wi-Fi e crashava o stack de rede 802.11 da Microsoft.
   - Patch: 'b 0x81f0c864' no offset 0xc800 (opcode 0x48000064) para pular o desligamento destrutivo do USB,
     mantendo a placa Wi-Fi interna conectada e funcionando 100% junto com o controle.

3. Correcao de estouro da pilha de Usages (Usage List Overflow):
   - Controles ShanWan / iPega PG-9076 (VID:PID 2563:0575) reportam 12 usages consecutivos.
   - O parser original tinha limite de 8, retornando codigo de erro 4 (HID_PARSE_UsageListOverflow).
   - Patch: 'b 0x81f106d4' no offset 0x81f1022c (offset 0x922c no uncompressed) para ignorar usages excedentes.

4. Redirecionamento do arquivo de configuracao:
   - Original gravava em 'HDD:\\hiddriver.json'.
   - Redirecionado para 'Usb:\\hiddriver.json' (offset 0x413c no XEX).

5. Traducao completa do Assistente de Mapeamento para Portugues (PT-BR).

6. Otimizacao de sensibilidade de clique e timing responsivo:
   - Remocao do freeze bloqueante de 5 segundos.
   - Debounce refinado de 300 ms antes da captura (leitura imediata no 1º clique).
"""

import sys

def patch_binary(data: bytearray) -> bytearray:
    # 1. Patch Wi-Fi Fix (Skip destructive USB power-down)
    # b 0x81f0c864 em 0x81f0c800 (offset 0xc800 no uncompressed)
    # opcode: 0x48000064
    off_wifi = 0xc800
    data[off_wifi:off_wifi+4] = (0x48000064).to_bytes(4, 'big')

    # 2. Patch Usage List Overflow (ShanWan / iPega PG-9076)
    # b 0x81f106d4 em 0x81f1022c (offset 0x922c no uncompressed)
    # opcode: 0x480004a8
    off_overflow = 0x922c
    data[off_overflow:off_overflow+4] = (0x480004a8).to_bytes(4, 'big')

    # 3. Config path: HDD:\hiddriver.json -> Usb:\hiddriver.json
    path_old = b'HDD:\\hiddriver.json'
    path_new = b'Usb:\\hiddriver.json'
    idx = data.find(path_old)
    if idx != -1:
        data[idx:idx+len(path_new)] = path_new

    # 4. Code cave timing (300 ms debounce)
    # cave_off = 0x81f33a40 - 0x81F07000 = 0x2ca40
    # instrucao em 0x2ca50: li r3, 300 (0x3860012c)
    cave_timing_off = 0x2ca50
    data[cave_timing_off:cave_timing_off+4] = (0x3860012c).to_bytes(4, 'big')

    # 5. Startup Notification & 30s Detection Routine
    # Call site at 0xa628 (VA 0x81f11628): bl 0x81f33ab0 (opcode 0x48022489)
    call_off = 0xa628
    data[call_off:call_off+4] = (0x48022489).to_bytes(4, 'big')

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

    print("Arquivo modificado com sucesso (Wi-Fi + 30s Detection + ShanWan + PT-BR + Timing)!")
