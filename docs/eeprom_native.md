# EEPROM e gravação do port Windows

Verificado em 23/10/2026 na ROM USA BDVE rev0. A inicialização original em
`0x080010C4` chama a configuração EEPROM com valor **4**, isto é, 4 Kbit ou
**512 bytes**. O runtime anterior fixava 14 bits de endereço e arquivos de
8 KiB. Isso não correspondia aos comandos usados pelo jogo.

O runtime agora seleciona a capacidade pelo DMA3 para a EEPROM: comandos com
9/73 halfwords usam seis bits de endereço; 17/81 usam quatorze. Transferências
de resposta de 68 halfwords não mudam essa seleção. A memória apagada começa
com `FF`; a escrita apresenta estado ocupado antes de retornar pronto. O
intervalo configurado é 115.000 ciclos, seguindo o mGBA fixado no projeto;
equivalência ciclo a ciclo desse intervalo ainda não foi comprovada.

Os testes exercitam o barramento e o DMA do runtime efetivamente vinculado ao
jogo, nas capacidades de 512 e 8.192 bytes, incluindo reabertura em processos
separados. Não executam um interpretador de CPU nem aumentam a contagem de
código GBA com matching.

## Compatibilidade comprovada com a ROM

O jogo nativo criou o save e iniciou três vezes mantendo os mesmos 512 bytes.
A assinatura `0x9547424C` fica no setor indicado pelo descritor da ROM, setor
27, com os oito bytes serializados em ordem inversa pelo SDK. A verificação
inicial que procurava essa assinatura no offset zero estava incorreta.

A ROM original foi executada separadamente no mGBA em dois cenários, totalizando
6.000 quadros: EEPROM apagada e importação do save criado pelo port. Nos dois
casos, os **512 bytes completos** coincidiram com o arquivo nativo. Isso valida
a inicialização e a importação desse save; progresso de campanha ainda precisa
de uma alteração feita no jogo, gravação e recarga verificadas.

Os relatórios são `build/native_eeprom_dma_validation/report.json`,
`build/native_game_save_boot_validation/report.json` e
`build/native_game_save_rom_validation/report.json`. O executável atual fica em
`build/next/game_save/bin/dbaa_game.exe`; o build ainda reutiliza objetos
experimentais conferidos por hash e precisa ser promovido a um fluxo limpo e
reproduzível antes da publicação final.

## Proteção do arquivo

`port/windows/save_storage.c` escreve um arquivo irmão com nome exclusivo,
confere a quantidade escrita, chama `FlushFileBuffers`, fecha o arquivo e
substitui o destino com
[MoveFileEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexa).
Uma falha é propagada; o destino existente não é aberto com truncamento. A
finalização drena o áudio antes da gravação durável. Cartuchos EEPROM não
produzem um arquivo SRAM fictício.

Passaram substituição integral, destino somente leitura, rejeição de tamanho
zero e **12 encerramentos forçados de processos próprios**, observados vivos
com um arquivo temporário. O destino permaneceu sempre completo e a gravação
seguinte recuperou-se. Isso não é teste de corte de energia ou de filesystem
de rede. Os caminhos usam a codificação ANSI do runtime atual; suporte Unicode
completo ainda depende da camada de inicialização Windows.

```powershell
.\.venv\Scripts\python.exe build\next\game_save\build.py
.\.venv\Scripts\python.exe tools\verify_native_eeprom_dma.py
.\.venv\Scripts\python.exe tools\verify_game_save_boot.py
.\.venv\Scripts\python.exe tools\verify_game_save_rom.py
.\.venv\Scripts\python.exe tools\verify_save_storage.py
.\.venv\Scripts\python.exe -m unittest tests.test_native_eeprom -v
```

Os sete testes de regressão também exigem que sejam detectadas alterações
intencionais na largura de endereço das duas capacidades, byte apagado, sinal
de ocupado e tamanho persistido. Os sete testes foram executados novamente
contra a etapa `game_timing` e passaram. O port completo continua pendente.
A execução anterior de 5.000 quadros registrou três esvaziamentos do endpoint;
após ativar MMCSS no produtor, as sessões de 5.000 e 20.000 quadros passaram
sem esvaziamentos e com PCM, imagem e saves iguais à execução offline.
