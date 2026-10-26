# Callback 0x080F0040 e carregamento do fundo especial

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes são descritivos, atribuídos neste projeto.

## Resultado

O callback solicitado, **`0x080F0040`**, foi reconstruído em C com
**56/56 bytes iguais à ROM**. A etapa acrescentou **16 funções e 1.564 bytes**:
1.378 de instruções, 172 de literais e 14 de alinhamento. O agregado atual tem
**224 funções, 33.032 bytes iguais e 190 testes aprovados, sem skips**.

| Função | Endereço USA | Bytes completos |
|---|---|---:|
| `PostBoot_Phase21` | `0x080F0040` | 56 |
| `PostBoot_Phase22` | `0x080F0078` | 112 |
| `PostBoot_Phase23` | `0x080F00E8` | 36 |
| `PostBoot_Phase24` | `0x080F010C` | 64 |
| `PostBoot_Phase25` | `0x080F014C` | 56 |
| `PostBoot_Phase26` | `0x080F0184` | 44 |
| `PostBoot_Phase27` | `0x080F01B0` | 36 |
| `PostBoot_Phase28` | `0x080F01D4` | 56 |
| `PostBoot_Phase29` | `0x080F020C` | 24 |
| `PostBoot_LoadMap` | `0x080EEFE8` | 316 |
| `PostBoot_LoadPalette` | `0x080EF124` | 188 |
| `PostBoot_ApplyBackground` | `0x080EF1E0` | 80 |
| `PostBoot_LoadSpecialBackground` | `0x080EF230` | 108 |
| `PostBoot_LoadSpecialTiles` | `0x080EF29C` | 168 |
| `PostBoot_LoadSpecialMap` | `0x080EF344` | 112 |
| `PostBoot_LoadSpecialPalette` | `0x080F04E0` | 108 |

Todos usam agbcc GCC 2.9-arm-000512 com **`-O2 -mthumb-interwork`**.
Doze fontes não usam asm. Quatro usam **nove templates vazios**, documentados
no manifesto: três no mapa comum, um na espera do fade, quatro nos tiles
especiais e um no preenchimento da paleta especial. **Nenhum emite instruções.**

## Callbacks e tempos

`PostBoot_Phase21` aguarda **`flags & 0x40`**, a sinalização intermediária
da conclusão do fade processada por `PostBoot_Update`. Quando ela aparece,
desliga o BG indicado pela entrada **7** do roteiro e agenda `0x080F0078`.
Na ROM USA essa entrada corresponde a BG0. A função não incrementa `step`.

A fase 22 aguarda o bit de skip livre e `elapsed >= timeline[step]`,
incrementa o passo e configura a entrada **8** em três chamadas distintas:
mapa, paleta e prioridade/scroll. Seus tiles já foram transferidos pela
[cópia em blocos da etapa anterior](post_boot_phases_matching.md).
Depois liga o BG da entrada 8, solicita fade na direção zero e só avança
quando `PostBoot_StartFade` retorna sucesso.

A fase 23 aguarda os bits `0x10` e 1 ficarem livres. A fase 24 aguarda o
próximo tempo e solicita fade na direção 1. A fase 25 espera `0x40` e desliga
o BG da entrada 8. A fase 26, com o bit de skip livre, limpa seu mapa.
A fase 27 limpa o mapa do BG da entrada **9**, sem essa guarda de skip.

A fase 28 carrega a entrada 9 e liga seu BG. Na USA ela usa BG2, ID signed
**-1**, que seleciona o recurso padrão **98** no carregador comum. Os dois
valores de scroll armazenados são `0xFFB8`. A fase 29 carrega a entrada
**10**, que usa BG0, prioridade 3 e banco de paleta 2, e registra o ponteiro
Thumb **`0x080EEA7D`**, para o callback agora reconstruído na
[etapa de sprites e scroll](post_boot_phase30_matching.md).

No caminho iniciado com passo zero, os quatro novos valores efetivamente
usados da tabela `0x08A4E438` são:

| Passo | Valor | Uso |
|---:|---:|---|
| 14 | 147 | Início da configuração da entrada 8 |
| 15 | 162 | Limite usado para calcular a duração de seu primeiro fade |
| 16 | 190 | Início do segundo fade |
| 17 | 205 | Limite usado para calcular sua duração |

São contagens absolutas de `data->elapsed`. Agora foram verificados os
primeiros dezoito valores; a extensão completa da tabela continua em aberto.

## Serviços comuns de fundo

`PostBoot_LoadMap` seleciona o recurso pelo ID signed, com fallback 98,
obtém o mapa em `asset+0x18` e escolhe o screenblock pelos bits 8..12 do
controle do BG. Preserva os dois caminhos do carregador maior:

- Cópia normal por linha com `CpuSet`, largura em halfwords, máscara
  `0x1FFFFF` e stride de **32 halfwords** no destino.
- Espelhamento com destino decrescente e **XOR `0x0400`** em cada entrada,
  incluindo a inversão do flip horizontal do tile.

Quando os bancos de origem e destino diferem, remapeia somente os quatro
bits superiores: `(tile & 0x0FFF) | ((destinationPalette & 15) << 12)`.
O contador de linha é unsigned de 16 bits; o de coluna é unsigned de oito.

`PostBoot_LoadPalette` também preserva o ID signed e o fallback. Com
`gSystemFlags & 0x10000`, chama `0x08114668`, usando destino mascarado para
quatro bits. No outro caminho, usa DMA3 para o buffer BG, com destino sem
essa máscara, quantidade em halfwords e bit `0x80000000`. Há leitura de
retorno do controle DMA. Ao terminar, zera a primeira cor BG e ativa o bit 0
de `gSystemFlags`, mesmo quando a quantidade de paleta é zero.

`PostBoot_ApplyBackground` preserva as **duas escritas** de prioridade no
shadow: primeiro limpa os bits 0..1, depois combina a prioridade da entrada.
Em seguida escreve os dois valores de scroll. Não carrega tiles nem paleta.

## Fundo especial construído por tabelas

O caminho especial de `PostBoot_LoadBackground(10)` está agora reconstruído
por completo. `PostBoot_LoadSpecialBackground` aplica a prioridade, extrai
charblock e screenblock, chama os três auxiliares e aplica scroll. Usa o
campo **`sourcePalette`** para os auxiliares de mapa e paleta.

`PostBoot_LoadSpecialTiles` lê nove registros de quatro bytes em
**`0x08A4E400`**. Cada registro contém dois pares de valor e quantidade de
words. O valor é expandido em oito posições de quatro bits de uma word.
Na tabela real, os valores vão de 0 a 7 e as quantidades somam **72 words**:
**288 bytes, nove tiles de 4 bpp**. O tile central combina quatro words de
índice 3 e quatro de índice 4; os demais usam oito words de um só índice.
Tudo é escrito diretamente no charblock selecionado, sem descompressão.

O limite de nove registros é conservado em `r8`; as words expandidas usam
`r3`. As quatro restrições vazias conservam esses valores e a alocação do
offset. A última expansão unsigned é feita em uma instrução C separada,
depois das leituras anteriores do valor, mantendo a ordem de avaliação definida.

`PostBoot_LoadSpecialMap` lê dez bytes em **`0x08A4E424`**:

```text
1, 1, 2, 2, 3, 4, 5, 6, 7, 8
```

Cada índice preenche uma linha de 32 tiles. Depois escreve outras dez linhas
na ordem inversa com **`0x0800`**, o flip vertical. Combina o banco de paleta
nos quatro bits superiores. O resultado contém **640 halfwords, 32 × 20 tiles**.

`PostBoot_LoadSpecialPalette` lê oito níveis em **`0x08A4E42E`**:

```text
0, 31, 28, 24, 20, 16, 12, 8
```

Converte cada nível para o canal azul com `(level << 10) & 0x7C00`, escreve
as primeiras oito cores do banco e zera as oito restantes por `CpuSet`.
Depois ativa o bit 0 de `gSystemFlags`. Esse auxiliar escreve no buffer de
paleta diretamente; ele não usa a seleção entre serviço e DMA do carregador comum.

## Evidências e continuação

```powershell
.\.venv\Scripts\python.exe tools\match.py --target post_boot_phase21
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O comparador usa a seção `.text` inteira, linkada no endereço original,
incluindo literais e alinhamento. Não há relocations pendentes, edição de
assembly, alterações no compilador, opcodes embutidos ou máscaras de diferenças.
Os controles negativos recompilam alterações de callbacks, flags, recursos,
limites de tempo, cópia/espelhamento, paleta, tabelas e preenchimentos, e exigem
que cada alteração seja rejeitada pelo comparador.

Relatórios locais: `build/matching/summary.json`, relatórios individuais e
`build/verification.json`. A classificação dos bytes desta etapa fica em
`build/next/phase21_flow.json`; as leituras de tabelas em `phase21_tables.json`.
A auditoria também compara a concatenação integral de todo o bloco local:

| Início | Fim exclusivo | Bytes | Funções |
|---|---|---:|---:|
| `0x080EE654` | `0x080F0910` | 8.892 | 96 |

A etapa de [sprites e scroll](post_boot_phase30_matching.md) concluiu
`0x080EEA7C` e quinze dependências, com 1.724 bytes iguais.
O [callback `0x080F02EC` e o encerramento](post_boot_phase38_matching.md) também têm matching.
O [desenho de sprites, alocador OAM, serviço de paleta e memset](graphics_draw_sprite_matching.md) também têm matching.
A [animação `0x0810FD70`, seus doze comandos e a paleta OBJ](sprite_animation_matching.md) também têm matching.
O [início do player e cinco serviços de áudio](music_player_start_matching.md) também têm matching.
Permanecem externos o processador de músicas `0x0810A724`, inicialização de áudio e outros wrappers/helpers.
Ainda faltam o build completo
da ROM, a validação de execução por frame e o port PC.
