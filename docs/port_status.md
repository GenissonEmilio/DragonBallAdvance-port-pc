# Estado do port para PC/Windows

Atualizado em 26/10/2026, ROM USA `BDVE`, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

**Existe uma prévia nativa que inicia a campanha e executa a primeira fase.
O port completo ainda não está concluído.** O executável dessa integração não
compila um interpretador ARM/Thumb e interrompe a execução quando falta uma
entrada C, em vez de ignorar a chamada.

A reconstrução GBA continua com **242 alvos C/GNU C (33.856 bytes) e 23 alvos
assembly (2.720 bytes): 265 alvos e 36.576 bytes exatos**. As traduções C geradas
para explorar o jogo não aumentam essa contagem. O último agregado geral passou
em **514 testes**, antes da adição dos testes novos de IRQ e PSG; não foi executada
novamente toda a suíte nesta etapa. Os fontes desse conjunto de matching e do
áudio anteriormente validado não foram alterados.

| Área | Evidência atual | Falta verificar ou integrar |
|---|---|---|
| Jogo nativo | Abertura/título: 3.000 quadros; menus/campanha/primeira fase: 10.000 quadros com entrada roteirizada | Paridade de estado, todas as fases, chefes, finais e modos |
| Execução C | 66 serviços de áudio reconstruídos, VSync de áudio e IRQ nativos; demais caminhos usam recompilação estática | Cobertura dos caminhos não exercitados e revisão das traduções |
| IRQ | 66.560 casos e 49 instruções ARM originais, contexto e barramento iguais; seis testes de regressão | Integração e temporização geral de todos os dispositivos |
| Vídeo/entrada | Janela Win32 exercitada por 5.000 quadros; dez teclas, repetição, perda de foco e fechamento verificados em sonda isolada | Paridade visual/estado, controle USB e sessões interativas completas |
| Música original | ID 1: 1.800 quadros, 475.200 pares PCM8 e 1.446.569 pares PCM16 iguais à referência da ROM; consumidor do jogo reproduziu esse corpus | PCM de uma sessão completa contra a ROM e músicas com CGB |
| WASAPI | Janela/GDI em thread separada, MMCSS no produtor e worker; sessões de 5.000 e 20.000 quadros, 16.072.761 pares estéreo na longa, zero esvaziamentos/erros e PCM/imagem/saves iguais à execução offline | Paridade do PCM contra a ROM, suspender/retomar e troca de dispositivo |
| PSG/CGB | Ligado ao relógio do jogo, sem CPU; 160.000 amostras/1.490 escritas e 4.040 observações na virada de contador iguais à referência digital; nove músicas e 14.892 quadros de driver com estado/barramento/PCM8 iguais à ROM no modelo de I/O isolado | Comparar a mistura final PCM/PSG das músicas com a ROM e o hardware de referência |
| Saves | Capacidade real de 512 bytes corrigida; três boots estáveis; 512 bytes iguais à ROM e importados por ela; 4/64 Kbit, estado apagado, busy e 12 processos interrompidos verificados | Progresso de campanha, temporização exata do busy, corte de energia e caminhos Unicode |

A [integração nativa e suas evidências](native_game_integration.md) descreve o
executável, o escopo das comparações e a origem dos componentes. As
[APIs de início/parada e música original](song_playback_native.md) mantêm a
validação contra a ROM e a separação entre C nativo e assembly de matching.

O [áudio integrado ao jogo](game_audio_native.md) descreve o executável atual em
`build/windows_native/bin/dbaa_game.exe`. A mistura digital passou em 150.528
casos contra a implementação original do mGBA. Passaram 20 testes direcionados
de IRQ, PSG, consumidor e mistura; os 514 testes gerais são o agregado histórico
preservado. Mais sete testes de EEPROM/gravação passaram, sem uma nova execução
geral dos 541 testes descobertos. A [validação do salvamento](eeprom_native.md)
detalha o formato e a comparação com a ROM. A execução de combate chegou a
20.000 quadros sem entrada C faltante, atravessando o contador de 32 bits.

O [build Windows](windows_native_build.md) gera os fontes a partir da ROM local
e compila os 108 objetos sem objetos experimentais. Em 20.000 quadros, memória,
imagem, PCM, save e diagnósticos coincidiram com a prévia auditada. O caminho
público de build já usa a [janela assíncrona](async_window_native.md), validada
após observar bloqueios GDI de até 175 ms no produtor síncrono. Os casos de
falha anteriores permanecem registrados. Uma sessão de combate chegou a
60.000 quadros sem entradas faltantes; isso ainda não concluiu a fase nem
validou save de progresso.

Para concluir faltam: corrigir diferenças de vídeo
e temporização observadas, validar movimento/combate/colisões e transições com
estados controlados, testar salvamento e recarga e cobrir as fases e modos
restantes. O pacote preliminar inclui instruções e avisos das dependências. A instalação foi testada em uma cópia isolada de 527 fontes,
com dependências obtidas novamente, ambiente Python novo e 108 objetos
compilados do zero. Em 20.000 quadros, memória, imagem, PCM e save coincidiram
com o executável principal. O arquivo de download do compilador, verificado
por SHA-256, foi reutilizado como cache; nenhuma ferramenta extraída ou objeto
anterior foi herdado.
A prévia ainda usa a ROM local para os recursos e as tabelas do jogo.

A revisão do tradutor encontrou e corrigiu carry incorreto em deslocamentos
e uma classificação ARM incorreta de constantes como acessos à memória.
Passaram [405.376 comparações de instruções](static_instruction_validation.md)
contra a ROM, sem divergências de registradores/flags. O executável corrigido,
compilado em `build/windows_native_shift`, passou em 20.000 quadros com memória,
imagem, PCM e save iguais à prévia anterior, além de 5.000 quadros com WASAPI
sem esvaziamento do endpoint. O executável anterior permanece preservado.

A comparação com a ROM identificou e corrigiu diferenças na fase inicial do
vídeo, no pedido de IRQ de VBlank e no quadro de aplicação da entrada
roteirizada. Com os mesmos botões nos mesmos quadros, coincidem todas as
356 observações de posição/câmera/estado e 600 observações de RNG. No quadro
6.000, os 115.200 bytes RGB e todos os bytes de paleta/VRAM/OAM coincidem.
Restam 160 bytes diferentes em EWRAM, 39 em IWRAM e 37 em I/O nesse estado;
não se afirma equivalência integral de memória ou temporização. A correção
isolada dos registradores de vídeo também passou em 14 casos contra os eventos
de hardware da referência mGBA, sem executar CPU no teste.

`ArcTan` e `ArcTan2` também foram corrigidas no runtime: a versão anterior
deslocava os ângulos de `ArcTan2` em meia volta. Passaram
[196.833 casos de registradores](bios_math_validation.md) contra a referência
de BIOS de software do mGBA, tanto nos auxiliares quanto pela entrada real
de SWI. O novo build de 108 objetos em `build/windows_native_bios` passou em
20.000 quadros com memória/imagem/PCM/save iguais ao build anterior. A sessão
isolada de 5.000 quadros por WASAPI também passou, sem esvaziamentos.
Uma sessão concorrente com compressão de arquivos e teste de campanha teve
50 esvaziamentos; esse resultado foi preservado. A causa exata dessa falha
sob carga ainda não foi estabelecida. Temporização de BIOS e paridade integral
continuam pendentes.

A base está sendo publicada como **v0.1.0-preview**, por solicitação do usuário,
para permitir testes jogando antes da conclusão do port. O pacote Windows exige
a ROM local e inclui iniciador, diagnósticos e avisos das dependências. Consulte
as [instruções da prévia](windows_preview.md) e seu manifesto de validação.

No binário atual da prévia, os 14 casos de vídeo, os limites de entrada e a
persistência EEPROM passaram. O quadro 6.000 preservou a comparação gráfica
exata. Os testes de 5.000 quadros com WASAPI registraram 27 e 3 esvaziamentos;
todo o PCM enviado continuou igual ao offline, mas a continuidade do áudio
**não passou**. Os resultados anteriores sem esvaziamentos descrevem builds
anteriores, e não substituem essa limitação atual.

Os números de matching medem somente código comprovado; não são uma porcentagem
de conclusão do port. Uma captura de gameplay ou a ausência de entradas faltantes
na primeira fase também não demonstra equivalência do jogo inteiro.

A referência de base solicitada para a continuação é
[zelda-tmc-3ds](zelda_base_assessment.md). Sua política de sessões de diagnóstico
foi portada para PowerShell e integrada ao iniciador, preservando logs entre
execuções e mudanças do relógio. A lógica específica de Minish Cap não substitui
a de Dragon Ball; os serviços compartilhados serão aproveitados com validação.
