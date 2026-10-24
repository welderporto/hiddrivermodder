# 🤖 Guia & Prompt de IA para Adicionar Qualquer Controle no Xbox 360

Este guia ensina qualquer pessoa a utilizar uma Inteligência Artificial (ChatGPT, Claude, Gemini, Antigravity, etc.) para identificar seu controle USB/sem fio no computador e torná-lo 100% compatível com o plugin **`hiddriver.xex`** no Xbox 360 (RGH / JTAG).

---

## Passo 1: Obter os Dados Técnicos do seu Controle no PC

1. Conecte seu controle USB (ou o receptor/dongle sem fio) em qualquer porta USB do seu computador com Windows.
2. Certifique-se de que o controle está ligado e pareado ao receptor.
3. Abra o terminal (PowerShell ou CMD) na pasta do projeto e execute:
   ```powershell
   python tools/identificar_controle.py
   ```
4. O script identificará automaticamente o seu controle, coletará o **VID**, **PID**, **Report Descriptor** e gerará o texto formatado.

---

## Passo 2: Copiar e Enviar o Prompt para a IA

Copie o modelo de prompt abaixo, preenchendo os dados obtidos (ou use a mensagem já pronta gerada pelo `identificar_controle.py`):

```markdown
Olá! Preciso da sua ajuda para adicionar compatibilidade para o meu controle no Xbox 360 (RGH/JTAG) utilizando o plugin homebrew 'hiddriver.xex' (ou hiddriver360).

Aqui estão as informações técnicas do meu controle obtidas no PC:
- Nome do Dispositivo: [Ex: PS3/PC Gamepad]
- Fabricante: [Ex: SHANWAN / iPega]
- Vendor ID (VID): [Ex: 0x2563 ou 9571 em decimal]
- Product ID (PID): [Ex: 0x0575 ou 1397 em decimal]
- Pacote de Entrada de Exemplo (Neutro): [Ex: [0, 0, 8, 128, 128, 128, 128, ...]]
- HID Report Descriptor (Hex): [Cole a sequência hexadecimal obtida]

Com base nesses dados:
1. Me forneça a configuração JSON exata para adicionar em 'Usb:\hiddriver.json' ou 'HDD:\hiddriver.json'.
2. Explique os mapeamentos de eixos (X, Y, Z, RZ) e informe se há inversão vertical necessária para os analógicos do Xbox 360.
3. Se possível, me mostre como injetar este controle na tabela estática de dispositivos do 'hiddriver.xex' para reconhecimento instantâneo sem precisar do assistente de mapeamento.
```

---

## Passo 3: Como Aplicar a Solução no Xbox 360

A IA responderá fornecendo uma estrutura JSON semelhante a esta:

```json
[
  {
    "vid": 9571,
    "pid": 1397,
    "comment": "iPega PG-9076 (Modo 2.4G)",
    "axes": [
      { "usage": 48, "field": "x" },
      { "usage": 49, "field": "y" },
      { "usage": 50, "field": "z" },
      { "usage": 53, "field": "rz" }
    ],
    "buttons": [
      { "idx": 1, "field": "a_button" },
      { "idx": 2, "field": "b_button" },
      { "idx": 0, "field": "x_button" },
      { "idx": 3, "field": "y_button" },
      { "idx": 4, "field": "l1" },
      { "idx": 5, "field": "r1" },
      { "idx": 6, "field": "l2" },
      { "idx": 7, "field": "r2" },
      { "idx": 8, "field": "back" },
      { "idx": 9, "field": "start" },
      { "idx": 10, "field": "l3" },
      { "idx": 11, "field": "r3" },
      { "idx": 12, "field": "xbox" }
    ],
    "invert": {
      "x": false,
      "y": true,
      "z": false,
      "rx": false,
      "ry": false,
      "rz": true
    }
  }
]
```

### Onde colocar o arquivo:
1. Salve o arquivo com o nome **`hiddriver.json`** na raiz do seu pendrive USB (`Usb:\hiddriver.json`) ou na raiz do disco rígido interno (`HDD:\hiddriver.json`).
2. Reinicie o console ou reconecte o receptor USB. O controle funcionará imediatamente!
