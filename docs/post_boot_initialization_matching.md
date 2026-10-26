# Inicialização da sequência 0x4D

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes são descritivos; não são símbolos
recuperados do código-fonte original.

## Resultado e escopo

`PostBoot_Initialize`, em **`0x080EFAA4`**, reproduz **144/144 bytes**.
Foram reconstruídas também dezoito dependências: **19 funções e 2.252 bytes**,
incluindo literais e padding, sem diferenças. Todos esses alvos usam agbcc
GCC 2.9-arm-000512 com `-O2 -mthumb-interwork`.

| Função | Endereço USA | Instruções | Literais | Padding | Total |
|---|---|---:|---:|---:|---:|
| `PostBoot_Initialize` | `0x080EFAA4` | 118 | 24 | 2 | 144 |
| `PostBoot_OnDestroy` | `0x080EE654` | 132 | 4 | 0 | 136 |
| `PostBoot_Run` | `0x080EE6DC` | 230 | 76 | 2 | 308 |
| `PostBoot_Update` | `0x080EE810` | 188 | 28 | 4 | 220 |
| `PostBoot_Finish` | `0x080EE8EC` | 122 | 40 | 2 | 164 |
| `PostBoot_PrepareSprites` | `0x080EF3B4` | 138 | 8 | 2 | 148 |
| `PostBoot_FreeSprites` | `0x080F054C` | 46 | 0 | 2 | 48 |
| `PostBoot_Begin` | `0x080EFB34` | 78 | 12 | 2 | 92 |
| `PostBoot_EnableBackgrounds` | `0x080EFB90` | 68 | 12 | 0 | 80 |
| `PostBoot_DisableBackgrounds` | `0x080EFBE0` | 68 | 12 | 0 | 80 |
| `PostBoot_Phase3` | `0x080EFC30` | 74 | 12 | 2 | 88 |
| `PostBoot_LoadTiles` | `0x080F0434` | 92 | 20 | 4 | 116 |
| `Music_StartSong` | `0x0810ADB8` | 36 | 8 | 0 | 44 |
| `Vram_AllocateTiles` | `0x08113B80` | 160 | 24 | 0 | 184 |
| `Vram_FreeTiles` | `0x08113C60` | 36 | 12 | 0 | 48 |
| `PostBoot_CreateSkipTask` | `0x080F0898` | 104 | 12 | 0 | 116 |
| `PostBoot_SkipRun` | `0x080EF9BC` | 98 | 16 | 2 | 116 |
| `PostBoot_SkipFade` | `0x080EFA30` | 104 | 8 | 4 | 116 |
| `PostBoot_SkipOnDestroy` | `0x080F090C` | 2 | 0 | 2 | 4 |

O agregado atual tem **224 funções e 33.032 bytes completos iguais à ROM**.
Os **190 testes passaram, sem skips**. A auditoria também confere todo o bloco
contínuo `0x080EE654..0x080F0910`: 96 funções e 8.892 bytes, incluindo o
[encerramento da abertura](post_boot_phase38_matching.md), sem lacunas nem sobreposições.

## Conexão com a inicialização anterior

Depois das quatro telas da [apresentação inicial](boot_presentation_matching.md),
`Sequence_StartAfterBoot` chama `Func_080C863C(0x4D, 0, 1, 0)`.
A entrada `0x4D` da tabela de inicializadores contém `0x080EFAA5`, com o bit
Thumb. O novo corpo C preserva essa ligação.

O inicializador limpa o bit `0x01000000` de `gSystemFlags` e cria uma tarefa
com **492 bytes**, prioridade `0x200`, flags `0x10`, callback `0x080EE6DC`
e destrutor `0x080EE654`. Preenche os 492 bytes com zero via `CpuSet`, salva
os ponteiros do pai, incrementa seu estado e registra a tabela de fundos
em `0x08A4E33C`.

A estrutura parcial está em `include/post_boot.h`. Os campos observados são:

| Offset ARM | Campo |
|---|---|
| `+0x04`, `+0x08`, `+0x0C` | Sequência pai, ponteiro do contador e ponteiro do campo de VRAM |
| `+0x10` | Flags de controle |
| `+0x14` | Contador local de atualizações |
| `+0x18` | Índice de 16 bits na tabela de tempos |
| `+0x1C` | Callback da fase |
| `+0x20..+0x1D0` | Nove registros de sprite de 48 bytes |
| `+0x1D0` | Ponteiro para os registros de fundos |
| `+0x1D8..+0x1E8` | Cinco ponteiros de tarefas filhas, incluindo o skip |

## Vídeo, sprites e música

`PostBoot_Run` configura a área de alocação de sprites para 1.024 tiles,
com base `0x06010000`, e chama o reset do mapa de alocações, já reconstruído.
Escreve `0x1040` no shadow de vídeo e `0x5E00, 0x5C04, 0x5A08` nos controles
dos primeiros três BGs. Zera scroll e blend, limpa os 96 KiB de VRAM e os dois
buffers de paleta e ativa os bits 0 e 1 de `gSystemFlags`.

O callback chama `MusicPlayer_Stop` para o player apontado pelo word ROM `0x08D2BAE4`, cujo valor é
`0x03001E00`, e inicia a música de ID 1. O wrapper `Music_StartSong` usa registros
de oito bytes na tabela `0x08A69068` e de doze bytes em `gMusicPlayerTable`.
Para ID 1, o header é `0x08D0E854` e o índice de player é zero. O serviço
`MusicPlayer_Start`, em `0x0810B4EC`, já tem [matching integral](music_player_start_matching.md).

A preparação dos nove sprites lê configurações de oito bytes em `0x08A4E2F0`:

| Índices | Animação | Variantes | Tiles pedidos por sprite | Paleta |
|---|---:|---|---:|---:|
| 0 | 4 | 16 | 24 | 0 |
| 1 | 4 | 17 | 4 | 0 |
| 2..8 | 177 | 0..6 | 9 | 1 |

Cada sprite recebe VRAM, posição inicial `(-64, -64)`, variante anterior
`0xFF`, velocidade `0x10`, frame zero e ordem `0x400`. O índice 0 recebe
flags `0x400`; o índice 1 recebe ordem `0x440`. A chamada que atualiza a animação,
`0x0810FD70`, já tem [matching integral com seus doze comandos](sprite_animation_matching.md). `PostBoot_FreeSprites` libera os nove endereços
não nulos e zera cada ponteiro liberado.

`Vram_AllocateTiles` arredonda o pedido para blocos de quatro tiles,
percorre o mapa de halfwords em `0x03006A20` e armazena o tamanho no primeiro
elemento do bloco. O endereço devolvido é `base + índice * 128`.
O limite é a capacidade em tiles dividida por quatro; falhas devolvem o mesmo
sentinela global usado pelo código original. `Vram_FreeTiles` ignora esse
sentinela e zera a entrada correspondente ao offset do endereço, em blocos de
128 bytes. As larguras dos contadores e a aritmética original foram preservadas.

## Atualização, fases iniciais e avanço por botão

`PostBoot_Update` incrementa o contador local e `gDbaaGameState.word14`.
Transforma a flag `0x20` em `0x40`; no despacho posterior, limpa `0x40` e `0x10`.
Teclas recém pressionadas na máscara `0xB` criam uma tarefa de skip quando
o bit 2 ainda está limpo. O callback da fase é opcional. O bit `0x40000000`
agenda a conclusão da tarefa; a atualização também limpa o bit `0x0800`
do shadow de vídeo.

`PostBoot_Begin` configura a janela, chama o carregador de fundos com os índices
0, 1 e 2, descomprime os tiles do índice 8 e agenda a primeira espera.
`PostBoot_LoadTiles` usa registros de doze bytes; um ID negativo seleciona
o fundo padrão, 98. O índice 8 descomprime para `0x06012000`; os outros usam
o charblock selecionado no controle do BG.

Os três limiares confirmados da tabela `0x08A4E438` são **51, 59 e 64**.
As fases reconstruídas habilitam os BGs das entradas 0 e 1, depois os desabilitam,
e por fim habilitam os BGs das entradas 0 e 2 e solicitam o fundo de índice 3.
A fase seguinte é `0x080EFC88`, agora concluída com 80 bytes na
[continuação](post_boot_loader_matching.md). Não foi estabelecido o tamanho
completo da tabela de tempos nem da tabela de fundos apenas por esses acessos.

O skip cria uma tarefa de 16 bytes, prioridade **`0x1000`**, flags zero e duração
20. Ela espera o bit `0x10` do pai ficar limpo, configura blend e janelas,
ativa o bit 1 do pai e passa para o fade. O fade calcula
`(elapsed << 4) / duration`; ao atingir a duração, fixa o brilho em 16, ativa
`0x40000000` no pai, zera `parent->skipTask` e destrói a si próprio.
O destrutor do skip é vazio.

`PostBoot_Finish` limpa o controle da janela e seus seis shadows, incrementa
o contador global, libera os sprites e restaura a alocação para 512 tiles
com base `0x06014000`. Após resetar o mapa de VRAM, decrementa o estado do pai
e destrói a tarefa principal. O destrutor principal ativa `0x01000000`
e destrói cada uma das cinco tarefas filhas que estiver registrada.

## Como foi validado e o que falta

Os fontes são compilados e linkados individualmente nos endereços originais.
A seção executável inteira é comparada; nenhuma diferença é mascarada.
Não há templates de instruções ASM, arrays de opcodes, recorte de binário,
alteração do compilador ou edição do assembly emitido.

Cinco fontes novos usam **seis templates vazios** ao todo: duas restrições no
inicializador, uma na conclusão, uma na preparação dos sprites, uma no alocador
de VRAM e uma no criador do skip. Elas conservam endereços e duração de valores;
algumas variáveis têm vínculos explícitos a registradores. `Music_StartSong`
também vincula a base da tabela a `r2`, sem template ASM. Os outros treze fontes
não contêm `__asm__`. As extensões GNU C estão declaradas nos fontes e no manifesto.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target post_boot_initialize
.\.venv\Scripts\python.exe tools\match.py --target post_boot_run
.\.venv\Scripts\python.exe tools\match.py --target post_boot_skip_fade
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Relatórios em `build/matching/<id>/report.json`, `build/matching/summary.json`
e `build/verification.json`. A auditoria conserva a análise de fluxo em
`build/next/post_boot_flow.json` e leituras das tabelas em
`build/next/post_boot_tables.json`. Os novos testes negativos alteram tamanho
da tarefa, preenchimento, vídeo, destruição, controles, sprites, arredondamento
da VRAM, stride do player, tempos, callbacks e conclusão do skip.

A continuação [carregador e fase seguinte](post_boot_loader_matching.md) concluiu
**`0x080EEDB4`**, com 564 bytes, e **`0x080EFC88`**, com 80 bytes. A referência
algorítmica permanece em `reference/post_boot_load_background.c`; o fonte com
matching está em `src/post_boot_load_background.c`.
A [continuação de fases, fade e transferência de tiles](post_boot_phases_matching.md)
concluiu `0x080EFCD8` e vinte dependências, com 1.456 bytes iguais.
A etapa do [callback seguinte e fundo especial](post_boot_phase21_matching.md)
concluiu `0x080F0040`, `0x080EF230` e outras quatorze funções, com 1.564 bytes.
A etapa do [callback `0x080EEA7C`, sprites e scroll](post_boot_phase30_matching.md)
concluiu mais dezesseis funções e 1.724 bytes.
O [callback `0x080F02EC` e o encerramento](post_boot_phase38_matching.md) também têm matching.
O [desenho de sprites, alocador OAM, serviço de paleta e memset](graphics_draw_sprite_matching.md) também têm matching.
A [animação `0x0810FD70`, seus doze comandos e a paleta OBJ](sprite_animation_matching.md) também têm matching.
O [início do player e cinco serviços de áudio](music_player_start_matching.md) também têm matching.
Permanecem externos o processador de músicas `0x0810A724`, inicialização de áudio e outros wrappers/helpers.
O build completo da ROM, a validação por frame em emulador e o port PC continuam pendentes.
