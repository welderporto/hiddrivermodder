# hiddrivermodder 🎮 (Xbox 360)

Modificação personalizada do **[hiddriver360](https://github.com/EinTim23/hiddriver360)** (desenvolvido originalmente por **EinTim23**), adicionando correção definitiva do bug de **Wi-Fi** no Xbox 360 Slim/E, suporte expandido a controles USB/Wireless genéricos (como ShanWan / iPega PG-9076), assistente de mapeamento interativo 100% em **Português (PT-BR)** e otimização de sensibilidade de clique.

---

## ✨ Melhorias e Modificações

### 1. 📶 Correção Definitiva do Bug do Wi-Fi (Xbox 360 Slim / E)
* **O Problema Histórico:** Muitos usuários e canais da comunidade (como *Edu Dicas e Gameplay*) relataram que o Wi-Fi parava de funcionar completamente após o desbloqueio com `hiddriver`. A única "solução" conhecida na comunidade era remover o driver e perder o suporte aos controles.
* **A Causa Raiz Descoberta:** Na função `DllMain`, o autor original executava um reset forçado do barramento USB (`UsbdPowerDownNotification()` e `MmFreePhysicalMemory()`) para forçar a re-enumeração de controles já conectados. Nos consoles Slim e Super Slim (E), a **placa de Wi-Fi interna é conectada via USB interno**. Esse desligamento cortava a energia da placa Wi-Fi, e o sistema da Microsoft marcava o hardware de rede como inexistente.
* **A Solução:** Patch cirúrgico em `0x81f0c800` (`b 0x81f0c864`) ignorando o desligamento forçado do USB. Agora **o Wi-Fi funciona continuamente sem jamais cair**, e os controles USB funcionam juntos com perfeição!

### 2. 🎮 Suporte a Controles ShanWan / iPega PG-9076 (`2563:0575`)
* **Problema no original:** O parser HID nativo do `hiddriver360` possui uma pilha máxima de 8 Usages (`HID_USAGE_STACK_DEPTH = 8`). Dispositivos como o iPega PG-9076 (ShanWan Wireless) reportam sequências de até 12 vendor usages seguidos, gerando o erro silencioso `HID_PARSE_UsageListOverflow` (código 4) e travando a inicialização do controle.
* **Solução:** Patch binário em `0x81f1022c` (`b 0x81f106d4`) instruindo o parser a descartar o excedente seguro em vez de abortar o dispositivo.

### 3. 🇧🇷 Assistente de Mapeamento em Português (PT-BR)
* Todas as notificações na interface do console (`XNotifyUI`) e nomes dos botões foram traduzidos e adaptados para o Português Brasileiro:
  * Mensagem de boas-vindas com nome do controle identificado.
  * Instruções passo a passo: `Aperte o botão A`, `Aperte o Gatilho Direito (RT)`, `Gire o Analógico Esquerdo`, etc.
  * Mensagens de confirmação e salvamento de perfil.

### 4. ⚡ Sensibilidade de Clique Responsiva (Timing Otimizado)
* **Problema:** Na versão anterior, havia uma pausa bloqueante de 5 segundos que fazia a thread dormir e descartar cliques, forçando o usuário a pressionar o botão repetidas vezes até registrar.
* **Solução:** Substituído por um debounce leve de **300 ms** (apenas o suficiente para o banner de notificação subir e evitar repiques elétricos). A leitura do botão agora é imediata no **primeiro clique**!

### 5. 💾 Salvamento do Perfil em `Usb:\hiddriver.json`
* O caminho de salvamento e leitura da configuração foi alterado de `HDD:\hiddriver.json` para `Usb:\hiddriver.json`, permitindo usar o controle diretamente a partir do pendrive de desbloqueio sem conflitar com arquivos residuais do disco interno.

---

## 🚀 Como Instalar no Xbox 360

1. Copie o arquivo `bin/hiddriver.xex` para a raiz do seu pendrive (ex: `Usb:\hiddriver.xex`).
2. Abra o seu arquivo `launch.ini` e adicione o driver na seção `[Plugins]`:

```ini
[Plugins]
plugin1 = Usb:\hiddriver.xex
```

> **Dica sobre Devkit Plugins:** Não carregue `Xbdm.xex` junto caso você não esteja usando depuração via PC. O depurador do XDK foi feito para devkits e não tem suporte a rede sem fio.

3. Reinicie o console com o pendrive conectado.
4. Conecte o receptor USB do seu controle iPega / ShanWan em uma porta USB do Xbox 360.
5. Siga as instruções do assistente em português na tela para mapear seus botões!

---

## 🛠️ Créditos
* **[EinTim23](https://github.com/EinTim23/hiddriver360)** - Criador do projeto original `hiddriver360`.
* **Welder Porto ([soldadorporto](https://github.com/welderporto))** - Engenharia reversa, correção do bug de Wi-Fi, patches binários, tradução PT-BR e ajustes de timing.
