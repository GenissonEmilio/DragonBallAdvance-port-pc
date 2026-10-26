# Inicialização de alto nível e wrapper de áudio no PC

Verificado em 20/10/2026 sobre a ROM USA `BDVE`, revisão 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

`0x0810AD34` e `0x0810ADAC` agora têm implementações C nativas:
`Dbaa_AudioInitialize` e `Dbaa_AudioMain`. A dependência
`MusicPlayer_Open` (`0x0810B474`) também foi ligada em C.
O despachante resolve **62 endereços**, incluindo esses três novos bindings,
e todos os **36 slots** da tabela de comandos.

Os três alvos GBA já pertenciam ao conjunto C/GNU C com matching e foram
recompilados e comparados integralmente:

| Função | Endereço | Instruções | Literais | Padding | Total |
|---|---|---:|---:|---:|---:|
| Inicialização de alto nível | `0x0810AD34` | 84 | 36 | 0 | 120 |
| Wrapper do mixer | `0x0810ADAC` | 10 | 0 | 2 | 12 |
| `MusicPlayer_Open` | `0x0810B474` | 106 | 12 | 2 | 120 |
| **Total** | | **200** | **48** | **4** | **252** |

São **93 instruções Thumb** nos três corpos. A comparação inclui os literais
e o padding, sem recortes, máscaras, opcodes inseridos ou edição do assembly
emitido pelo compilador. `MusicPlayer_Open` mantém uma restrição vazia de GNU C
para alocação de registrador; ela não emite instruções. O compilador é o agbcc
GCC 2.9-arm-000512, revisão `da598c1d918402c42c0c0d7128ba14567f3175e9`,
com `-O2 -mthumb-interwork`, sem alterações locais.

Esta etapa acrescenta **zero bytes novos** ao matching. O agregado permanece
**242 alvos C/GNU C, 33.856 bytes, e 23 assembly, 2.720 bytes**:
**265 alvos e 36.576 bytes exatos**.

## Sequência reconstruída

1. Copia **1.024 bytes**, em 256 words, de `0x0810A108` para `0x030008B0`,
   equivalentes ao `CpuSet` com controle `0x04000100`.
2. Executa `Sound_Initialize(0x03000CC0)` e `Sound_Extend(0x03001D00)`.
3. Aplica o modo `0x0095FC00`: 12 canais PCM, volume mestre 15 e frequência
   de índice 5, com **264 amostras por frame**. A configuração intermediária
   de índice 4, com 224 amostras, também é preservada.
4. Percorre as quatro entradas de `0x08A69038`, abre cada player, lê sua
   prioridade como halfword e grava o byte inferior em `player+11`.
5. Grava o ponteiro de memória compartilhada `0x03001EC0` em `player+24`.

A cópia do bloco de RAM é preservada como parte do estado observável. O PC
executa o [mixer em C](pcm_mixer_native.md); os bytes copiados não são executados
pelo lado nativo.

| Player | Trilhas | Quantidade |
|---|---|---:|
| `0x03001E00` | `0x03000000` | 16 |
| `0x03001E40` | `0x03000500` | 4 |
| `0x03001E80` | `0x03000640` | 5 |
| `0x03001ED0` | `0x030007D0` | 2 |
| **Total** | | **27** |

`MusicPlayer_Open` trunca a contagem recebida para oito bits, retorna imediatamente
se for zero e limita valores maiores a 16. Exige o lock original, chama o callback
de limpeza instalado em RAM, configura o player e zera somente o status de cada
trilha, com stride de 80 bytes. Insere o novo player no início da cadeia e
restaura os locks na ordem original.

Após a inicialização, a ordem dos callbacks é:
`0x03001ED0 → 0x03001E80 → 0x03001E40 → 0x03001E00`.
Os players começam pausados. O wrapper `0x0810ADAC` chama o mixer, que percorre
essa cadeia, chama o serviço CGB instalado e gera os buffers PCM.

## Validação

Passaram **1.288 cenários e 1.392 execuções**, com igualdade de RAM observável,
espelho de I/O e acessos ordenados de dados entre ROM e C nativo.
Um modelo Python separado também coincidiu nas **1.296 execuções** de
inicialização e abertura de player.

| Grupo | Cenários |
|---|---:|
| Controles iniciais | 7 |
| Combinações de controles DMA | 36 |
| Todos os bytes de bias | 256 |
| Locks anteriores à inicialização | 16 |
| Pares de sequências VCOUNT | 49 |
| Todos os bytes de contagem, com e sem cadeia | 512 |
| Contagens de 32 bits | 16 |
| Contagem versus lock do player | 80 |
| Posicionamentos das estruturas | 36 |
| Sobreposições controladas | 12 |
| Callbacks de limpeza | 4 |
| Inicialização, frames e reinicialização | 8 |
| Aleatórios determinísticos | 256 |

As oito sequências executam **96 atualizações pelo wrapper** e depois repetem a
inicialização. Os dois primeiros frames mantêm os players pausados, como saem
da rotina original. Em seguida, uma fixture controlada ativa fluxos WAIT/FINE
nos quatro players e um canal PCM, preservando a cadeia e a frequência reais
instaladas pela inicialização. Isso exercita a integração sem representar a
reprodução de uma música completa do jogo.

As **93 instruções** dos novos bindings foram cobertas. Houve **502 verificações**
do estado instalado, incluindo a cópia integral, os quatro players, as 27 trilhas,
os callbacks e os 36 comandos. Cada um dos quatro modos CpuSet observados foi
exercitado 502 vezes. O modelo de referência explicita cópia/fill32; não usa
imagem BIOS nem altera a ROM.

Passaram **108 testes direcionados**, incluindo 21 novos, e os **25 corpora de
áudio** com os fontes finais. As mutações deliberadas verificam extensão e origem
da cópia, modo, quantidade de players, largura de prioridade, ponteiro de memória,
truncamento/clamp, lock, limpeza, stride, cadeia e delegação indevida ao ARM.
Os gates revalidaram os **242 alvos C e 23 assembly**. Há **491 testes descobertos**;
a suíte geral não foi reexecutada integralmente. A última execução completa
registrada continua sendo a de 290 testes da etapa de instrumento.

Unicorn ARM926 fornece a referência funcional. I/O é um espelho plano com VCOUNT
roteirizado. Como nos corpora anteriores, a pilha morta
`0x03007000..0x030077FF` é excluída da comparação entre arquiteturas. A execução
do wrapper usa a cópia real do código GBA na RAM; suas leituras de literais
não entram no trace de dados. Não se validam ciclos ARM7TDMI, efeitos de DMA/FIFO,
tempo real ou saída audível.

Fontes: [C nativo](../port/audio/audio_helpers.c), [API](../port/include/audio_helpers.h),
[inicialização GBA](../src/audio_initialize.c), [wrapper GBA](../src/audio_main.c),
[Open GBA](../src/music_player_open.c), [verificador](../tools/verify_audio_startup.py)
e [testes](../tests/test_audio_startup_native.py).

```powershell
.\.venv\Scripts\python.exe tools\match.py --target audio_initialize
.\.venv\Scripts\python.exe tools\match.py --target audio_main
.\.venv\Scripts\python.exe tools\match.py --target music_player_open
.\.venv\Scripts\python.exe tools\verify_audio_startup.py --cases 256
.\.venv\Scripts\python.exe -m unittest discover -s tests -p '*native.py' -v
```

Evidências: `build/native_audio_startup_validation/report.json`,
`build/next/audio_startup_native/tests_target.log`,
`build/next/audio_startup_native/native_jobs.json`,
`build/next/audio_startup_native/audit_startup.json` e `build/verification.json`.

## O que falta no port

As [quatro APIs de músicas](song_playback_native.md) já têm bindings C nativos,
e a [saída Windows](windows_audio_output.md) fornece WASAPI, fila e temporização.
A ligação ao caminho completo do jogo, PSG e comportamento geral de
IRQ/DMA/FIFO/timers permanecem pendentes.
O jogo Windows ainda não é jogável. Vídeo, entrada, recursos, saves,
gameplay e comparação do jogo completo continuam pendentes; veja o
[estado do port](port_status.md).
