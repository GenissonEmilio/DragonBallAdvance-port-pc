# Configuração de frequência no port nativo

`Sound_SetFrequency` (`0x0810B22C`) e sua dependência `Sound_VSyncOn` (`0x0810B438`)
estão integradas em **C Windows x64**, sem delegar essas rotinas ao ARM.
O C do build GBA continua reproduzindo **164/164 e 60/60 bytes**, respectivamente,
na ROM USA BDVE rev0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

Essas funções já pertenciam ao conjunto com matching. Seus 224 bytes **não são
somados novamente**: o total permanece em **242 funções C/GNU C, 33.856 bytes,
mais 23 alvos assembly, 2.720 bytes** — **265 alvos e 36.576 bytes exatos**.
O avanço desta etapa são dois bindings novos: **59 endereços nativos no conjunto atual** e
**36/36 slots da tabela ligados**, após as substituições de `Sound_Extend`.
Isso não encerra as dependências transitivas do áudio ou a integração do jogo.

## Comportamento reconstruído

`Dbaa_SoundSetFrequency` lê o ponteiro de som em `0x03007FF0`, extrai
`(mode >> 16) & 15` e consulta a tabela de halfwords em `0x08A675D4`, no índice
`index - 1`. Atualiza:

| Campo de SoundInfo | Largura | Cálculo |
|---|---:|---|
| `+0x08` | 1 byte | Índice de frequência |
| `+0x10` | 4 bytes | Amostras por frame, lidas da ROM |
| `+0x0B` | 1 byte | `1584 / samples`, truncado ao byte |
| `+0x14` | 4 bytes | Divisão signed de `wrap32(597275 * samples + 5000)` por 10000 |
| `+0x18` | 4 bytes | Shift aritmético de `wrap32(div_signed(0x01000000, rate) + 1)` por um bit |

A multiplicação conserva o overflow de 32 bits. O C do host usa intermediários
largos para expressar os valores signed sem overflow indefinido. A divisão
trunca em direção a zero; o auxiliar original retorna zero para divisor zero.
O corpus usa os halfwords da ROM intacta, sem substituir a tabela para forçar esse último caso.

Os modos usuais 1..12 usam `96,132,176,224,264,304,352,448,528,608,672,704`
amostras por frame. A rotina original não faz clamp: 0 e 13..15 leem halfwords
adjacentes. Esses quatro índices também foram comparados para preservar o
comportamento observado, incluindo os cálculos signed do índice 0.
Os 28 bits restantes do argumento não alteram o índice.

Depois dos cálculos, emite escritas de **16 bits**, nesta ordem:

1. Desabilita timer 0 em `0x04000102`, gravando zero.
2. Grava `-(280896 / samples)` em `0x04000100`, truncado ao halfword.
3. Executa `Sound_VSyncOn`.
4. Espera sair de VCOUNT 159; depois espera alcançar VCOUNT 159 novamente.
5. Grava `0x80` em `0x04000102`.

`Dbaa_SoundVSyncOn` relê o ponteiro global e o lock. Se o lock for `0x68736D53`,
retorna sem escrever. Caso contrário, escreve `0xB600` nos controles DMA
`0x040000C6` e `0x040000D2`, faz a leitura volátil de `sound+4`, zera esse byte
e armazena `lock - 10`, com wrap de 32 bits.

## Contrato do host e limites da validação

Os endereços continuam sendo valores GBA de 32 bits. As operações passam pelos
callbacks `read` e `write`, preservando endereço, largura, ordem e quantidade.
Durante polling, o relógio do host precisa fazer **VCOUNT progredir**. Um espelho
de memória permanentemente parado não permite concluir as esperas originais.
Esse contrato está documentado em [music_player.h](../port/include/music_player.h).

O verificador fornece sequências finitas de VCOUNT, incluindo chamadas iniciadas
na linha 159, saída e reentrada, várias leituras repetidas e passagem por outras
linhas. Não troca as esperas por uma conclusão imediata. Um limite do harness
produz diagnóstico e encerra o processo de teste se um candidato consumir leituras
extras ou ficar preso; esse limite não foi inserido no C de produção.

O I/O é um **espelho plano com rastreamento de acessos**. O teste confere a
operação emitida, mas não implementa DMA, timer, FIFO ou geração de som.
Temporização real, ciclos ARM7TDMI, efeitos dos dispositivos, saída audível e
boot integral continuam sem validação.

## Evidências desta etapa

Passaram **1.718 cenários**, com **1.750 execuções** e cobertura das **81
instruções** das duas funções: 58 de frequência e 23 de VSync-on.

- Os 16 índices, seis estados de lock e três sequências de relógio: 288 casos.
- Os 28 bits ignorados, seis locais de SoundInfo e sete percursos de VCOUNT.
- 32 casos em que o ponteiro global muda antes da entrada em VSync-on.
- 32 sequências de duas configurações consecutivas, carregando o estado da primeira.
- Todos os bytes de `sound+4`, com e sem escritas de VSync-on; limites e wrap do lock.
- Seis controles dirigidos e 512 casos aleatórios determinísticos.

RAM do jogo, espelho de I/O e cada leitura/escrita observada coincidiram com a
ROM e com uma transição de estado independente em Python. Foram observadas
**6.426 escritas em I/O**. O SP e os registradores preservados do original
também são conferidos. Não há fallback ARM nos dois serviços nativos.

Passaram os **15 testes próprios**, incluindo mutações dos fontes GBA e do
C nativo. Os **20 corpora de áudio** foram reexecutados com os fontes e headers
finais, assim como os gates completos dos **242 alvos C e 22 assembly**.
A suíte geral contém **398 testes** e não foi reexecutada integralmente nesta
etapa; a última execução completa continua sendo a de 290 testes da etapa de instrumento.

Fontes: [C nativo](../port/audio/audio_helpers.c),
[API](../port/include/audio_helpers.h),
[C GBA de frequência](../src/sound_set_frequency.c),
[C GBA de VSync-on](../src/sound_vsync_on.c),
[verificador](../tools/verify_sound_frequency.py) e
[testes](../tests/test_sound_frequency_native.py).

```powershell
.\.venv\Scripts\python.exe tools\match.py --target sound_set_frequency
.\.venv\Scripts\python.exe tools\match.py --target sound_vsync_on
.\.venv\Scripts\python.exe tools\verify_sound_frequency.py --cases 512
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sound_frequency_native.py -v
```

Relatórios: `build/native_sound_frequency_validation/report.json`,
`build/matching/sound_set_frequency/report.json`,
`build/matching/sound_vsync_on/report.json`,
`build/next/sound_frequency/tests_target.log` e `build/verification.json`.

O [modo e VSync-off](sound_mode_native.md) foram integrados na continuação,
com 152 e 124 bytes GBA revalidados. A [inicialização e extensão](sound_initialization_native.md) foram ligadas depois.
A continuação de [CGB](cgb_native.md) ligou Stop, Update e Volume.
O [mixer PCM](pcm_mixer_native.md) foi integrado depois; a próxima fronteira inclui
saída de áudio, dispositivos, backend e gameplay.
Veja o [estado completo do port](port_status.md).
