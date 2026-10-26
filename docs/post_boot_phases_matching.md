# Continuação de 0x080EFCD8, fade e transferência de tiles

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes são descritivos, atribuídos neste projeto.

## Resultado

Foram acrescentadas **21 funções e 1.456 bytes completos iguais à ROM**:
1.248 bytes de instruções, 184 de literais e 24 de alinhamento. O agregado
atual tem **224 funções, 33.032 bytes iguais e 190 testes aprovados, sem skips**.

| Função | Endereço USA | Bytes completos |
|---|---|---:|
| `PostBoot_Phase5` | `0x080EFCD8` | 24 |
| `PostBoot_Phase6` | `0x080EFCF0` | 96 |
| `PostBoot_Phase7` | `0x080EFD50` | 96 |
| `PostBoot_Phase8` | `0x080EFDB0` | 32 |
| `PostBoot_Phase9` | `0x080EFDD0` | 24 |
| `PostBoot_Phase10` | `0x080EFDE8` | 72 |
| `PostBoot_Phase11` | `0x080EFE30` | 72 |
| `PostBoot_Phase12` | `0x080EFE78` | 24 |
| `PostBoot_Phase13` | `0x080EFE90` | 72 |
| `PostBoot_Phase14` | `0x080EFED8` | 72 |
| `PostBoot_Phase15` | `0x080EFF20` | 64 |
| `PostBoot_Phase16` | `0x080EFF60` | 24 |
| `PostBoot_Phase17` | `0x080EFF78` | 96 |
| `PostBoot_Phase18` | `0x080EFFD8` | 36 |
| `PostBoot_Phase19` | `0x080EFFFC` | 68 |
| `PostBoot_CopyTileChunk` | `0x080EE990` | 108 |
| `PostBoot_ClearBackgroundMap` | `0x080F04A8` | 56 |
| `PostBoot_StartFade` | `0x080EE9FC` | 128 |
| `PostBoot_CreateFade` | `0x080EF448` | 168 |
| `PostBoot_FadeRun` | `0x080EF4F0` | 120 |
| `PostBoot_FadeOnDestroy` | `0x080F057C` | 4 |

Todos usam agbcc GCC 2.9-arm-000512, **`-O2 -mthumb-interwork`**, sem alterar
o compilador ou o assembly emitido. Três fontes usam uma restrição vazia cada:
`PostBoot_ClearBackgroundMap` e `PostBoot_Phase15` conservam o endereço do
zero temporário antes da escrita; `PostBoot_Phase18` conserva os dois testes
de flags, impedindo que o compilador combine suas máscaras. **Os templates
são vazios e não emitem instruções.** As outras dezoito funções não usam asm.
Não há arrays de opcodes, funções naked, recorte do candidato ou máscaras.

## Roteiro de fundos

`PostBoot_Phase5`, a função solicitada, carrega a entrada **4** da tabela
`0x08A4E33C` e registra o ponteiro Thumb `0x080EFCF1`. Essa entrada usa BG2
e recurso 68. A fase não incrementa o passo nem aguarda um novo tempo.

As fases 6 e 7 esperam `elapsed >= timeline[step]`, incrementam `step` e
respectivamente ligam e desligam os BGs das entradas **0, 3 e 4**. Na tabela
USA, correspondem a BG0, BG1 e BG2. A fase 8 limpa o mapa do BG da entrada 0:
`CpuSet` preenche **2.048 halfwords, 4 KiB**, a partir do screenblock indicado
pelos bits 8..12 de seu controle. A fase 9 carrega a entrada 5.

As fases 10 e 11 ligam e desligam o BG da entrada 5. A fase 12 carrega a
entrada 6; as fases 13 e 14 ligam e desligam seu BG. A fase 15 limpa o bit
`0x2000` do controle de vídeo e zera seis halfwords do shadow de janelas.
A fase 16 carrega a entrada 7. Os recursos dessas entradas são, em ordem,
**28, 29 e 25**, todos em BG0 nesta ROM.

A tabela de tempos contém os seguintes quatorze valores efetivamente usados
pelo caminho reconstruído, desde o passo inicial zero:

```text
51, 59, 64, 72, 76, 84, 88, 92, 93, 97, 100, 110, 125, 137
```

São contagens absolutas de `data->elapsed`, incrementado por `PostBoot_Update`.
Isso não estabelece a extensão completa da tabela. As fases 6/7 usam 76/84,
10/11 usam 88/92 e 13/14 usam 93/97. As fases que apenas carregam recursos
ou trocam o callback ocupam suas próprias atualizações da tarefa.

## Fade da abertura

Na fase 17, o bit 0 de `flags` bloqueia o avanço durante o skip. Fora desse
caminho, ao atingir o tempo do passo, a função incrementa `step`, liga o BG
da entrada 7 e solicita `PostBoot_StartFade(data, 0)`. Só agenda a fase 18
quando esse serviço retorna sucesso. A fase 18 aguarda os bits `0x10` e 1
ficarem livres. A fase 19 aguarda o próximo tempo e chama o fade na direção 1;
em caso de sucesso zera o contador de blocos e agenda `PostBoot_CopyTileChunk`.

O campo do pai em **`+0x1D4`** foi identificado como ponteiro para os **dados
do fade**, não como ponteiro da tarefa. `PostBoot_StartFade` retorna zero
quando esse campo está ocupado. No caminho livre, zera uma configuração de
20 bytes por meio de `0x08118508`, preenche controle `0xFF`, alpha zero e
duração signed de 16 bits com `timeline[step] - elapsed`, e incrementa `step`.
Direção zero usa coeficiente **16 → 0**; direção diferente de zero usa **0 → 16**.

`PostBoot_CreateFade` cria uma tarefa de **20 bytes**, prioridade **`0x180`**,
flags zero. Copia a configuração por `CpuSet`, zera o contador local e calcula:

```c
increment = ((target - start) << 8) / duration;
current = start << 8;
```

A divisão usa o helper signed original. Esses deslocamentos e conversões
seguem a semântica do compilador ARM usado no matching; ainda precisam de
tratamento explícito ao adaptar o código para um compilador moderno do port.
O serviço salva o pai, ocupa seu campo de fade, ativa `flags & 0x10` e
inicializa os três halfwords de `gBlendShadow`.

`PostBoot_FadeRun` soma o incremento ao acumulador signed de 16 bits, escreve
`current >> 8` no coeficiente do shadow e incrementa o contador signed local.
Quando `elapsed >= duration`, força o coeficiente final, ativa **`0x20`** no
pai, libera seu campo de fade e destrói a tarefa. `PostBoot_Update`, já
reconstruída, processa a conclusão `0x20 → 0x40 → limpeza de 0x10`.
O destrutor do fade é vazio, com dois bytes de retorno e dois de alinhamento.

## Cópia de tiles em blocos

O campo do pai em **`+0x1A`** é o contador signed de 16 bits usado pela cópia.
A rotina considera o charblock do BG indicado pela entrada **8** do roteiro.
Em cada atualização com o bit 0 livre, copia **1.024 words, 4 KiB** por `CpuSet`:

```text
origem  = 0x06012000 + tileChunk * 0x1000
destino = 0x06000000 + charBase * 0x4000 + tileChunk * 0x1000
```

Após os blocos **0 a 5**, zera o contador e registra **`0x080F0041`**, para
o corpo `0x080F0040`, agora reconstruído na
[etapa seguinte](post_boot_phase21_matching.md). São 24 KiB em seis atualizações que
passam pela guarda. Essa rotina só testa o bit de skip; não espera o segundo
fade terminar para começar a copiar. O carregamento prévio da área temporária
em `0x06012000` é feito por `PostBoot_LoadTiles(8)`, já reconstruída.

## Validação e continuação

```powershell
.\.venv\Scripts\python.exe tools\match.py --target post_boot_phase5
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O build compara cada `.text` linkada por inteiro, incluindo literais e
padding, sem relocations restantes. Os testes também recompilam todos os
alvos e rejeitam alterações de recursos, callbacks, tempos, flags, duração
do fade, precisão do incremento e quantidade das transferências.

As evidências locais estão em `build/matching/summary.json`, nos relatórios
individuais e em `build/verification.json`. `build/next/phase5_flow.json`
classifica os 1.456 bytes; `phase5_tables.json` registra as leituras das tabelas.
A auditoria atual verifica todo o bloco contínuo, incluindo as etapas anteriores e o encerramento:

| Início | Fim exclusivo | Bytes | Funções |
|---|---|---:|---:|
| `0x080EE654` | `0x080F0910` | 8.892 | 96 |

A [etapa seguinte](post_boot_phase21_matching.md) concluiu `0x080F0040`,
`0x080EF230` e outras quatorze funções, com 1.564 bytes iguais.
A etapa de [sprites e scroll](post_boot_phase30_matching.md) concluiu
`0x080EEA7C` e quinze dependências, com 1.724 bytes iguais.
O [callback `0x080F02EC` e o encerramento](post_boot_phase38_matching.md) também têm matching.
O [desenho de sprites, alocador OAM, serviço de paleta e memset](graphics_draw_sprite_matching.md) também têm matching.
A [animação `0x0810FD70`, seus doze comandos e a paleta OBJ](sprite_animation_matching.md) também têm matching.
O [início do player e cinco serviços de áudio](music_player_start_matching.md) também têm matching.
Permanecem externos o processador de músicas `0x0810A724`, inicialização de áudio e outros wrappers/helpers.
Ainda faltam o build completo da ROM, testes de execução por frame e o port PC.
