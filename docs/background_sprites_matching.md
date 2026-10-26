# Sprites de fundos: matching de 0x0810EFB4

Estado em 16/10/2026, ROM USA BDVE rev. 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

`Graphics_DrawBackgroundSprites`, em `src/graphics_draw_background_sprites.c`, reproduz
**1.340/1.340 bytes**, de `0x0810EFB4` até `0x0810F4F0` exclusivo. O comparador retornou 0.
A função saiu do manifesto de candidatas e entrou em `config/functions.usa.json`.

SHA-256 do binário candidato e da referência:
`53ae6b9d7eed9899bcf2ba62837ac8ace2ea8428749ca41c1a9c24b98275a8b7`.

## Comportamento reconstruído

O slot 2 da tabela gráfica `0x08D26710` desenha sprites no mapa de tiles de um fundo.
A rotina retorna 0 fora de VBlank. Dentro de VBlank, percorre a fila em `0x030065A0`,
pula frames com índice `0xFFFFFFFF`, processa os subframes e zera a contagem em `0x03006C20`.
Os nomes são descritivos; não foram recuperados símbolos originais.

- Seleciona o fundo pelos bits `0x18000` das flags do sprite e obtém as bases de caracteres
  e mapa a partir do controle desse fundo.
- Lê metadados de dimensões com passo de 12 ou 16 bytes e registros OAM da tabela do sprite.
  Cada registro de origem avança seis bytes; DMA3 copia três halfwords para o scratch local.
- No caminho afim, escreve índices de tile de oito bits, agrupados em pares para escritas
  de halfword. O término de uma linha parcial preserva o byte alto já presente.
- No caminho de texto, aplica a paleta, compara as flags de inversão do sprite e do frame,
  ajusta os pivôs e escreve entradas de mapa de 16 bits. Os passos horizontal e vertical
  mudam de sinal conforme as inversões.

Foram conservados os contadores de oito bits, as conversões para 16 bits e o estado de
`tileShift`, inicializado uma vez antes da fila. No caminho de texto, o pitch muda de 32
para 64 quando `(u8)(size - 2) <= 1`, exatamente como nas instruções da ROM.
As expressões de alinhamento e os acessos halfword foram reproduzidos; uma camada de PC
terá de modelar os acessos de memória do GBA antes de executar este C fora do hardware original.

## Como o matching foi fechado

O compilador continua sendo `agbcc` GCC 2.9-arm-000512 com `-O2 -mthumb-interwork`.
O código reserva os mesmos 68 bytes de pilha e tem as mesmas 624 instruções alcançáveis.
Essas observações ajudaram a localizar diferenças; a aprovação depende da comparação de
**todos os bytes**, incluindo pools de literais e alinhamento, não de uma similaridade de assembly.

O fonte usa GNU C, aritmética de ponteiros `void *`, vínculos de registradores e templates
`asm` vazios. Os templates controlam a ordem de avaliação e a duração dos valores, incluindo:

- o ponteiro DMA3 em `r1` e o ponteiro opaco para o scratch OAM em registrador alto;
- as coordenadas, máscaras de inversão e ordem dos deslocamentos antes da negação;
- a duração do halfword lido antes da escrita final de um par parcial;
- a expressão de passo de linha e o estado de recarga de `r7` entre seus dois caminhos.

Todos os templates são strings vazias e estão declarados em `compiler_barriers` no manifesto.
Uma leitura `volatile` do atributo OAM impede reutilizar um valor anterior no caminho de texto.
Isso não identifica unicamente o C histórico. Não há código de máquina embutido, assembly
editado, recortes da saída, máscaras de comparação ou correções posteriores ao link.
A formatação do fonte também foi seguida de nova compilação com zero diferenças.

## Verificação reproduzível

```powershell
.\.venv\Scripts\python.exe tools\match.py --target graphics_draw_background_sprites
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O relatório fica em `build/matching/graphics_draw_background_sprites/report.json`.
Na etapa anterior, concluída com a fila de mapas, o conjunto chegou a **42 funções e 12.416 bytes com matching integral**.
O teste negativo `test_changed_background_sprite_tile_size_fails_the_gate` altera
`tileShift` de 5 para 4 em uma cópia do C e exige reprovação após recompilar e linkar.
A execução completa aprovou 27 testes, sem skips.

## Continuação: fila de mapas concluída

`Graphics_ProcessBackgroundQueue`, em `0x0810DDCC`, foi concluída posteriormente em GNU C,
com 2.868 bytes iguais. Sua configuração `-O1`, a forma que explicita registradores e os
metadados de labels estão documentados em [background_queue_matching.md](background_queue_matching.md).
Os quatro processadores da tabela gráfica agora têm matching. As variantes divergentes
anteriores continuam apenas como experimentos ignorados em `build/next/`.

A etapa posterior de [tarefas e memória](tasks_memory_matching.md) elevou o total então verificado para
52 funções e 13.484 bytes; os tamanhos e resultados individuais desta rotina permanecem iguais.

A continuação de [reset serial, buffers e áudio](reset_services_matching.md), seguida do
[callback serial](serial_irq_matching.md), da [parada de trilha](music_track_stop_matching.md),
dos [pacotes](serial_packets_matching.md) e das [sequências](sequences_initialization_matching.md),
leva o total atual a 224 funções e 33.032 bytes iguais. O resultado desta rotina permanece igual.
