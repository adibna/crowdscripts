# Network_Containment — README

Este repositório contém um exemplo de Workflow Fusion SOAR do CrowdStrike e arquivos de suporte para automaticamente conter um host Windows quando uma detecção Crítica for acionada, executar uma rápida limpeza pré-contenção e notificar o usuário final na tela.

## Como o fluxo de trabalho opera

Em alto nível:

- **Gatilho:** Um sinal investigável / EPP com severidade Crítica (5) inicia o fluxo de trabalho.  
- **Verificação de plataforma:** O fluxo de trabalho prossegue apenas para sensores Windows.  
- **Limpeza pré-contenção:** O fluxo de trabalho coloca e executa `CS_pre-containment_cleanup.exe` no dispositivo.  
- **Preparar ativos de notificação:** Ele faz upload de três arquivos para `C:\Windows\TEMP\`:
    - `CS_company_logo.png`
    - `CS_notify_network_containment.html`
    - `CS_notify_network_containment.cmd`  
    Uma vez preparados, ele coloca e executa `CS_notify_network_containment.exe`.  
- **Contenção:** Após um curto intervalo, o dispositivo é colocado em contenção de rede.

Tempos e ações principais usados pelo fluxo de trabalho:

- `PutAndRunFile2` → executa o EXE de limpeza, depois espera 10s antes de preparar os arquivos de notificação e executar o EXE de notificação.  
- `PutFile4/5/6` → coloca o HTML, CMD e PNG em `C:\Windows\TEMP\`.  
- `PutAndRunFile3` → executa o EXE de notificação, depois Sleep (5s) → `ContainDevice`.

O arquivo do fluxo é `Network_Containment.yaml` (um Falcon Workflow exportado). O cabeçalho alerta que editar o YAML diretamente não é recomendado — importe no Falcon e edite lá, se necessário.

## Arquivos explicados

- `Network_Containment.yaml`  
    Falcon Workflow que conecta tudo: aciona em eventos EPP Críticos, restringe para Windows, executa o EXE de limpeza, prepara os ativos de notificação (`.html`, `.cmd`, `.png`), executa o EXE de notificação e, finalmente, contém o dispositivo. Também configura intervalos de espera para garantir a ordem.

- `CS_notify_network_containment.html`  
    Página em tela cheia, com tema escuro, exibida ao usuário indicando que o dispositivo foi contido por razões de segurança, instruindo a não desligar ou desconectar e pedindo para contatar o TI. Exibe um logo da empresa e inclui um telefone de contato placeholder `(00) 1234-5678` e o nome placeholder “Empresa” no rodapé.

- `CS_notify_network_containment.cmd`  
    Script auxiliar colocado em `C:\Windows\TEMP\` cuja finalidade é lançar a notificação HTML (por exemplo, via navegador padrão) usando caminhos locais. É preparado junto com o HTML e o logo e pode ser invocado conforme necessário.

- `CS_pre-containment_cleanup.ps1` → compilado para `CS_pre-containment_cleanup.exe`  
    Script PowerShell destinado a ser executado antes da contenção. Usos típicos incluem parar serviços/processos, remover sessões de rede transitórias, notificar o EDR ou registrar um breadcrumb. O fluxo de trabalho coloca e executa o EXE compilado como a primeira ação no endpoint.

- `CS_notify_network_containment.ps1` → compilado para `CS_notify_network_containment.exe`  
    Script PowerShell que provavelmente abre a notificação (HTML) e/ou garante que ela esteja em destaque para o usuário final após a limpeza ser concluída. O fluxo de trabalho executa esse EXE após preparar o HTML/CMD/PNG.

- `CS_company_logo.png`  
    Logo exibido no topo da notificação HTML. O arquivo é enviado para `C:\Windows\TEMP\` e referenciado pelo HTML.

- `CS_icon.ico`  
    Ícone usado ao compilar os scripts `.ps1` em arquivos `.exe`.

## Construindo os arquivos .exe (usando ps2exe)

Use `ps2exe` (PowerShell) para compilar os dois scripts em executáveis 64-bit com ícone/metadados personalizados. Exemplos de comandos:

```
ps2exe -inputFile .\CS_pre-containment_cleanup.ps1 `
             -outputFile .\CS_pre-containment_cleanup.exe `
             -x64 `
             -iconFile .\CS_icon.ico `
             -title "Falcon pre-containment Cleanup" `
             -company "SuaEmpresa" `
             -description "Falcon - limpeza antes network containment" `
             -Verbose

ps2exe -inputFile .\CS_notify_network_containment.ps1 `
             -outputFile .\CS_notify_network_containment.exe `
             -x64 `
             -iconFile .\CS_icon.ico `
             -title "Falcon Notification" `
             -company "SuaEmpresa" `
             -description "Notificação Falcon - network containment" `
             -Verbose
```

Coloque os EXEs resultantes (e o `.html`, `.cmd`, `.png`) onde seu workflow Falcon possa `PutFile` / `PutAndRunFile` usando os mesmos nomes de arquivo referenciados em `Network_Containment.yaml`.

## Personalização necessária (importante)

- Substitua todos os placeholders “Empresa” pelo nome real da sua empresa (aparece no rodapé do HTML e no texto alternativo do logo).  
- Atualize o número de telefone no HTML (`(00) 1234-5678`) para o contato do seu Service Desk de TI.  
- Ao compilar com `ps2exe`, defina `-company` para sua empresa (por exemplo, `"SuaEmpresa"` → `"AcmeCorp"`).

## Dicas de implantação

- Caminho do logo: O HTML espera `CS_company_logo.png` na mesma pasta do HTML; o fluxo de trabalho coloca ambos em `C:\Windows\TEMP\`.  
- Ordem das operações: Os sleeps (10s antes da notificação; 5s antes da contenção) fazem parte do fluxo de trabalho — ajuste-os no Falcon se seu ambiente precisar de mais/menos tempo para os EXEs terminarem.

## Testes

- Importe `Network_Containment.yaml` em um ambiente Falcon de teste e acione com um evento Crítico sintético.  
- Confirme que o HTML é renderizado e mostra seu nome de empresa e telefone atualizados.  
- Verifique se o host fica contido ao final.

## Disclaimer IA

- Este documento foi gerado com o auxílio de IA e pode conter erros ou omissões.