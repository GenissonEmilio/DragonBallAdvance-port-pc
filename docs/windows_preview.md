# Prévia Windows x64 — v0.1.0-preview

Esta versão publica a base atual para testes jogando. Não representa a conclusão
do port nem uma campanha inteira validada. O executável usa recompilação estática
e serviços C nativos; não inclui interpretador ARM/Thumb.

## Executar

Baixe `DBAA-Windows-x64-v0.1.0-preview.zip` na
[página da release](https://github.com/GenissonEmilio/DragonBallAdvance-port-pc/releases/tag/v0.1.0-preview).
Extraia em uma pasta gravável e abra `Jogar.cmd`. O iniciador pede a ROM se
`baserom.gba` não estiver na pasta. Também é possível arrastar uma ROM sobre
`Jogar.cmd`. Não é necessário instalar dependências de desenvolvimento.

Exige a ROM **USA BDVE revisão 0**, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`. Os dados do jogo são carregados
dessa ROM local. O pacote não contém ROM, BIOS, gráficos ou músicas extraídos.
O manifest e `SHA256SUMS.txt` permitem conferir os arquivos distribuídos.

| Tecla | Botão GBA |
|---|---|
| Setas | Direcional |
| Z | A — pular |
| X | B — atacar |
| Enter | Start |
| Backspace | Select |
| A / S | L / R |

A janela pode ser redimensionada e usa escala inteira. Feche a janela para
sair. Ao perder o foco, as teclas presas são liberadas. O áudio usa WASAPI no
dispositivo padrão do Windows. Controle USB e remapeamento não estão integrados.

O save `.eep` fica junto da ROM, com o mesmo nome. Para o primeiro teste, use
uma cópia da ROM em uma pasta separada, preservando seus saves existentes.
O formato e a persistência de EEPROM foram verificados, mas o progresso de
campanha e sua recarga ainda precisam de teste dentro do jogo.

## O que já foi exercitado

- Abertura, menus, início e combate da primeira fase, pausa e retorno ao mapa.
- Reconstruções GBA: 265 alvos, 36.576 bytes exatos; os fontes traduzidos
  automaticamente não aumentam esse número.
- Correções de shifts/flags, `ArcTan`/`ArcTan2`, fase inicial do vídeo, pedidos
  de interrupção, registradores de status e aplicação da entrada roteirizada.
- Comparação com a ROM no quadro 6.000: todos os bytes RGB e das regiões de
  paleta, VRAM e OAM iguais. Posição/câmera/estado e RNG iguais nos pontos
  amostrados, com os mesmos botões nos mesmos quadros.
- Áudio original, saída WASAPI e gravação atômica de EEPROM. O manifesto da
  release registra os testes direcionados executados no binário distribuído.

## Limitações conhecidas

Todas as fases, chefes, finais e modos ainda precisam de cobertura. Existem
diferenças de RAM/I/O e aproximações de temporização/BIOS. A mistura completa
do áudio durante o jogo ainda não foi comparada integralmente com a ROM.
Nesta prévia, duas sessões de 5.000 quadros registraram respectivamente 27 e 3
esvaziamentos do endpoint de áudio; a continuidade de áudio ainda falha, embora
todos os bytes PCM enviados coincidam com a execução offline. Troca de dispositivo, suspensão e caminhos
Unicode não estão garantidos. Entradas C ausentes encerram o processo com
diagnóstico; caminhos não exercitados podem apresentar erros ou travamentos.

O renderer herdado também tem recursos ainda incompletos, incluindo mosaic,
sprites afins e modo 5; a necessidade deles nas fases restantes será avaliada
durante os testes. Não se afirma equivalência integral de vídeo ou hardware.

## Relatar problemas

O iniciador cria `logs/` com uma pasta numerada por sessão: saída padrão, diagnóstico
de execução e relatório de áudio. Não há envio automático de dados.
Abra uma [issue](https://github.com/GenissonEmilio/DragonBallAdvance-port-pc/issues)
e informe a versão da prévia, Windows, fase/tela, passos e resultado esperado.
Anexe os logs da sessão; não envie ROM, BIOS ou recursos extraídos.

O [guia de compilação](windows_native_build.md) reproduz o executável a partir
da sua ROM. As licenças e os fontes correspondentes do componente PSG estão
no pacote em `third_party/` e em [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

A política de sessões numeradas foi adaptada de zelda-tmc-3ds, com créditos e
GPL-3.0-or-later no script `Sessoes.ps1`. A [análise da base](zelda_base_assessment.md)
explica o que foi reaproveitado e quais partes dependem da lógica de Zelda.
