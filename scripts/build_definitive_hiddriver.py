#!/usr/bin/env python3
"""
build_definitive_hiddriver.py - Comprehensive Technical Overhaul & Build Automation
Target: Xbox 360 Homebrew USB Controller Driver hiddriver360 (v0.6 beta)

Root-cause fixes implemented:
1. R1 (DllMain Clean Return):
   - At offset 0x0c800, patch with 'b 0xc864' (0x48000064).
   - Cleanly skips UsbdPowerDownNotification, MmFreePhysicalMemory, and UsbdDriverEntry.
   - Preserves power to internal Slim/E Wi-Fi module on Southbridge USB bus.
   - Guarantees immediate return TRUE (<1ms) to DashLaunch without freezes.

2. R2 (ShanWan / iPega PG-9076 Hook & Wi-Fi Preservation):
   - Preserves USB root hub power state.
   - At offset 0x0922c, write 0x480004a8 ('b 0x96d4') and 0x60000000 ('nop' at 0x09230).
   - Skips error 4 (HID_PARSE_UsageListOverflow) in USB_ProcessHIDReport.

3. R3 (Thread Safety, Continuous Sync Mode & Controller Detection):
   - Cave at 0x2cab0 (VA 0x81F33AB0) spawns via XapiThreadStartup thunk (0x0a628).
   - Latch 'has_run' located in Section 4 (.data RW segment) at VA 0x81F43BF0.
   - Active Synchronization Mode:
     - Startup banner: "Sincronizando controle, aguarde..." (0x2cc00).
     - 5s Fast poll (50 x 100ms).
     - If not detected yet, shows: "Modo sincronizacao ativo..." (0x2cc80).
     - Keeps continuous background poll active (120 x 500ms = 60s) so turning on/plugging in controller is caught immediately!
     - On detection: "Controle sincronizado com sucesso!" (0x2cd00) followed by "Mapear? Segure p/ DIREITA 3s" (0x2cd80).

4. R4 (PT-BR Wizard, 300ms Debounce & Usb:\\hiddriver.json):
   - Complete Portuguese translation of all in-game mapping prompts.
   - 300ms button-press debounce logic in code caves 0x2ca40..0x2ca98.
   - Configuration persistence redirected to 'Usb:\\hiddriver.json' at offset 0x413c.

5. R5 (Native iPega PG-9076 / ShanWan Hardware Support):
   - VID 0x2563, PID 0x0575 injected into expanded static mapping table at VA 0x81F43C00.
   - Full 13-button mapping table at VA 0x81F43CC0 (A, B, X, Y, LB, RB, LT, RT, Back, Start, L3, R3, Guide).
   - Inlined FindStaticMapping patched to scan 8 entries (0xc0 bytes) at VA 0x81F43C00.
   - Instant native recognition without requiring mapping wizard.
"""

import os
import sys
import struct
import subprocess
import shutil

# Offsets in uncompressed XEX
OFF_PTBR_BLOCK_START = 0x03f78
OFF_PTBR_BLOCK_END   = 0x04198
OFF_USAGE_OVERFLOW   = 0x0922c
OFF_DLLMAIN_RESET    = 0x0c800
OFF_THREAD_HOOK      = 0x0a628
OFF_WIZARD_HOOK_1    = 0x0a75c
OFF_WIZARD_HOOK_2    = 0x0ab6c
OFF_WIZARD_HOOK_3    = 0x0ad54

OFF_DEBOUNCE_CAVE    = 0x2ca40
OFF_STARTUP_CAVE     = 0x2cab0
OFF_HAS_RUN_DATA     = 0x34bf0  # VA 0x81F43BF0 in .data (RW)

OFF_STR_INIT         = 0x2cc00  # "Sincronizando controle, aguarde..."
OFF_STR_SYNC_ACTIVE  = 0x2cc80  # "Modo sincronizacao ativo..."
OFF_STR_FOUND        = 0x2cd00  # "Controle sincronizado com sucesso!"
OFF_STR_ASK_MAP      = 0x2cd80  # "Mapear? Segure p/ DIREITA 3s"

OFF_SLEEP_THUNK      = 0x2c6cc
OFF_XNOTIFY_THUNK    = 0x2c6bc

# R5 Native Static Mapping Offsets
OFF_FIND_MAPPING_BASE    = 0x0bbb0  # Instruction: addi r11, r11, 0x1008 -> change to 0x3c00
OFF_FIND_MAPPING_BOUND   = 0x0bbd4  # Instruction: cmplwi cr6, r10, 0xa8  -> change to 0xc0
OFF_ORIG_STATIC_MAPPINGS = 0x32008  # 7 entries x 24 = 168 bytes
OFF_EXPANDED_MAPPINGS    = 0x34c00  # VA 0x81F43C00 (8 entries x 24 = 192 bytes = 0xc0)
OFF_IPEGA_BUTTONS        = 0x34cc0  # VA 0x81F43CC0 (13 entries x 8 = 104 bytes = 0x68)

def assemble_branch(from_off, to_off, lk=False):
    delta = to_off - from_off
    val = (delta & 0x03FFFFFC) | (1 if lk else 0) | 0x48000000
    return val

def assemble_cond_branch(from_off, to_off, bo, bi):
    delta = to_off - from_off
    val = 0x40000000 | (bo << 21) | (bi << 16) | (delta & 0xFFFC)
    return val

def make_bl(from_off, to_off): return assemble_branch(from_off, to_off, lk=True)
def make_b(from_off, to_off): return assemble_branch(from_off, to_off, lk=False)
def make_beq(from_off, to_off): return assemble_cond_branch(from_off, to_off, bo=12, bi=2)
def make_bne(from_off, to_off): return assemble_cond_branch(from_off, to_off, bo=4, bi=2)
def make_bgt(from_off, to_off): return assemble_cond_branch(from_off, to_off, bo=12, bi=1)

def build_startup_cave():
    """Generates the position-independent PowerPC machine code for the active sync startup thread."""
    cave_ins = [
        # Check has_run latch at VA 0x81F43BF0 (.data segment)
        ('start', lambda off: 0x3d6081f4),                     # lis r11, 0x81f4
        ('', lambda off: 0x814b3bf0),                          # lwz r10, 0x3bf0(r11)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['exit_cave'])),  # already ran -> exit
        ('', lambda off: 0x39400001),                          # li r10, 1
        ('', lambda off: 0x914b3bf0),                          # stw r10, 0x3bf0(r11)

        # Initial Sleep(1000)
        ('', lambda off: 0x386003e8),                          # li r3, 1000
        ('', lambda off: make_bl(off, OFF_SLEEP_THUNK)),       # bl Sleep

        # Show 'Sincronizando controle, aguarde...'
        ('', lambda off: 0x38600022),                          # li r3, 34
        ('', lambda off: 0x38800000),                          # li r4, 0
        ('', lambda off: 0x38a00000),                          # li r5, 0
        ('', lambda off: 0x3cc081f3),                          # lis r6, 0x81f3
        ('', lambda off: 0x38c63c00),                          # addi r6, r6, 0x3c00 (0x2cc00)
        ('', lambda off: 0x38e00000),                          # li r7, 0
        ('', lambda off: make_bl(off, OFF_XNOTIFY_THUNK)),     # bl XNotifyQueueUI

        # Sleep(500)
        ('', lambda off: 0x386001f4),                          # li r3, 500
        ('', lambda off: make_bl(off, OFF_SLEEP_THUNK)),       # bl Sleep

        # Fast polling loop (50 x 100ms = 5s)
        ('', lambda off: 0x3a800032),                          # li r20, 50

        ('detect_loop_fast', lambda off: 0x38600064),          # li r3, 100
        ('', lambda off: make_bl(off, OFF_SLEEP_THUNK)),       # bl Sleep

        # Check connectedControllers[0..3]
        ('', lambda off: 0x3d6081f4),                          # lis r11, 0x81f4
        ('', lambda off: 0x814b17c4),                          # lwz r10, 0x17c4(r11) (slot 0)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),
        ('', lambda off: 0x814b1828),                          # lwz r10, 0x1828(r11) (slot 1)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),
        ('', lambda off: 0x814b188c),                          # lwz r10, 0x188c(r11) (slot 2)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),
        ('', lambda off: 0x814b18f0),                          # lwz r10, 0x18f0(r11) (slot 3)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),

        ('', lambda off: 0x3694ffff),                          # addic. r20, r20, -1
        ('', lambda off: make_bgt(off, labels['detect_loop_fast'])),

        # Show 'Modo sincronizacao ativo...'
        ('sync_active_banner', lambda off: 0x38600022),        # li r3, 34
        ('', lambda off: 0x38800000),                          # li r4, 0
        ('', lambda off: 0x38a00000),                          # li r5, 0
        ('', lambda off: 0x3cc081f3),                          # lis r6, 0x81f3
        ('', lambda off: 0x38c63c80),                          # addi r6, r6, 0x3c80 (0x2cc80)
        ('', lambda off: 0x38e00000),                          # li r7, 0
        ('', lambda off: make_bl(off, OFF_XNOTIFY_THUNK)),     # bl XNotifyQueueUI

        # Continuous background polling loop (120 x 500ms = 60s)
        ('', lambda off: 0x3a800078),                          # li r20, 120

        ('detect_loop_bg', lambda off: 0x386001f4),            # li r3, 500
        ('', lambda off: make_bl(off, OFF_SLEEP_THUNK)),       # bl Sleep

        ('', lambda off: 0x3d6081f4),                          # lis r11, 0x81f4
        ('', lambda off: 0x814b17c4),                          # lwz r10, 0x17c4(r11)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),
        ('', lambda off: 0x814b1828),                          # lwz r10, 0x1828(r11)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),
        ('', lambda off: 0x814b188c),                          # lwz r10, 0x188c(r11)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),
        ('', lambda off: 0x814b18f0),                          # lwz r10, 0x18f0(r11)
        ('', lambda off: 0x280a0000),                          # cmplwi r10, 0
        ('', lambda off: make_bne(off, labels['found_controller'])),

        ('', lambda off: 0x3694ffff),                          # addic. r20, r20, -1
        ('', lambda off: make_bgt(off, labels['detect_loop_bg'])),
        ('', lambda off: make_b(off, labels['exit_cave'])),

        # Found Controller Branch
        ('found_controller', lambda off: 0x38600022),          # li r3, 34
        ('', lambda off: 0x38800000),                          # li r4, 0
        ('', lambda off: 0x38a00000),                          # li r5, 0
        ('', lambda off: 0x3cc081f3),                          # lis r6, 0x81f3
        ('', lambda off: 0x38c63d00),                          # addi r6, r6, 0x3d00 (0x2cd00)
        ('', lambda off: 0x38e00000),                          # li r7, 0
        ('', lambda off: make_bl(off, OFF_XNOTIFY_THUNK)),     # bl XNotifyQueueUI

        ('', lambda off: 0x386007d0),                          # li r3, 2000
        ('', lambda off: make_bl(off, OFF_SLEEP_THUNK)),       # bl Sleep

        # Show 'Mapear? Segure p/ DIREITA 3s'
        ('', lambda off: 0x38600022),                          # li r3, 34
        ('', lambda off: 0x38800000),                          # li r4, 0
        ('', lambda off: 0x38a00000),                          # li r5, 0
        ('', lambda off: 0x3cc081f3),                          # lis r6, 0x81f3
        ('', lambda off: 0x38c63d80),                          # addi r6, r6, 0x3d80 (0x2cd80)
        ('', lambda off: 0x38e00000),                          # li r7, 0
        ('', lambda off: make_bl(off, OFF_XNOTIFY_THUNK)),     # bl XNotifyQueueUI

        ('', lambda off: 0x386007d0),                          # li r3, 2000
        ('', lambda off: make_bl(off, OFF_SLEEP_THUNK)),       # bl Sleep

        ('exit_cave', lambda off: 0x81810058),                 # lwz r12, 0x58(r1)
        ('', lambda off: 0x4e800020),                          # blr
    ]

    labels = {}
    cur_off = OFF_STARTUP_CAVE
    for label, _ in cave_ins:
        if label:
            labels[label] = cur_off
        cur_off += 4

    cur_off = OFF_STARTUP_CAVE
    machine_code = bytearray()
    for _, gen in cave_ins:
        ins = gen(cur_off)
        machine_code.extend(ins.to_bytes(4, 'big'))
        cur_off += 4

    return bytes(machine_code)

def patch_binary(base_bytes: bytes, ref_ptbr_bytes: bytes = None) -> bytearray:
    """Applies all root-cause technical overhaul patches to the uncompressed XEX."""
    data = bytearray(base_bytes)

    # 1. R1: DllMain Clean Return (0x0c800)
    print("[-] Applying R1: DllMain Clean Return ('b 0xc864' at 0x0c800)...")
    data[OFF_DLLMAIN_RESET:OFF_DLLMAIN_RESET+4] = (0x48000064).to_bytes(4, 'big')

    # 2. R2: ShanWan / iPega PG-9076 Usage Overflow Patch (0x0922c)
    print("[-] Applying R2: ShanWan Descriptor Overflow Bypass ('b 0x96d4' at 0x0922c)...")
    data[OFF_USAGE_OVERFLOW:OFF_USAGE_OVERFLOW+4] = (0x480004a8).to_bytes(4, 'big')
    data[OFF_USAGE_OVERFLOW+4:OFF_USAGE_OVERFLOW+8] = (0x60000000).to_bytes(4, 'big')  # nop

    # 3. R4: PT-BR Localization, 300ms Debounce, and Usb:\hiddriver.json
    print("[-] Applying R4: Brazilian Portuguese Wizard & 300ms Debounce...")
    if ref_ptbr_bytes is not None:
        data[OFF_PTBR_BLOCK_START:OFF_PTBR_BLOCK_END] = ref_ptbr_bytes[OFF_PTBR_BLOCK_START:OFF_PTBR_BLOCK_END]
    else:
        intro = "Controle detectado. Iniciando mapeamento...".encode("utf-16-be") + b"\x00\x00"
        data[0x3f78:0x3f78+len(intro)] = intro
        btns = b"A\x00B\x00X\x00Y\x00LB\x00RB\x00Select\x00Start\x00L3 (Analog.Esq)\x00R3 (Analog.Dir)\x00\x00Guia\x00LT\x00RT\x00"
        data[0x3feb:0x3feb+len(btns)] = btns
        prompt = "Aperte %hs no controle (segure p/ pular)".encode("utf-16-be") + b"\x00\x00"
        data[0x4050:0x4050+len(prompt)] = prompt
        skip = "Botao pulado".encode("utf-16-be") + b"\x00\x00"
        data[0x40a4:0x40a4+len(skip)] = skip
        dpad = b"D-Pad Esq\x00D-Pad Dir\x00\x00D-Pad Cima\x00D-Pad Baixo\x00"
        data[0x40c4:0x40c4+len(dpad)] = dpad
        path = b"Usb:\\hiddriver.json\x00"
        data[0x413c:0x413c+len(path)] = path
        comp = "Mapeamento pronto! Controle ativo.".encode("utf-16-be") + b"\x00\x00"
        data[0x4150:0x4150+len(comp)] = comp

    # Wizard hooks to debounce cave
    data[OFF_WIZARD_HOOK_1:OFF_WIZARD_HOOK_1+4] = (0x48022315).to_bytes(4, 'big') # bl 0x2ca70
    data[OFF_WIZARD_HOOK_2:OFF_WIZARD_HOOK_2+4] = (0x48021ed5).to_bytes(4, 'big') # bl 0x2ca40
    data[OFF_WIZARD_HOOK_3:OFF_WIZARD_HOOK_3+4] = (0x48021ced).to_bytes(4, 'big') # bl 0x2ca40

    # Debounce code caves (0x2ca40..0x2ca98) with 300ms debounce
    debounce_cave = bytes.fromhex(
        "7d8802a69181fff89421ffc04bfffc713860012c4bfffc79396000ff997f0001"
        "382100408181fff87d8803a64e8000207d8802a69181fff89421ffc04bfffc41"
        "38600bb84bfffc49382100408181fff87d8803a64e800020"
    )
    data[OFF_DEBOUNCE_CAVE:OFF_DEBOUNCE_CAVE+len(debounce_cave)] = debounce_cave

    # 4. R3: Threading Hook, Code Cave & has_run Latch in .data
    print("[-] Applying R3: Active Synchronization Mode Cave (0x2cab0) & .data Latch...")
    data[OFF_THREAD_HOOK:OFF_THREAD_HOOK+4] = (0x48022489).to_bytes(4, 'big') # bl 0x2cab0

    startup_cave = build_startup_cave()
    data[OFF_STARTUP_CAVE:OFF_STARTUP_CAVE+len(startup_cave)] = startup_cave

    # UTF-16BE Notification Strings
    s_init        = "Sincronizando controle, aguarde...".encode("utf-16-be") + b"\x00\x00"
    s_sync_active = "Modo sincronizacao ativo...".encode("utf-16-be") + b"\x00\x00"
    s_found       = "Controle sincronizado com sucesso!".encode("utf-16-be") + b"\x00\x00"
    s_ask_map     = "Mapear? Segure p/ DIREITA 3s".encode("utf-16-be") + b"\x00\x00"

    data[OFF_STR_INIT:OFF_STR_INIT+len(s_init)] = s_init
    data[OFF_STR_SYNC_ACTIVE:OFF_STR_SYNC_ACTIVE+len(s_sync_active)] = s_sync_active
    data[OFF_STR_FOUND:OFF_STR_FOUND+len(s_found)] = s_found
    data[OFF_STR_ASK_MAP:OFF_STR_ASK_MAP+len(s_ask_map)] = s_ask_map

    # Clear has_run latch at VA 0x81F43BF0 (file offset 0x34BF0 in .data)
    data[OFF_HAS_RUN_DATA:OFF_HAS_RUN_DATA+4] = bytes(4)

    # 5. R5: Native iPega PG-9076 / ShanWan (VID 0x2563, PID 0x0575) Static Mapping
    print("[-] Applying R5: Native iPega PG-9076 (VID 0x2563, PID 0x0575) Static Mapping...")
    orig_mappings = bytes(data[OFF_ORIG_STATIC_MAPPINGS:OFF_ORIG_STATIC_MAPPINGS+168])
    data[OFF_EXPANDED_MAPPINGS:OFF_EXPANDED_MAPPINGS+168] = orig_mappings

    # Build 8th entry: iPega PG-9076 (24 bytes)
    ipega_entry = struct.pack(
        ">HHIIIH6B",
        0x2563, 0x0575,           # vid, pid
        0x81F02B70,               # axisMap (kDefaultAxisMap)
        0x06000000,               # axisMapCount (6) + 3 bytes pad
        0x81F43CC0,               # buttonMap (kIpegaButtonMapping at VA 0x81F43CC0)
        0x0D00,                   # buttonMapCount (13) + 1 byte pad
        0x01, 0x00, 0x00, 0x00, 0x01, 0x00 # invert flags (invertY=1, invertRZ=1)
    )
    data[OFF_EXPANDED_MAPPINGS+168:OFF_EXPANDED_MAPPINGS+192] = ipega_entry

    # Build 13-button mapping table at 0x34cc0 (VA 0x81F43CC0)
    ipega_buttons = [
        (1, 0x0F),   # Cross / A
        (2, 0x0E),   # Circle / B
        (0, 0x10),   # Square / X
        (3, 0x0D),   # Triangle / Y
        (4, 0x1D),   # L1 / LB
        (5, 0x1C),   # R1 / RB
        (6, 0x1B),   # L2 / LT
        (7, 0x1A),   # R2 / RT
        (8, 0x19),   # Select / Back
        (9, 0x18),   # Start
        (10, 0x17),  # L3
        (11, 0x16),  # R3
        (12, 0x1E)   # PS / Home / Xbox Guide
    ]
    ipega_btn_bytes = b"".join(struct.pack(">II", idx, field) for idx, field in ipega_buttons)
    data[OFF_IPEGA_BUTTONS:OFF_IPEGA_BUTTONS+len(ipega_btn_bytes)] = ipega_btn_bytes

    # Patch inlined FindStaticMapping in HidAddDeviceHook:
    data[OFF_FIND_MAPPING_BASE:OFF_FIND_MAPPING_BASE+4] = (0x396b3c00).to_bytes(4, "big")
    data[OFF_FIND_MAPPING_BOUND:OFF_FIND_MAPPING_BOUND+4] = (0x2b0a00c0).to_bytes(4, "big")

    return data

def verify_patched_binary(data: bytearray) -> bool:
    """Verifies all required opcodes, data structures, and invariants."""
    print("[-] Verifying patched uncompressed binary invariants...")

    # R1 Verification
    c800 = struct.unpack(">I", data[0x0c800:0x0c804])[0]
    assert c800 == 0x48000064, f"R1 Failed: Expected 0x48000064 at 0x0c800, got {hex(c800)}"

    # R2 Verification
    ov = struct.unpack(">I", data[0x0922c:0x09230])[0]
    assert ov == 0x480004a8, f"R2 Failed: Expected 0x480004a8 at 0x0922c, got {hex(ov)}"

    # R3 Threading & Latch Verification
    thook = struct.unpack(">I", data[0x0a628:0x0a62c])[0]
    assert thook == 0x48022489, f"R3 Failed: Expected 0x48022489 at 0x0a628, got {hex(thook)}"

    cave_start = struct.unpack(">I", data[0x2cab0:0x2cab4])[0]
    assert cave_start == 0x3d6081f4, f"R3 Failed: Cave must reference .data (0x81f4), got {hex(cave_start)}"

    latch_load = struct.unpack(">I", data[0x2cab4:0x2cab8])[0]
    assert latch_load == 0x814b3bf0, f"R3 Failed: Cave must load 0x3bf0(r11), got {hex(latch_load)}"

    dec_op = struct.unpack(">I", data[0x2cb34:0x2cb38])[0]
    assert dec_op == 0x3694ffff, f"R3 Failed: Loop decrement must be addic. (0x3694ffff), got {hex(dec_op)}"

    latch_val = struct.unpack(">I", data[0x34bf0:0x34bf4])[0]
    assert latch_val == 0, f"R3 Failed: has_run at 0x34bf0 must be 0, got {latch_val}"

    # R4 Verification
    deb = struct.unpack(">I", data[0x2ca50:0x2ca54])[0]
    assert deb == 0x3860012c, f"R4 Failed: Debounce must be 300ms (0x3860012c), got {hex(deb)}"

    path = data[0x413c:0x414f]
    assert path == b"Usb:\\hiddriver.json", f"R4 Failed: Path must be Usb:\\hiddriver.json, got {path}"

    s_init_read = data[0x2cc00:0x2cc46].decode("utf-16-be").rstrip("\x00")
    assert s_init_read == "Sincronizando controle, aguarde...", f"Banner init mismatch: {s_init_read}"

    s_sync_read = data[0x2cc80:0x2ccb8].decode("utf-16-be").rstrip("\x00")
    assert s_sync_read == "Modo sincronizacao ativo...", f"Banner sync active mismatch: {s_sync_read}"

    # R5 Native Mapping Verification
    map_base = struct.unpack(">I", data[0x0bbb0:0x0bbb4])[0]
    assert map_base == 0x396b3c00, f"R5 Failed: Expected 0x396b3c00 at 0x0bbb0, got {hex(map_base)}"

    map_bound = struct.unpack(">I", data[0x0bbd4:0x0bbd8])[0]
    assert map_bound == 0x2b0a00c0, f"R5 Failed: Expected 0x2b0a00c0 at 0x0bbd4, got {hex(map_bound)}"

    ipega_vid, ipega_pid = struct.unpack_from(">HH", data, 0x34c00 + 168)
    assert ipega_vid == 0x2563 and ipega_pid == 0x0575, f"R5 Failed: Entry 7 VID/PID must be 0x2563:0x0575, got {hex(ipega_vid)}:{hex(ipega_pid)}"

    btn_cnt = struct.unpack_from(">H", data, 0x34c00 + 168 + 16)[0] >> 8
    assert btn_cnt == 13, f"R5 Failed: Entry 7 button count must be 13, got {btn_cnt}"

    first_btn_idx, first_btn_field = struct.unpack_from(">II", data, 0x34cc0)
    assert first_btn_idx == 1 and first_btn_field == 0x0F, f"R5 Failed: Button 0 must be Cross->A (1, 0x0F)"

    print("[+] All binary invariants VERIFIED successfully!")
    return True

def package_xex(tools_dir: str, uncompressed_path: str, output_path: str) -> bool:
    """Invokes xextool.exe to package Devkit Encrypted Compressed DLL."""
    xextool = os.path.join(tools_dir, "xextool.exe")
    if not os.path.exists(xextool):
        print(f"[!] ERROR: xextool not found at {xextool}")
        return False

    cmd = [xextool, "-m", "d", "-c", "c", "-e", "e", "-o", output_path, uncompressed_path]
    print(f"[-] Packaging: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] xextool failed: {res.stderr}")
        return False

    if not os.path.exists(output_path):
        print(f"[!] ERROR: Output file {output_path} was not generated!")
        return False

    size = os.path.getsize(output_path)
    print(f"[+] Successfully generated packaged XEX: {output_path} ({size} bytes)")
    return True

def deploy_to_console(source_xex: str, target_root: str):
    """Safely deploys the built XEX to the console root drive (E:\\)."""
    if not os.path.exists(target_root):
        print(f"[*] Target drive {target_root} is not mounted. Skipping auto-deploy.")
        return

    dest_xex = os.path.join(target_root, "hiddriver.xex")
    bak_xex = os.path.join(target_root, "hiddriver.xex.bak_pre_final")

    print(f"[-] Deploying to console target: {dest_xex}")
    try:
        if os.path.exists(dest_xex) and not os.path.exists(bak_xex):
            shutil.copy2(dest_xex, bak_xex)
            print(f"[+] Created safety backup at {bak_xex}")

        shutil.copy2(source_xex, dest_xex)
        print(f"[+] Successfully deployed {dest_xex}!")
    except Exception as e:
        print(f"[!] Deployment error: {e}")

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.join(workspace, "tools")
    base_file = os.path.join(workspace, "hiddriver_uncompressed.xex")
    ref_ptbr_file = os.path.join(workspace, "hiddriver_uncompressed_ptbr_v2.xex")
    if not os.path.exists(ref_ptbr_file):
        ref_ptbr_file = os.path.join(workspace, "hiddriver_uncompressed_ptbr.xex")

    output_uncompressed = os.path.join(workspace, "hiddriver_uncompressed_final.xex")
    output_packaged = os.path.join(workspace, "hiddriver.xex")

    print("=================================================================")
    print("  Xbox 360 hiddriver360 Active Sync Mode Build                   ")
    print("=================================================================")

    if not os.path.exists(base_file):
        print(f"[!] Base file not found: {base_file}")
        sys.exit(1)

    with open(base_file, "rb") as f:
        base_data = f.read()

    ref_ptbr_data = None
    if os.path.exists(ref_ptbr_file):
        print(f"[-] Using reference PT-BR data from {ref_ptbr_file}")
        with open(ref_ptbr_file, "rb") as f:
            ref_ptbr_data = f.read()

    patched = patch_binary(base_data, ref_ptbr_data)
    verify_patched_binary(patched)

    with open(output_uncompressed, "wb") as f:
        f.write(patched)
    print(f"[+] Saved uncompressed patched binary: {output_uncompressed}")

    if not package_xex(tools_dir, output_uncompressed, output_packaged):
        print("[!] Packaging failed!")
        sys.exit(1)

    # Deploy to console drive E:\
    deploy_to_console(output_packaged, "E:\\")

    print("\n=================================================================")
    print("  Build & Deployment SUCCEEDED: Active Sync Mode Ready!          ")
    print("=================================================================")

if __name__ == "__main__":
    main()
