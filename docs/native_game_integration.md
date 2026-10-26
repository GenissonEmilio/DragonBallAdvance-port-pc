# Integração nativa do jogo: prévia e validação

A prévia em `build/next/game_save/bin/dbaa_game.exe` alcança o título e a primeira
fase da ROM USA BDVE rev0. O port completo ainda não foi aprovado. A execução
nativa mantém registradores/endereços GBA como inteiros e resolve as chamadas
indiretas para funções C do processo Windows; nenhum núcleo ARM/Thumb é
compilado nessa versão. Entradas ausentes, ISA incorreta, profundidade excedida e
retorno inesperado do loop principal geram erro explícito.

O build continua experimental e depende dos artefatos em `build/next/`. O script
`build/next/game_save/build.py` recompila os componentes modificados, confere
os objetos reutilizados e registra hashes em `build.json`. O runner
`build/next/game_audio/run.py` guarda comando, retorno, tempo, hash do executável,
log e captura. Os arquivos de save ficam no sandbox dessa integração.
A [correção EEPROM](eeprom_native.md) acrescenta a capacidade de 512 bytes,
comparação do arquivo com a ROM original e substituição protegida no Windows.
O teste atual de vídeo/áudio preserva bytes e estado, mas ainda detecta
interrupções de reprodução; sua aprovação anterior não é estendida a este build.

## Execuções observadas

- `strict3000.run.json` / `strict3000.native.json`: 3.000 quadros até o título,
  5.880 chamadas de áudio, 6.937 chamadas de IRQ e nenhuma entrada faltante.
- `enter_game2400c.*`: menus e texto de abertura da campanha.
- `first_stage10000b.run.json` / `first_stage10000b.native.json`: 10.000 quadros,
  movimento/ataques roteirizados, Goku e inimigos na primeira fase; 20.239 chamadas
  de áudio, 10.581 chamadas de IRQ, 369.663 despachos indiretos e zero falhas.
- `first_stage10000b.bmp` e `oracle_first_stage10000.bmp`: capturas nativa e da ROM
  no mGBA. Há diferenças de fase temporal/estado; elas não são uma comparação
  pixel a pixel aprovada.

O código C do áudio já validado substitui 66 entradas geradas, além do serviço
VSync. O IRQ em `port/native/irq_dispatch.c` substitui o despachante ARM copiado
para `0x03001F50`. Seu gate `tools/verify_native_irq.py` compara 66.560 combinações
IE/IF com a rotina original em Unicorn: prioridade, agrupamento Serial/Timer3,
confirmação W1C, contexto dos registradores/flags e ordem dos acessos. Os seis
testes novos também detectam alterações intencionais desses comportamentos.

## Tradução estática e fronteiras

A base do tradutor é [gbarecomp](https://github.com/sp00nznet/gbarecomp), MIT,
commit `ac1176f467cbb708f58785e65f36b4f091a8ab20`. Ela recebeu correções locais:
limite candidato de código `0x0811855C`, reconhecimento de retornos com ajuste
intermediário da pilha, passagem explícita para blocos externos e compilação
condicional que remove o interpretador do runtime. O backend Win32 fica em
`port/windows/game_window.c`; o renderizador de software vem dessa base.

A análise original gerou 6.397 candidatos, incluindo duplicatas e entradas
heurísticas. Ponteiros alinhados e padrões limitados de tabelas Thumb acrescentam
2.366 traduções auxiliares, emitidas por `tools/native_emit_extensions.c` em
shards. O conjunto não é um inventário validado de funções do jogo. Nem o limite
código/dados nem candidatos nunca executados são tratados como prova. As fontes
geradas são regeneradas pelo tradutor; não foram corrigidas manualmente.

A ponte cobra trabalho ao relógio dos serviços C: com prefetch, o runtime atribui
custo zero a certos acessos RAM/I/O e espera que os blocos gerados cobrem os
fetches. Sem essa cobrança, o polling de VCOUNT ficava preso. Esse modelo ainda
é aproximado e não representa validação ciclo a ciclo do hardware.

## PSG/CGB independente da CPU

`port/audio/psg_mgba.c` vincula o PSG C do
[mGBA](https://github.com/mgba-emu/mgba), MPL-2.0, commit
`fd9dc5c2cbf234365068855851107e762fc6211b`. O build específico desabilita
`M_CORE_GBA` e `M_CORE_GB` e liga somente chip, temporização, sincronização e
buffers. A tabela de símbolos é auditada para excluir núcleos de CPU. Não se
trata de reconstrução byte a byte dessas rotinas GBA.

O adaptador reproduz os eventos de amostragem, a prioridade do sequenciador de
quadros, larguras/máscaras de I/O, banco de onda e a diferença entre escritas de
byte e halfword quando o áudio está desabilitado. A referência separada em
`tools/psg_oracle.c` usa o I/O e scheduler completos do mGBA, sem executar ROM/CPU.
O teste ampliado compara **160.000 amostras estéreo digitais e 1.490 escritas**,
incluindo square/sweep, envelopes, wave, noise, roteamento e NR52. Esse teste é
de hardware digital; não substitui a comparação do PCM do mixer com a ROM e não
mede PWM ou circuito analógico. Inclui as quatro resoluções SOUNDBIAS e mudanças
durante a execução; outro teste compara 4.040 observações atravessando a virada
do contador de 32 bits. A mistura DAC é validada separadamente em 150.528 casos.

```powershell
.\.venv\Scripts\python.exe tools\verify_native_psg.py
.\.venv\Scripts\python.exe tools\verify_native_irq.py
```

## WASAPI e PCM

O sink para o jogo, `port/windows/wasapi_sink.c`, mantém COM e interfaces WASAPI
em uma thread própria. O produtor entrega PCM16 estéreo a 48 kHz por fila; o
worker usa eventos, pré-buffer e drenagem, registrando a quantidade e hash dos
bytes efetivamente submetidos.

A sonda `tools/wasapi_sink_probe.c` tocou o arquivo derivado da ROM em
`build/native_song_validation/song_reference.pcm`: **1.446.569 pares estéreo**,
FNV-1a64 `051f790bb9359803`, erro HRESULT zero e nenhum esvaziamento do endpoint.
Não houve confirmação humana de escuta ou medição da saída analógica. O sink e
o PSG agora estão ligados ao relógio do jogo. O [relatório da integração de áudio](game_audio_native.md)
separa o corpus PCM validado contra a ROM, a referência digital de hardware e a
comparação do jogo offline com os bytes submetidos ao WASAPI. A última execução
com janela passou em 5.000 quadros e 4.018.027 pares estéreo, sem esvaziamentos;
tentativas anteriores tiveram pausas, e a estabilidade longa continua pendente.

## Critério de conclusão

Faltam paridade do áudio completo, estabilidade longa, validação interativa de vídeo/controles, correções
de diferenças de estado/temporização, sessões longas, salvamento/recarga e
cobertura das fases, chefes e modos. A camada de matching continua separada:
**242 alvos C/GNU C e 23 assembly, 36.576 bytes exatos**. Tradução gerada, IRQ
semântico e síntese PSG não aumentam esses totais.
