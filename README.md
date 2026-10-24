# hiddrivermodder 🎮 (Xbox 360)

Modificação personalizada e definitiva do **[hiddriver360](https://github.com/EinTim23/hiddriver360)** (desenvolvido originalmente por **EinTim23**), adicionando:
* Suporte nativo embutido a controles **ShanWan / iPega PG-9076** (`2563:0575`).
* Preservação total da placa interna de **Wi-Fi** no Xbox 360 Slim/E (sem quedas nem travamentos no boot).
* Notificação visual de inicialização e detecção em 5 segundos (`Iniciando o hiddriver, aguarde...`).
* **Menu Interativo Opcional de Mapeamento:** Ao conectar qualquer controle (sincronizado ou não), pergunta se o usuário deseja remapear (`Deslize para a DIREITA por 3s`). Se ignorar, mantém a configuração padrão nativa!
* Assistente de mapeamento interativo 100% em **Português (PT-BR)** com debounce de 300 ms.
* **Ferramenta & Prompt de Inteligência Artificial** para identificar e compatibilizar qualquer controle USB genérico.

---

## ✨ Melhorias e Modificações Definitivas

### 1. 🎮 Suporte Nativo ao iPega PG-9076 / ShanWan (`2563:0575`)
* **Mapeamento Estático Embutido:** O dispositivo foi adicionado diretamente à tabela nativa de controles do driver com todos os 13 botões (A, B, X, Y, LB, RB, LT, RT, Back, Start, L3, R3, Guia Xbox) e 4 eixos (analógicos esquerdo e direito com inversão vertical precisa).
* **Plug & Play Instantâneo:** Ao conectar o receptor USB 2.4G e ligar o controle no modo `L1 + Home`, ele é reconhecido de imediato pelo console como o Controle 1 (XAM), sem exigir assistente de mapeamento forçado.
* **Correção de Overflow HID:** O parser original possuía limite de pilha de 8 Usages. O iPega reporta 12 usages consecutivos, gerando erro `HID_PARSE_UsageListOverflow` (código 4). O patch binário descarta o excedente com segurança.

### 2. 🕹️ Pergunta Interativa de Mapeamento (Deslizar para a Direita 3s ou Ignorar)
* Ao conectar qualquer controle (pareado ou não), surge a notificação na tela:
  `🔔 "Mapear controle? Deslize p/ DIREITA 3s (ou ignore)"`
* **Se o jogador IGNORAR:** Após 5 segundos, a mensagem desaparece e o controle continua funcionando com o mapeamento nativo/salvo de fábrica. Nenhuma tela de mapeamento atrapalha a sua jogatina!
* **Se o jogador QUISER mapear:** Basta segurar o analógico direito (ou esquerdo) para a **DIREITA por 3 segundos**. O assistente passo a passo será iniciado para personalizar botão por botão!

### 3. 📶 Preservação Definitiva do Wi-Fi (Xbox 360 Slim / E)
* **A Causa do Problema:** No `hiddriver` original, o `DllMain` executava um reset bruto no barramento USB (`UsbdPowerDownNotification` + `UsbdDriverEntry`) para forçar o kernel a re-detectar controles já espetados. Como a placa de Wi-Fi interna dos modelos Slim e E fica no mesmo barramento USB interno, ela perdia energia e parava de funcionar.
* **A Solução:** O reset destrutivo foi substituído por um desvio limpo (`b 0xc864`) que preserva os controladores de host USB e a placa de Wi-Fi sem jamais desligá-los. O console inicia com Wi-Fi 100% operacional e sem qualquer congelamento.

### 4. 🔔 Notificação Visual de Inicialização (PT-BR)
* **Feedback Imediato:** Assim que o plugin sobe no boot, exibe o aviso:
  `🔔 "Iniciando o hiddriver, aguarde..."`
* **Checagem de 5 Segundos:** Verifica a presença de controles conectados nas portas USB. Se identificado: `🔔 "Controle identificado!"`. Caso contrário, avisa `🔔 "Nenhum controle identificado!"`.
* **Thread Segura & Latch:** A variável de controle foi alocada na seção de dados graváveis (`.data`), garantindo execução limpa sem exceções de interrupção DSI.

### 5. 🇧🇷 Assistente de Mapeamento em Português & 300ms Debounce
* Todas as mensagens na interface do console (`XNotifyUI`) traduzidas para o Português Brasileiro.
* Debounce ajustado de 5s para **300 ms**, registrando o clique do botão na primeira pressão.
* Configurações salvas automaticamente em `Usb:\hiddriver.json`.

---

## 🤖 Quer Adicionar Outro Controle Usando IA?

Disponibilizamos um fluxo automático completo para você usar qualquer IA (ChatGPT, Gemini, Claude, Antigravity) para deixar seu controle genérico compatível:

1. Conecte o seu controle USB ou receptor sem fio no computador.
2. Execute o diagnosticador automático:
   ```powershell
   python tools/identificar_controle.py
   ```
3. O script lerá o **VID**, **PID** e o **HID Report Descriptor** do controle e gerará o prompt pronto para você copiar!
4. Veja as instruções completas no arquivo: **[PROMPT_IA_COMPATIBILIZAR_CONTROLE.md](PROMPT_IA_COMPATIBILIZAR_CONTROLE.md)**.

---

## 📦 Como Instalar no Xbox 360

1. Copie o arquivo `bin/hiddriver.xex` e `hiddriver.json` para a raiz do seu pendrive USB (`Usb:\`).
2. No seu arquivo `launch.ini`, mantenha o plugin configurado:
```ini
[Plugins]
plugin1 = Usb:\Xbdm.xex
plugin2 = Usb:\hiddriver.xex
plugin3 = Usb:\JRPC2.xex
plugin4 = Usb:\NetISO.xex
```
3. Ligue o console.
4. Conecte o receptor USB do controle (ou plugue-o após o boot).
5. Ligue o controle iPega PG-9076 segurando **`L1` + `HOME`** por 3 segundos (os LEDs 1 e 2 permanecerão acesos fixos).
6. O controle funcionará imediatamente no Dashboard e nos jogos!

---

## 🛠️ Créditos
* **[EinTim23](https://github.com/EinTim23/hiddriver360)** - Criador do projeto original `hiddriver360`.
* **Welder Porto ([welderporto](https://github.com/welderporto))** - Engenharia reversa, correção de Wi-Fi, mapeamento nativo iPega PG-9076, menu opcional de mapeamento 3s, tradução PT-BR, thread segura e integração de IA.
