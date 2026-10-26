# Fila de mapas: matching de 0x0810DDCC

Verificação em 16/10/2026, ROM USA BDVE rev. 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

`src/graphics_process_background_queue.c` recompila **2.868/2.868 bytes**, de
`0x0810DDCC` a `0x0810E900` exclusivo, com **zero diferenças**. A comparação inclui
instruções, saltos, pools de constantes e alinhamento. O fonte foi formatado e recompilado
pelo pipeline completo antes da aprovação.

SHA-256 do candidato e da referência:
`8232b853b4a0055f649bb9a01dc274b77c6a264e779b9715b87558700be3970a`.

## Comportamento reconstruído

A rotina ocupa o slot 3 da tabela gráfica `0x08D26710`. Ela consome a fila de descritores
em `0x03002B60`, com índices de leitura em `0x03003F74` e escrita em `0x03003D00`.
O índice avança com máscara `0xF`, preservando a fila circular de 16 entradas.

- Verifica VBlank por `DISPSTAT`; retorna 0 se precisar adiar o processamento.
- Seleciona mapas de texto ou afins, determinando entradas de um ou dois bytes e o pitch.
- Copia mapas com inversão horizontal/vertical, aplicando as máscaras de atributos de tile.
- Divide transferências de mapas com rolagem nos limites dos blocos de tela.
- Decompõe coordenadas de metatiles com `Bios_Div`, recorta cada trecho e transfere suas linhas
  por DMA3. O único serviço externo chamado é `Bios_Div`, em `0x08115A8C`.
- Conserva as coordenadas anteriores, lê `VCOUNT` e prossegue até esvaziar a fila ou sair de VBlank.

Os `BL` para destinos dentro desse intervalo são saltos longos locais. Eles não representam
serviços adicionais. O fluxo alcançável contém 1.350 instruções; a pilha local reserva 68 bytes.

## Forma do C e configuração de compilação

Esta é uma reconstrução **GNU C que explicita o fluxo de registradores e os blocos do CFG**.
Ela contém aritmética, conversões, acessos de memória, condições, chamadas C e `goto`.
Não se afirma que seja a grafia do fonte histórico. Ela ainda depende dos registradores e
endereços de memória do GBA, portanto não é uma implementação portátil pronta para PC.

O compilador é o mesmo agbcc GCC 2.9-arm-000512, sem alterações nos fontes, commit
`da598c1d918402c42c0c0d7128ba14567f3175e9`. Para esta reconstrução, as flags verificadas são
**`-O1 -mthumb-interwork`**, registradas por alvo em `config/functions.usa.json` e no relatório.
As outras 41 funções continuam com `-O2 -mthumb-interwork`. Isso não prova que a compilação
histórica desta função tenha usado `-O1`.

Há 36 templates GNU C vazios para conservar valores e vínculos de registradores. Todos são
strings vazias e não emitem instruções. O compilador antigo atribui tamanho estimado a esses
templates, o que pode expandir um desvio curto em dois saltos mesmo quando o código real cabe.

Nove limites de blocos são conservados por endereços de labels C (`&&anchor_*`) numa tabela
estática `flowAnchors`. A tabela tem **36 bytes de metadados**, gerados pelo compilador a partir
dos próprios labels; não contém código de máquina nem dados extraídos da ROM. O linker coloca
`.debug_dbaa_flow` em uma seção **INFO, não alocável e não executável**, fora da imagem de execução.
Essa seção mantém os blocos separados para combine/reload sem acrescentar instruções ou aumentar
a estimativa do alcance dos saltos. O matcher verifica sua existência, tamanho e flags.

O objeto possui essa seção auxiliar; o corpo executável `.text` completo tem exatamente
2.868 bytes. Nenhum byte de `.text` é removido, corrigido, mascarado ou ignorado. Não há strings
de instruções assembly, opcodes embutidos, função naked, alteração do compilador ou edição do
assembly/binário após sua geração.

O algoritmo mais legível usado durante a investigação foi preservado em
`reference/graphics_background_queue.c`. Esse arquivo é uma referência de estudo, não um alvo
de build nem uma segunda implementação contada como matching. A fonte SAT-R/sa2 ajudou a interpretar
o motor; a aprovação desta reconstrução vem da comparação com a ROM USA local.

## Reprodução e controles

```powershell
.\.venv\Scripts\python.exe tools\match.py --target graphics_process_background_queue
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O relatório fica em `build/matching/graphics_process_background_queue/report.json`.
Ele registra as flags efetivas, hashes de fonte, headers, compilador, assembly, linker e o
resultado da comparação integral. `label_metadata` registra separadamente os 36 bytes auxiliares.

O teste negativo `test_changed_background_queue_wrap_fails_the_gate` troca a máscara da fila de
`0xF` para `0xE` em uma cópia do C e exige diferenças após recompilar. O teste de todos os alvos
também verifica as flags por função e a natureza não alocável dos metadados de labels.

Esse marco levou o conjunto a **42 funções e 12.416 bytes com matching integral**, com os quatro slots da
tabela gráfica reconstruídos. Ainda faltam a ROM completa, validação por frame em emulador,
dependências transitivas e sistemas de gameplay para chegar ao port nativo.

A etapa posterior de [tarefas e memória](tasks_memory_matching.md) elevou o total então verificado para
52 funções e 13.484 bytes; os tamanhos e resultados individuais desta rotina permanecem iguais.

A continuação de [reset serial, buffers e áudio](reset_services_matching.md), seguida do
[callback serial](serial_irq_matching.md), da [parada de trilha](music_track_stop_matching.md),
dos [pacotes](serial_packets_matching.md) e das [sequências](sequences_initialization_matching.md),
leva o total atual a 224 funções e 33.032 bytes iguais. O resultado desta rotina permanece igual.
