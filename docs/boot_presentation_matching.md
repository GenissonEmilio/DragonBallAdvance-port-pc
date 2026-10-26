# Callback filho e apresentação inicial

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes de funções e campos são descritivos,
atribuídos neste projeto a partir dos acessos observados.

## Resultado

`BootSequence_Run`, em **`0x080F2FD0`**, foi reconstruída em C e reproduz
**252/252 bytes**. Outras doze funções completam o fluxo da apresentação inicial:
**13 funções e 1.428 bytes**, sem diferenças. Cada comparação inclui a seção
linkada inteira, literais e alinhamento. Todos esses alvos usam agbcc
GCC 2.9-arm-000512, com `-O2 -mthumb-interwork`.

| Função | Endereço | Instruções | Literais | Padding | Total |
|---|---|---:|---:|---:|---:|
| `BootSequence_Run` | `0x080F2FD0` | 198 | 52 | 2 | 252 |
| `BootSequence_Finish` | `0x080F30CC` | 110 | 28 | 2 | 140 |
| `BootSequence_BeginFadeOut` | `0x080F3158` | 70 | 8 | 2 | 80 |
| `BootSequence_Advance` | `0x080F31A8` | 112 | 8 | 0 | 120 |
| `BootSequence_LoadScreen` | `0x080F3220` | 284 | 40 | 4 | 328 |
| `BootSequence_Update` | `0x080F33F4` | 94 | 16 | 2 | 112 |
| `BootSequence_StartScreen` | `0x080F3464` | 58 | 8 | 2 | 68 |
| `BootSequence_FadeIn` | `0x080F34A8` | 74 | 4 | 2 | 80 |
| `BootSequence_BeginHold` | `0x080F34F8` | 26 | 4 | 2 | 32 |
| `BootSequence_Hold` | `0x080F3518` | 48 | 0 | 0 | 48 |
| `BootSequence_FadeOut` | `0x080F3548` | 48 | 4 | 0 | 52 |
| `BootSequence_BeginPause` | `0x080F357C` | 44 | 4 | 0 | 48 |
| `BootSequence_ClearScreen` | `0x080F35AC` | 56 | 12 | 0 | 68 |

Os fontes estão em `src/boot_sequence_*.c`; as estruturas parciais recuperadas
estão em `include/sequences.h`. O inicializador `0x080F3368` e o destrutor
`0x080F33F0` já tinham matching na [etapa anterior](sequences_initialization_matching.md)
e continuam passando com o cabeçalho ampliado. Juntos, os quinze corpos cobrem
o intervalo contínuo **`0x080F2FD0..0x080F35F0`**, totalizando **1.568 bytes**
sem lacunas ou sobreposições; a auditoria também verifica essa união contra a ROM.

## Preparação, fases e conclusão

O inicializador cria uma tarefa de 44 bytes com o callback `BootSequence_Run`.
O callback resolve seus dados em EWRAM ou IWRAM, escreve `0x140` no shadow do
controle de vídeo e `0x1F00` no controle do BG0. Zera os quatro pares de scroll,
configura os shadows de blend para `0xFF, 0, 16`, preenche os 96 KiB da VRAM
e os dois buffers de paleta de 512 bytes com zero por `Bios_CpuSet`.
Depois ativa os bits 0 e 1 de `gSystemFlags`, chama o serviço já reconstruído
`0x0810AEEC` e troca o callback da tarefa por `BootSequence_Update`.
A fase interna passa a ser `BootSequence_StartScreen`.

A apresentação usa dois níveis de callbacks: o da tarefa em `task+8` e a fase
por tela em `data+0x1C`. Os campos confirmados do bloco de 44 bytes incluem:

| Offset | Campo ARM recuperado |
|---|---|
| `+0x04` | Ponteiro para a sequência pai |
| `+0x08` | Ponteiro para o contador do pai |
| `+0x0C` | Ponteiro para o campo de VRAM do pai |
| `+0x10` | Flags de 32 bits; bit 0 acelera, bit 31 termina |
| `+0x18` | Contador signed de 16 bits |
| `+0x1C` | Callback da fase, recebendo o bloco como argumento |
| `+0x20` | Duração unsigned de 16 bits |
| `+0x24` | Ponteiro para a tabela de telas |
| `+0x28` | Índice unsigned de 8 bits |

Cada tela passa por carregar, clarear, esperar, escurecer e pausar.
O fade de entrada escreve `16 - ((timer << 4) / duration)` no shadow de brilho;
o de saída escreve `((timer << 4) / duration)`. As divisões C geram chamadas ao
helper externo `__divsi3`, em `0x08116A58`.

`BootSequence_Update` testa a máscara `0xB` das teclas recém pressionadas apenas
quando o índice da tela é diferente de zero. Esse pedido ativa o bit 0; pode
encerrar a espera e reduz pela metade o fade de saída e a pausa. A transição
para a próxima tela limpa esse bit. As duas verificações independentes de
`BootSequence_Hold` foram preservadas: uma chamada a `BeginFadeOut` pode alterar
o contador e a duração antes da segunda comparação.

Ao incrementar o índice além de 3, `BootSequence_Advance` ativa o bit 31 e zera
a fase. No mesmo despacho, `BootSequence_Update` detecta as flags negativas e
agenda `BootSequence_Finish`. A conclusão limpa o blend e as paletas, solicita
o commit das paletas, decrementa o estado do pai e destrói a tarefa filha.
O pai pode então seguir para `Sequence_Finish` e `Sequence_StartAfterBoot`.

## Tabela de telas e carregamento gráfico

A tabela em `0x08A63B2C` contém entradas de 16 bytes. Os quatro índices usados
pelo código apontam para recursos na tabela `0x0882323C`. Os tempos abaixo são
parâmetros do script; as mudanças de callback também consomem despachos.

| Índice | ID do fundo | Tiles de largura × altura | Fade entrada | Espera | Fade saída | Pausa |
|---:|---:|---|---:|---:|---:|---:|
| 0 | 118 | 30 × 20 | 10 | 75 | 10 | 20 |
| 1 | 120 | 30 × 20 | 15 | 50 | 15 | 0 |
| 2 | 121 | 30 × 20 | 15 | 50 | 15 | 0 |
| 3 | 119 | 22 × 11 | 15 | 50 | 15 | 0 |

Todas usam BG0 e a primeira posição de paleta. Os offsets de scroll da última
são `0xFFE0, 0xFFD8`, equivalentes a -32 e -40 se interpretados como signed.
Não foram atribuídos nomes visuais a essas imagens apenas pelos endereços.

`BootSequence_ClearScreen` preenche com zero os 2 KiB do screenblock selecionado
pelos bits 8..12 do controle do BG. `BootSequence_LoadScreen` determina também
o charblock pelos bits 2..3, chama o wrapper BIOS de descompressão LZ77 para VRAM
e copia cada linha do mapa com `CpuSet`. O destino tem stride de **32 halfwords**;
a largura do recurso determina o número de halfwords copiados por linha.

Quando `gSystemFlags & 0x10000` está ativo, a paleta passa pelo serviço ainda
externo `0x08114668`. No outro caminho, o DMA3 copia para `gBgPaletteBuffer`,
com offset de 32 bytes por posição de paleta. Ambos os caminhos zeram a primeira
cor do buffer, solicitam atualização e aplicam o scroll da entrada do script.
As quatro paletas observadas têm 16 halfwords. Os quatro blocos de tiles
começam com o marcador LZ77 `0x10`.

## Prova e limites

Onze dos treze novos fontes não contêm inline assembly. `ClearScreen` usa
**uma restrição vazia** para manter o endereço da célula zero antes da escrita.
`LoadScreen` usa **duas**: um clobber de `r9` antes da leitura do ID conserva a
alocação do ponteiro do script em `r8`; uma restrição de entrada/saída conserva
a releitura do ponteiro do recurso após a escrita do destino do DMA. Todas têm
template vazio, não emitem instruções e estão declaradas no manifesto e nos
relatórios. A declaração do clobber afeta a alocação do compilador; não realiza
uma escrita em `r9` em execução.

Não há instruções em templates de assembly, arrays de opcodes, máscaras de
diferenças, recorte de binário ou edição da saída do compilador.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target boot_sequence_run
.\.venv\Scripts\python.exe tools\match.py --target boot_sequence_load_screen
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O conjunto atual contém **224 funções e 33.032 bytes completos iguais à ROM**.
Os **190 testes passaram, sem skips**. Os novos controles negativos alteram
o modo de vídeo, o tamanho dos preenchimentos, o estado do pai, a máscara de
entrada, a condição de conclusão, o limite de telas, o stride gráfico,
o caminho da paleta, os callbacks e o cálculo dos tempos e fades.

Relatórios: `build/matching/<id>/report.json`, `build/matching/summary.json`
e `build/verification.json`. A auditoria local também conserva o mapa de fluxo
em `build/next/boot_flow.json` e a leitura das tabelas em
`build/next/boot_tables.json`; esses arquivos gerados são ignorados pelo Git.

A entrada `0x4D` de `gSequenceInitializers` contém o ponteiro Thumb
`0x080EFAA5`. Esse [inicializador e dezoito dependências](post_boot_initialization_matching.md)
agora têm matching. O [serviço de paleta `0x08114668`](graphics_draw_sprite_matching.md) também tem matching. Também permanecem externos os wrappers
BIOS e helpers do compilador. O matching atual é por função; faltam o build
completo da ROM, a validação por frame em emulador e a camada nativa de PC.
