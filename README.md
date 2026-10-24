# hiddrivermodder 🎮 (Xbox 360)

Modificação personalizada do **[hiddriver360](https://github.com/EinTim23/hiddriver360)** (desenvolvido originalmente por **EinTim23**), adicionando detecção otimizada com janela responsiva de 5 segundos, re-enumeração USB nativa segura sem queda de Wi-Fi no Xbox 360 Slim/E, suporte expandido a controles USB/Wireless genéricos (como ShanWan / iPega PG-9076), assistente de mapeamento interativo 100% em **Português (PT-BR)** e otimização de sensibilidade de clique.

---

## ✨ Melhorias e Modificações (v5.0)

### 1. 🔔 Notificação de Inicialização e Detecção em 5 Segundos
* **Feedback Visual Imediato:** Assim que o console conclui a inicialização e o driver sobe, é exibida a notificação na tela:
  `🔔 "Iniciando o hiddriver, aguarde..."`
* **Janela Ágil de 5 Segundos:** O driver realiza uma checagem rápida de até 5 segundos (50 iterações de 100 ms) verificando as portas USB.
* **Resultado e Trava Única:**
  * Se o controle estiver conectado ou for ligado: `🔔 "Controle identificado!"` (iniciando o uso ou o assistente).
  * Se o tempo expirar sem nenhum controle: `🔔 "Nenhum controle identificado!"`.
  * **Trava de execução única (`has_run`):** O processo de inicialização ocorre apenas uma vez no boot, mantendo a thread de fundo totalmente livre para reconhecer controles conectados a quente posteriormente.

### 2. 📶 Re-enumeração Segura e Correção do Wi-Fi (Xbox 360 Slim / E)
* **O Problema Histórico:** No código original, o driver executava um reset forçado do barramento (`UsbdPowerDownNotification`), cortando a alimentação dos hubs USB. Como nos modelos Slim e Super Slim (E) a **placa interna de Wi-Fi é conectada ao barramento USB interno**, esse corte derrubava a placa sem fio permanentemente.
* **A Solução v5.0 Definitiva:** O driver agora utiliza a API oficial da Microsoft para drivers de acessórios: **`UsbdTitleDriverResetAllUnrecognizedPorts` (Ordinal 890 do `xboxkrnl.exe`)**.
  * Apenas portas com dispositivos não identificados (como o dongle USB do controle) recebem sinal de reset.
  * A porta interna da placa de Wi-Fi **jamais é tocada nem desligada**.
  * **Resultado:** O Wi-Fi funciona continuamente sem jamais cair, e o controle iPega/ShanWan é detectado perfeitamente!

### 3. 🎮 Suporte a Controles ShanWan / iPega PG-9076 (`2563:0575`)
* **Problema no original:** O parser HID nativo do `hiddriver360` possui uma pilha máxima de 8 Usages (`HID_USAGE_STACK_DEPTH = 8`). Dispositivos como o iPega PG-9076 (ShanWan Wireless) reportam sequências de até 12 vendor usages seguidos, gerando o erro silencioso `HID_PARSE_UsageListOverflow` (código 4) e travando a inicialização do controle.
* **Solução:** Patch binário em `0x81f1022c` (`b 0x81f106d4`) instruindo o parser a descartar o excedente seguro em vez de abortar o dispositivo.

### 4. 🇧🇷 Assistente de Mapeamento em Português (PT-BR)
* Todas as notificações na interface do console (`XNotifyUI`) e nomes dos botões foram traduzidos e adaptados para o Português Brasileiro:
  * Mensagem de boas-vindas com nome do controle identificado.
  * Instruções passo a passo: `Aperte o botão A`, `Aperte o Gatilho Direito (RT)`, `Gire o Analógico Esquerdo`, etc.
  * Mensagens de confirmação e salvamento de perfil.

### 5. ⚡ Sensibilidade de Clique Responsiva (Timing Otimizado)
* **Problema:** Na versão original havia uma pausa bloqueante de 5 segundos que fazia a thread dormir e descartar cliques, forçando o usuário a pressionar o botão repetidas vezes até registrar.
* **Solução:** Substituído por um debounce leve de **300 ms** (apenas o suficiente para o banner de notificação subir e evitar repiques elétricos). A leitura do botão agora é imediata no **primeiro clique**!

---

## 📦 Como Usar no Xbox 360

1. Copie o arquivo `bin/hiddriver.xex` para a raiz do seu pendrive USB (`Usb:\hiddriver.xex`).
2. No seu arquivo `launch.ini`, carregue o plugin:
```ini
[Plugins]
plugin1 = Usb:\Xbdm.xex
plugin2 = Usb:\hiddriver.xex
plugin3 = Usb:\JRPC2.xex
plugin4 = Usb:\NetISO.xex
```
3. Reinicie o console com o pendrive conectado.
4. Conecte o receptor USB do seu controle iPega / ShanWan em uma porta USB do Xbox 360.
5. Ligue o controle (no iPega PG-9076, segure `Home + X` até sincronizar com o dongle).
6. Assim que a notificação `Iniciando o hiddriver, aguarde...` e `Controle identificado!` surgirem, siga o assistente na tela para mapear os botões na primeira vez.
7. As configurações são salvas automaticamente em `Usb:\hiddriver.json`.

---

## 🛠️ Créditos
* **[EinTim23](https://github.com/EinTim23/hiddriver360)** - Criador do projeto original `hiddriver360`.
* **Welder Porto ([soldadorporto](https://github.com/welderporto))** - Engenharia reversa, correção definitiva do bug de Wi-Fi via Ordinal 890, patches binários, tradução PT-BR e ajustes de timing.
