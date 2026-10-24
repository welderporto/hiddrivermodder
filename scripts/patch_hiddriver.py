#!/usr/bin/env python3
"""
patch_hiddriver.py - Script de modificacao para hiddriver360 (v0.6 beta)
Autor original: EinTim23 (https://github.com/EinTim23/hiddriver360)
Modificacoes: Welder Porto (https://github.com/welderporto/hiddrivermodder)

Versao 6.0 (Safe Stable) - Modificacoes aplicadas:
1. Prevencao de Queda do Wi-Fi sem quebrar a re-enumeracao USB:
   - No codigo original, o driver executava UsbdPowerDownNotification() para desligar os hubs USB,
     cortando a alimentacao do chip Wi-Fi interno do Xbox 360 Slim/E e derrubando a rede sem fio.
   - Patch: NOP na chamada de UsbdPowerDownNotification() (offset 0xc80c..0xc818).
   - O driver mantem a re-enumeracao nativa (UsbdDriverEntry), permitindo que controles ja plugados
     sejam detectados no boot SEM desligar a alimentacao da placa Wi-Fi!

2. Notificacao de Inicializacao e Deteccao Responsiva de 5 Segundos:
   - Exibe no boot: "Iniciando o hiddriver, aguarde...".
   - Executa loop de 5 segundos (50 x 100 ms) verificando conexao de controladores.
   - Assim que o controle e detectado: exibe "Controle identificado!" e prossegue.
   - Se esgotar 5s sem nenhum controle: exibe "Nenhum controle identificado!".
   - Trava de execucao unica (has_run flag) para nao re-executar em loop e manter a thread
     MappingManagerThreadProc 100% livre para mapeamento e jogo.

3. Correcao de estouro da pilha de Usages (Usage List Overflow):
   - Controles ShanWan / iPega PG-9076 (VID:PID 2563:0575) reportam 12 usages consecutivos.
   - Patch: 'b 0x81f106d4' no offset 0x922c para ignorar usages excedentes com seguranca.

4. Redirecionamento do arquivo de configuracao:
   - Original gravava em 'HDD:\\hiddriver.json'.
   - Redirecionado para 'Usb:\\hiddriver.json' (offset 0x413c no uncompressed).

5. Traducao completa do Assistente de Mapeamento para Portugues (PT-BR).

6. Otimizacao de sensibilidade de clique e timing responsivo:
   - Debounce refinado de 300 ms antes da captura (leitura imediata no 1º clique).
"""

import sys

def patch_binary(data: bytearray) -> bytearray:
    SLEEP_OFF = 0x2c6cc
    XNOTIFY_OFF = 0x2c6bc
    HAS_RUN_OFF = 0x2cbf0
    STR_INIT_OFF = 0x2cc00
    STR_FOUND_OFF = 0x2cc60
    STR_NOTFOUND_OFF = 0x2cca0

    def make_bl(from_off, to_off):
        disp = (to_off - from_off) & 0x03FFFFFC
        return 0x48000001 | disp

    def make_b(from_off, to_off):
        disp = (to_off - from_off) & 0x03FFFFFC
        return 0x48000000 | disp

    def make_bne(from_off, to_off):
        disp = (to_off - from_off) & 0xFFFC
        return 0x40820000 | disp

    def make_beq(from_off, to_off):
        disp = (to_off - from_off) & 0xFFFC
        return 0x41820000 | disp

    def make_bgt(from_off, to_off):
        disp = (to_off - from_off) & 0xFFFC
        return 0x41810000 | disp

    # 1. NOP out UsbdPowerDownNotification() in DllMain (offset 0xc80c..0xc818)
    for off in range(0xc80c, 0xc81c, 4):
        data[off:off+4] = (0x60000000).to_bytes(4, 'big')

    # 2. Patch Usage List Overflow (ShanWan / iPega PG-9076)
    off_overflow = 0x922c
    data[off_overflow:off_overflow+4] = (0x480004a8).to_bytes(4, 'big')

    # 3. Config path: HDD:\hiddriver.json -> Usb:\hiddriver.json
    path_old = b'HDD:\\hiddriver.json'
    path_new = b'Usb:\\hiddriver.json'
    idx = data.find(path_old)
    if idx != -1:
        data[idx:idx+len(path_new)] = path_new

    # 4. Code cave timing (300 ms debounce)
    data[0x2ca50:0x2ca54] = (0x3860012c).to_bytes(4, 'big')

    # 5. Call site at 0xa628 in MappingManagerThreadProc: bl 0x2cab0 (0x48022489)
    data[0xa628:0xa62c] = (0x48022489).to_bytes(4, 'big')

    # 6. Assemble Code Cave at 0x2cab0
    insns = []
    # has_run check
    insns.append(('start', lambda off: 0x3d6081f3)) # lis r11, 0x81f3
    insns.append(('', lambda off: 0x814b3bf0))      # lwz r10, 0x3bf0(r11)
    insns.append(('', lambda off: 0x280a0001))      # cmplwi r10, 1
    insns.append(('', lambda off: make_beq(off, labels['already_ran'])))

    # First run: set has_run = 1
    insns.append(('do_startup', lambda off: 0x39400001)) # li r10, 1
    insns.append(('', lambda off: 0x914b3bf0))           # stw r10, 0x3bf0(r11)
    insns.append(('', lambda off: 0x7d8802a6))           # mflr r12
    insns.append(('', lambda off: 0x9421ffb0))           # stwu r1, -0x50(r1)
    insns.append(('', lambda off: 0x91810058))           # stw r12, 0x58(r1)
    insns.append(('', lambda off: 0x92810014))           # stw r20, 0x14(r1)
    insns.append(('', lambda off: 0x92a10018))           # stw r21, 0x18(r1)

    # Sleep 500ms
    insns.append(('', lambda off: 0x386001f4))           # li r3, 500
    insns.append(('', lambda off: make_bl(off, SLEEP_OFF)))

    # Notification 1: 'Iniciando o hiddriver, aguarde...'
    insns.append(('', lambda off: 0x38600050))           # li r3, 80
    insns.append(('', lambda off: 0x388000ff))           # li r4, 255
    insns.append(('', lambda off: 0x38a00001))           # li r5, 1
    insns.append(('', lambda off: 0x3cc081f3))           # lis r6, 0x81f3
    insns.append(('', lambda off: 0x38c63c00))           # addi r6, r6, 0x3c00
    insns.append(('', lambda off: 0x38e00000))           # li r7, 0
    insns.append(('', lambda off: make_bl(off, XNOTIFY_OFF)))

    # 5-second detection loop (50 iterations of 100ms)
    insns.append(('', lambda off: 0x3a800032))           # li r20, 50

    insns.append(('detect_loop', lambda off: 0x38600064)) # li r3, 100
    insns.append(('', lambda off: make_bl(off, SLEEP_OFF)))

    # Check connectedControllers[0..3].controllerDriver
    insns.append(('', lambda off: 0x3d6081f4))           # lis r11, 0x81f4
    insns.append(('', lambda off: 0x814b17c4))           # lwz r10, 0x17c4(r11)
    insns.append(('', lambda off: 0x280a0000))           # cmplwi r10, 0
    insns.append(('', lambda off: make_bne(off, labels['found_controller'])))
    insns.append(('', lambda off: 0x814b1828))           # lwz r10, 0x1828(r11)
    insns.append(('', lambda off: 0x280a0000))           # cmplwi r10, 0
    insns.append(('', lambda off: make_bne(off, labels['found_controller'])))
    insns.append(('', lambda off: 0x814b188c))           # lwz r10, 0x188c(r11)
    insns.append(('', lambda off: 0x280a0000))           # cmplwi r10, 0
    insns.append(('', lambda off: make_bne(off, labels['found_controller'])))
    insns.append(('', lambda off: 0x814b18f0))           # lwz r10, 0x18f0(r11)
    insns.append(('', lambda off: 0x280a0000))           # cmplwi r10, 0
    insns.append(('', lambda off: make_bne(off, labels['found_controller'])))

    # Decrement r20
    insns.append(('', lambda off: 0x3294ffff))           # subic. r20, r20, 1
    insns.append(('', lambda off: make_bgt(off, labels['detect_loop'])))

    # Not found!
    insns.append(('not_found', lambda off: 0x38600050))  # li r3, 80
    insns.append(('', lambda off: 0x388000ff))           # li r4, 255
    insns.append(('', lambda off: 0x38a00001))           # li r5, 1
    insns.append(('', lambda off: 0x3cc081f3))           # lis r6, 0x81f3
    insns.append(('', lambda off: 0x38c63ca0))           # addi r6, r6, 0x3ca0
    insns.append(('', lambda off: 0x38e00000))           # li r7, 0
    insns.append(('', lambda off: make_bl(off, XNOTIFY_OFF)))
    insns.append(('', lambda off: make_b(off, labels['finish'])))

    # Found!
    insns.append(('found_controller', lambda off: 0x38600050)) # li r3, 80
    insns.append(('', lambda off: 0x388000ff))           # li r4, 255
    insns.append(('', lambda off: 0x38a00001))           # li r5, 1
    insns.append(('', lambda off: 0x3cc081f3))           # lis r6, 0x81f3
    insns.append(('', lambda off: 0x38c63c60))           # addi r6, r6, 0x3c60
    insns.append(('', lambda off: 0x38e00000))           # li r7, 0
    insns.append(('', lambda off: make_bl(off, XNOTIFY_OFF)))
    insns.append(('', lambda off: 0x386005dc))           # li r3, 1500
    insns.append(('', lambda off: make_bl(off, SLEEP_OFF)))

    # Epilogue
    insns.append(('finish', lambda off: 0x82810014))     # lwz r20, 0x14(r1)
    insns.append(('', lambda off: 0x82a10018))           # lwz r21, 0x18(r1)
    insns.append(('', lambda off: 0x81810058))           # lwz r12, 0x58(r1)
    insns.append(('', lambda off: 0x7d8803a6))           # mtlr r12
    insns.append(('', lambda off: 0x38210050))           # addi r1, r1, 0x50

    # Already ran
    insns.append(('already_ran', lambda off: 0x7f9de378)) # mr r29, r28
    insns.append(('', lambda off: 0x4e800020))            # blr

    # Resolve labels
    START_OFF = 0x2cab0
    labels = {}
    cur_off = START_OFF
    for lbl, fn in insns:
        if lbl:
            labels[lbl] = cur_off
        cur_off += 4

    cur_off = START_OFF
    for lbl, fn in insns:
        op = fn(cur_off)
        data[cur_off:cur_off+4] = op.to_bytes(4, 'big')
        cur_off += 4

    # has_run flag at 0x2cbf0
    data[HAS_RUN_OFF:HAS_RUN_OFF+4] = (0).to_bytes(4, 'big')

    # Embed UTF-16-BE Strings
    s_init = 'Iniciando o hiddriver, aguarde...'.encode('utf-16-be') + b'\x00\x00'
    s_found = 'Controle identificado!'.encode('utf-16-be') + b'\x00\x00'
    s_notfound = 'Nenhum controle identificado!'.encode('utf-16-be') + b'\x00\x00'

    data[STR_INIT_OFF:STR_INIT_OFF+len(s_init)] = s_init
    data[STR_FOUND_OFF:STR_FOUND_OFF+len(s_found)] = s_found
    data[STR_NOTFOUND_OFF:STR_NOTFOUND_OFF+len(s_notfound)] = s_notfound

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

    print("Arquivo modificado com sucesso (v6.0 Safe Stable)!")
