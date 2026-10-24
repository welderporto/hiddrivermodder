#!/usr/bin/env python3
"""
identificar_controle.py - Diagnosticador e Extrator de Dados de Controles USB para Xbox 360
Compatível com Windows 10/11.

Como usar:
1. Conecte seu controle USB (ou o receptor/dongle sem fio) no computador.
2. Execute este script: python identificar_controle.py
3. Copie o resultado gerado e envie para a IA para gerar a compatibilidade no Xbox 360!
"""

import sys
import time

def check_requirements():
    try:
        import hid
        return hid
    except ImportError:
        print("[!] Modulo 'hidapi' nao encontrado. Instalando automaticamente...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "hidapi"], check=True)
        import hid
        return hid

def main():
    hid = check_requirements()
    print("=" * 65)
    print("  Identificador de Controles USB/Dongle para Xbox 360 (hiddriver)")
    print("=" * 65)
    print("Procurando dispositivos de jogo conectados...")

    devices = hid.enumerate()
    gamepads = []

    for d in devices:
        usage_page = d.get('usage_page', 0)
        usage = d.get('usage', 0)
        prod = d.get('product_string') or "Desconhecido"
        # Usage Page 1 (Generic Desktop), Usage 4 (Joystick) or 5 (Gamepad)
        if usage_page == 1 and usage in (4, 5):
            gamepads.append(d)
        elif any(k in prod.lower() for k in ['gamepad', 'controller', 'joystick', 'pad', 'shanwan', 'ipega']):
            gamepads.append(d)

    # Remover duplicatas por VID/PID
    unique_pads = {}
    for g in gamepads:
        key = (g['vendor_id'], g['product_id'])
        if key not in unique_pads:
            unique_pads[key] = g

    if not unique_pads:
        print("\n[!] Nenhum controle USB ou receptor foi detectado.")
        print("    Certifique-se de que o controle ou dongle USB esta espetado no PC.")
        return

    print(f"\n[+] Encontrado(s) {len(unique_pads)} dispositivo(s) compativel(is):\n")
    pads_list = list(unique_pads.values())
    for i, p in enumerate(pads_list):
        vid = p['vendor_id']
        pid = p['product_id']
        mfg = p.get('manufacturer_string') or "Desconhecido"
        prod = p.get('product_string') or "Dispositivo HID"
        print(f"  [{i+1}] {prod} ({mfg}) -> VID: 0x{vid:04X} ({vid}), PID: 0x{pid:04X} ({pid})")

    target = pads_list[0]
    if len(pads_list) > 1:
        choice = input(f"\nEscolha o numero do controle a testar (1-{len(pads_list)}) [Padrao: 1]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(pads_list):
            target = pads_list[int(choice)-1]

    vid = target['vendor_id']
    pid = target['product_id']
    prod = target.get('product_string') or "Game Controller"
    mfg = target.get('manufacturer_string') or "Standard"

    print(f"\n[-] Abrindo dispositivo 0x{vid:04X}:0x{pid:04X} para leitura...")
    dev = hid.device()
    try:
        dev.open(vid, pid)
    except Exception as e:
        print(f"[!] Erro ao abrir dispositivo: {e}")
        return

    desc_hex = ""
    try:
        desc = dev.get_report_descriptor()
        desc_hex = bytes(desc).hex()
    except Exception:
        pass

    print("[+] Lendo amostra de dados por 2 segundos (mantenha o controle ligado)...")
    sample_packet = []
    for _ in range(40):
        data = dev.read(64, 50)
        if data:
            sample_packet = list(data)
            break

    dev.close()

    print("\n" + "=" * 65)
    print("  COPIE O TEXTO ABAIXO E ENVIE PARA A SUA IA DE PREFERENCIA:")
    print("=" * 65)
    prompt_text = f"""Ola! Preciso da sua ajuda para adicionar compatibilidade para o meu controle no Xbox 360 (RGH/JTAG) utilizando o plugin homebrew 'hiddriver.xex' (ou hiddriver360).

Aqui estao as informacoes tecnicas do meu controle obtidas no PC:
- Nome do Dispositivo: {prod}
- Fabricante: {mfg}
- Vendor ID (VID): 0x{vid:04X} ({vid} em decimal)
- Product ID (PID): 0x{pid:04X} ({pid} em decimal)
- Pacote de Entrada de Exemplo (Estado Neutro): {sample_packet}
- HID Report Descriptor (Hex): {desc_hex if desc_hex else "N/A"}

Com base nesses dados:
1. Me forneca a configuracao JSON exata para adicionar em 'Usb:\\hiddriver.json' ou 'HDD:\\hiddriver.json'.
2. Explique os mapeamentos de eixos (X, Y, Z, RZ) e se ha inversao vertical para os analogicos do Xbox 360.
3. Se possivel, me mostre como injetar este controle na tabela estatica de dispositivos do 'hiddriver.xex' para reconhecimento instantaneo sem assistente de mapeamento.
"""
    print(prompt_text)
    print("=" * 65)

if __name__ == "__main__":
    main()
