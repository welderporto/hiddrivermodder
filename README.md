# hiddrivermodder 🎮 (Xbox 360)

Modificação personalizada do **[hiddriver360](https://github.com/EinTim23/hiddriver360)** (desenvolvido originalmente por **EinTim23**), adicionando notificações de status com janela de detecção de 30 segundos, correção definitiva do bug de **Wi-Fi** no Xbox 360 Slim/E, suporte expandido a controles USB/Wireless genéricos (como ShanWan / iPega PG-9076), assistente de mapeamento interativo 100% em **Português (PT-BR)** e otimização de sensibilidade de clique.

---

## ✨ Melhorias e Modificações

### 1. 🔔 Notificação de Inicialização e Detecção em 30 Segundos
* **Feedback Visual:** Assim que o console conclui a inicialização e o driver sobe, é exibida a notificação na tela:
  `🔔 "Iniciando, aguarde..."`
* **Janela de 30 Segundos:** O driver aguarda até 30 segundos enquanto verifica as portas do console, dando tempo suficiente para o usuário ligar o controle (ex: segurar Home + X no iPega) ou plugar o dongle USB.
* **Resultado Imediato:**
  * Se o controle for detectado: `🔔 "Controle identificado!"` (prosseguindo para uso ou mapeamento).
  * Se o tempo expirar sem nenhum controle: `🔔 "Nenhum controle identificado!"` (o driver segue em espera passiva em segundo plano).

### 2. 📶 Correção Definitiva do Bug do Wi-Fi (Xbox 360 Slim / E)
* **O Problema Histórico:** Muitos usuários e canais da comunidade (como *Edu Dicas e Gameplay*) relataram que o Wi-Fi parava de funcionar completamente após o desbloqueio com `hiddriver`. A única "solução" conhecida na comunidade era remover o driver e perder o suporte aos controles.
* **A Causa Raiz Descoberta:** Na função `DllMain`, o autor original executava um reset forçado do barramento USB (`UsbdPowerDownNotification()` e `MmFreePhysicalMemory()`) para forçar a re-enumeração de controles já conectados. Nos consoles Slim e Super Slim (E), a **placa de Wi-Fi interna é conectada via USB interno**. Esse desligamento cortava a energia da placa Wi-Fi, e o sistema da Microsoft marcava o hardware de rede como inexistente.
* **A Solução:** Patch cirúrgico em `0x81f0c800` (`b 0x81f0c864`) ignorando o desligamento forçado do USB. Agora **o Wi-Fi funciona continuamente sem jamais cair**, e os controles USB funcionam juntos com perfeição!

### 3. 🎮 Suporte a Controles ShanWan / iPega PG-9076 (`2563:0575`)
* **Problema no original:** O parser HID nativo do `hiddriver360` possui uma pilha máxima de 8 Usages (`HID_USAGE_STACK_DEPTH = 8`). Dispositivos como o iPega PG-9076 (ShanWan Wireless) reportam sequências de até 12 vendor usages seguidos, gerando o erro silencioso `HID_PARSE_UsageListOverflow` (código 4) e travando a inicialização do controle.
* **Solução:** Patch binário em `0x81f1022c` (`b 0x81f106d4`) instruindo o parser a descartar o excedente seguro em vez de abortar o dispositivo.

### 4. 🇧🇷 Assistente de Mapeamento em Português (PT-BR)
* Todas as notificações na interface do console (`XNotifyUI`) e nomes dos botões foram traduzidos e adaptados para o Português Brasileiro:
  * Mensagem de boas-vindas com nome do controle identificado.
  * Instruções passo a passo: `Aperte o botão A`, `Aperte o Gatilho Direito (RT)`, `Gire o Analógico Esquerdo`, etc.
  * Mensagens de confirmação e salvamento de perfil.

### 5. ⚡ Sensibilidade de Clique Responsiva (Timing Otimizado)
* **Problema:** Na versão anterior, havia uma pausa bloqueante de 5 segundos que fazia a thread dormir e descartar cliques, forçando o usuário a pressionar o botão repetidas vezes até registrar.
* **Solução:** Substituído por um debounce leve de **300 ms** (apenas o suficiente para o banner de notificação subir e evitar repiques elétricos). A leitura do botão agora é imediata no **primeiro clique**!

### 6. 💾 Salvamento do Perfil em `Usb:\hiddriver.json`
* O caminho de salvamento e leitura da configuração foi alterado de `HDD:\hiddriver.json` para `Usb:\hiddriver.json`, permitindo usar o controle diretamente a partir do pendrive de desbloqueio sem conflitar com arquivos residuais do disco interno.

---

## 🚀 Como Instalar no Xbox 360

1. Copie o arquivo `bin/hiddriver.xex` para a raiz do seu pendrive (ex: `Usb:\hiddriver.xex`).
2. Abra o seu arquivo `launch.ini` e garanta que os plugins estão numerados sequencialmente:

```ini
[Plugins]
plugin1 = Usb:\Xbdm.xex
plugin2 = Usb:\hiddriver.xex
plugin3 = Usb:\JRPC2.xex
plugin4 = Usb:\NetISO.xex
```

3. Reinicie o console com o pendrive conectado.
4. Conecte o receptor USB do seu controle iPega / ShanWan e ligue o controle (Home + X).
5. A notificação `Iniciando, aguarde...` surgirá e, em seguida, `Controle identificado!` confirmará o pareamento!

---

## 🛠️ Créditos
* **[EinTim23](https://github.com/EinTim23/hiddriver360)** - Criador do projeto original `hiddriver360`.
* **Welder Porto ([soldadorporto](https://github.com/welderporto))** - Engenharia reversa, notificações de status com detecção em 30s, correção do bug de Wi-Fi, patches binários, tradução PT-BR e ajustes de timing.
