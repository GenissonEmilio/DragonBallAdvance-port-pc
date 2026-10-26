# CGB no port nativo

`Cgb_Stop` (`0x0810B834`), `Cgb_Update` (`0x0810B8EC`) e sua dependência
`Cgb_UpdateVolume` (`0x0810B884`) estão ligadas ao despachante **C Windows x64**.
O lado nativo usa endereços GBA de 32 bits e callbacks de memória; esses três
serviços não executam ARM.

O build GBA recompilou os fontes C/GNU C e comparou integralmente a seção
`.text` no endereço original, incluindo pools de literais e padding:

| Rotina | Código | Literais | Padding | Bytes idênticos |
|---|---:|---:|---:|---:|
| Cgb_Stop | 60 | 16 | 4 | 80/80 |
| Cgb_UpdateVolume | 104 | 0 | 0 | 104/104 |
| Cgb_Update | 1.008 | 76 | 16 | 1.100/1.100 |

São **1.284 bytes contínuos**, de `0x0810B834` a `0x0810BD38` exclusivo,
que já pertenciam ao matching C. O total permanece em **242 alvos C/GNU C,
33.856 bytes, mais 23 assembly, 2.720 bytes**: **265 rotinas e 36.576 bytes
exatos**. Há agora **57 serviços nativos** e **36/36 slots da tabela ligados**.

O perfil GBA de Update é agbcc `-O1 -mthumb-interwork`. Stop usa `-O2
-mthumb-interwork -fprologue-bugfix`. Os fontes matching mantêm suas restrições
GNU C vazias; nenhum assembly gerado foi alterado. As quinze referências a labels
de Update são 60 bytes de metadados de debugger não alocados, fora da imagem ROM.

## Comportamento integrado

Stop recebe o byte inferior do argumento. Os canais 1 e 2 recebem escritas de
envelope/trigger; o canal 3 desliga a wave, e os demais valores seguem o caminho
de noise. Todas essas escritas têm largura de um byte.

Volume calcula o roteamento e o objetivo do envelope a partir de right/left,
sustain e panMask. Os caminhos direcionais limitam o objetivo a 15; o caminho
estéreo balanceado conserva a soma completa. As releituras e a ordem de gravação
dos campos foram preservadas.

Update percorre quatro registros de 64 bytes. Lê o contador global de
`sound+0x0A`: se o valor inicial é zero, grava 14; caso contrário, decrementa.
Quando o valor já atualizado é zero, pode processar um segundo passo do envelope.
Preserva os wraps de bytes e as comparações signed
usadas em decay, release e eco, junto aos testes de zero das taxas.

A rotina inicia e encerra notas, atualiza ataque/decay/sustain/release/eco,
roteamento estéreo e frequência. O arredondamento tonal depende do byte de bias:
até `0x3F` usa `(frequency+2)&0x7FC`; até `0x7F` usa
`(frequency+1)&0x7FE`, com overflow unsigned de 32 bits.
Noise conserva o bit 3 do registrador de frequência.

Para wave, a ROM transfere quatro words para `0x04000090..0x0400009F` somente
quando o ponteiro da waveform muda. Depois registra o ponteiro atual no canal.
As leituras são intercaladas às escritas, inclusive nos testes com origem
sobreposta ao espelho de I/O. O controle de volume consulta `0x08A676C4+índice`;
testar os 256 índices de byte não determina a extensão global dessa tabela.

As escritas repetidas de trigger do canal 1 são preservadas. Ao terminar um
canal ativo, Update zera as flags em `channel+0x1D`; um registro inativo é pulado
sem essa limpeza.

## Validação

Passaram **7.717 cenários e 7.925 execuções**, com igualdade entre a ROM,
o C nativo e um modelo Python separado:

- 512 argumentos de Stop, incluindo bits altos fora do byte do canal.
- 2.560 combinações estéreo: todos os 256 valores de right e dez valores de left;
  mais todos os 256 valores de sustain.
- Todos os 256 status em cada canal, os 256 valores do contador e as 768
  combinações de byte de ataque, decay e release.
- 224 limites de envelope e todos os 256 bytes de bias em cada canal.
- 24 casos de origem/cache/tamanho de wave, 256 índices de volume e 256
  combinações de flags, mais 512 casos aleatórios determinísticos.
- 16 casos em que `MusicTrack_Stop` chama o Stop CGB real pelo ponteiro instalado.
- Oito sequências de Initialize → Extend → callbacks reais: **192 atualizações
  e 200 chamadas indiretas**, com início, release, reinício e parada.

Foram cobertas **581 instruções alcançáveis** nos três serviços. As duas
instruções restantes, `0x0810B93E` e `0x0810B9F8`, exigem nas duas seleções
um canal menor ou igual a 2 que não seja 1 nem 2. O laço só gera 1, 2, 3 e 4.
Pools, padding e esses dois desvios continuam incluídos na comparação integral
dos bytes; não há máscara, recorte ou alteração da imagem compilada.

A comparação comportamental verifica RAM observável, buffers, I/O e ordem,
largura e valor das leituras/escritas. Foram observadas **20.112 escritas em I/O**,
incluindo **732 escritas word na região de wave RAM**. Exclui a pilha morta do executor
`0x03007000..0x030077FF`, como nos corpora anteriores. A referência executa
a ROM em Unicorn ARM926; o I/O é um espelho plano. A sequência de setup usa o
modelo controlado de CpuSet já documentado na [inicialização](sound_initialization_native.md).
Não foram validados ciclos ARM7TDMI, efeitos físicos dos dispositivos, áudio
em tempo real ou saída audível.

Passaram **69 testes direcionados**, incluindo 18 próprios de CGB, e os
**23 corpora de áudio** com os fontes finais. Mutações deliberadas verificam
truncamento do argumento, largura de I/O, volume/rounding, contador, máscara,
eco signed, extensão da cópia wave, frequência, trigger, flags e fallback ARM.
Os gates revalidaram todos os **242 alvos C e 22 assembly**.
Há **452 testes descobertos**; a suíte geral não foi reexecutada integralmente.
A última execução completa registrada continua sendo a de 290 testes da etapa
de instrumento.

O Windows bloqueou o primeiro carregamento da DLL de prioridade/tempo com
WinError 4551. Uma única repetição da compilação/execução normal, com os mesmos
fontes e sem alterar políticas do sistema, passou nos 3.525 casos. Os logs
da tentativa inicial e da repetição foram preservados.

Fontes: [C nativo](../port/audio/audio_helpers.c), [API](../port/include/audio_helpers.h),
[Stop GBA](../src/cgb_stop.c), [Volume GBA](../src/cgb_update_volume.c),
[Update GBA](../src/cgb_update.c), [verificador](../tools/verify_cgb.py)
e [testes](../tests/test_cgb_native.py).

```powershell
.\.venv\Scripts\python.exe tools\match.py --target cgb_stop
.\.venv\Scripts\python.exe tools\match.py --target cgb_update_volume
.\.venv\Scripts\python.exe tools\match.py --target cgb_update
.\.venv\Scripts\python.exe tools\verify_cgb.py --cases 512
.\.venv\Scripts\python.exe -m unittest discover -s tests -p '*native.py' -v
```

Evidências: `build/native_cgb_validation/report.json`,
`build/next/cgb_native/tests_target.log`, `build/next/cgb_native/native_jobs.json`,
`build/next/cgb_native/audit_cgb.json` e `build/verification.json`.

O jogo Windows ainda não é jogável. O [mixer PCM](pcm_mixer_native.md) foi
concluído na continuação, com C nativo e 1.064 bytes assembly exatos, chegando a
59 endereços resolvidos. A próxima etapa inclui saída de áudio, temporização,
dispositivos e integração de alto nível. Vídeo, entrada, recursos, saves,
gameplay e validação completa continuam necessários; veja o [estado do port](port_status.md).
