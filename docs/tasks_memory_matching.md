# Criação de tarefas e heaps: matching de 0x0810D758

Verificação em 16/10/2026, ROM USA BDVE rev. 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

`Task_Create`, em `src/task_create.c`, recompila **316/316 bytes**, de
`0x0810D758` a `0x0810D894` exclusivo, com **zero diferenças**. Esta etapa acrescentou
dez alvos e **1.068 bytes**: sete rotinas de tarefas/memória e três callbacks sentinelas.
Todos foram comparados integralmente após formatação dos fontes e link no endereço original.

| Função | Endereço | Bytes iguais | Fonte |
|---|---|---:|---|
| `Task_Create` | `0x0810D758` | 316 | `src/task_create.c` |
| `Task_Destroy` | `0x0810D894` | 184 | `src/task_destroy.c` |
| `Tasks_IwramAlloc` | `0x0810DA20` | 104 | `src/iwram_alloc.c` |
| `Tasks_IwramFree` | `0x0810DA88` | 124 | `src/iwram_free.c` |
| `Tasks_DestroyPriorityRange` | `0x0810DBF8` | 120 | `src/tasks_destroy_priority.c` |
| `Task_HeadSentinel` | `0x0810DC9C` | 4 | `src/task_head.c` |
| `Task_TailSentinel` | `0x0810DCA0` | 4 | `src/task_tail.c` |
| `Task_UnusedSentinel` | `0x0810DCA4` | 4 | `src/task_unused.c` |
| `Heap_EwramAlloc` | `0x0811562C` | 100 | `src/ewram_alloc.c` |
| `Heap_EwramFree` | `0x08115690` | 108 | `src/ewram_free.c` |

Cada sentinela contém um retorno Thumb de dois bytes e dois bytes de alinhamento zero.
São alvos separados pelos endereços originais; não são três rotinas adicionais de lógica de jogo.
Os nomes são descritivos deste projeto, não símbolos históricos recuperados.

## Criação e inserção

`Task_Create` usa `gFreeTaskIndex`, em `0x030030EC`, para retirar um dos 128 descritores
de `gTaskHeads`, em `0x03002CD0`. Se não houver slot, retorna o endereço de `gEmptyTask`,
em `0x03002C70`, e não um ponteiro nulo. O limite inclui os dois descritores sentinelas
reservados por `Tasks_Initialize`.

A rotina grava o callback, destrutor, prioridade e flags. O bit `0x10` seleciona dados
em EWRAM; sem esse bit, tenta IWRAM primeiro. Uma alocação IWRAM sem sucesso para tamanho
não zero aciona a tentativa em EWRAM. No caminho que começa em EWRAM, compara o ponteiro
reconstituído com `gEwramAllocationFailure`, em `0x0203A0C0`, e pode voltar para IWRAM.
Esse valor é lido da RAM; não foi substituído por uma constante de conveniência.

O campo `dataOffset` é de 16 bits. Para IWRAM, soma-se `0x03000000`; para EWRAM, multiplica-se
o offset por quatro e soma-se `0x02000000`. A criação conserva os casos de tamanho zero
e as conversões do endereço completo para esse formato. Não foi acrescentada uma política
de rollback do descritor em caso de falha das duas tentativas.

O campo `unknown00` é o offset da tarefa pai (`gCurrentTask`); `unknown02` é o offset da tarefa
anterior. Os nomes antigos dos campos foram mantidos com comentários para evitar mudanças
desnecessárias nos fontes já validados. A inserção ocorre antes da primeira prioridade
estritamente maior, preservando a ordem entre tarefas de mesma prioridade. O caso de uma
prioridade que nunca encontra um sucessor maior também segue o comportamento original.
Se a inserção alterar o predecessor da próxima tarefa, `gNextTask` passa a apontar para a nova.

## Destruição e continuação durante callbacks

`Task_Destroy` ignora tarefas protegidas pelo bit `2` e nós sem predecessor/sucessor válido.
Chama o destrutor com **o ponteiro da tarefa como argumento**, corrige as continuações,
remove o nó da lista, libera seus dados no heap selecionado e devolve o descritor ao pool.
O callback do descritor liberado passa a `Task_UnusedSentinel`.

O tipo `DbaaTaskDestructor` agora registra esse argumento. `Game_CreateCounterTask` faz
uma conversão explícita para seu callback de reset, que ignora o argumento recebido.
As alterações de tipos e nomes também foram recompiladas: as funções anteriores mantêm
seus mesmos bytes.

`Tasks_DestroyPriorityRange` usa o intervalo **[lower, upper)**, preserva os dois sentinelas
e salva a próxima tarefa antes de chamar um destrutor. Isso permite que o callback altere
ou destrua tarefas durante a passagem. Seu endereço já aparecia como `Func_0810DBF8`
em `Func_080FA048`; essa chamada agora usa o nome reconstruído.

O endereço `0x03003108` é **um ponteiro de continuação de destruição**, não um contador.
Foi renomeado de `gTaskCount` para `gNextTaskForDestruction`, inclusive na inicialização.
O nome `gTaskHeapHead` também foi substituído por `gEmptyTask` para o descritor de fallback.

## Alocadores

Os dois heaps usam busca do primeiro bloco livre que comporte o pedido, arredondamento
para múltiplos de quatro e tamanhos negativos para blocos ocupados. A liberação transforma
o tamanho em positivo e une blocos livres fisicamente adjacentes, antes e depois do nó.

IWRAM usa links de 16 bits e cabeçalhos de quatro bytes, iniciando em `0x03003F90`.
O tamanho arredondado é truncado para 16 bits e comparado como signed de 16 bits. EWRAM usa
ponteiros completos, cabeçalhos de oito bytes e a raiz em `0x02000520`. Seu alocador conserva
a primeira comparação unsigned e o teste signed do espaço mínimo de uma divisão de bloco.
Essas distinções e os wraps foram preservados; as estruturas estão em `include/task_memory.h`.

`Heap_EwramFree` ignora ponteiro zero e o valor de falha configurado. `Tasks_IwramFree`
mantém o contrato observado de receber um bloco válido; não foram adicionadas checagens
que alterariam as instruções da ROM.

## Compilação e prova

Os dez alvos usam o agbcc GCC 2.9-arm-000512, **`-O2 -mthumb-interwork`**, sem alterações
no compilador e sem pós-processamento do assembly. São funções C estruturadas; os ajustes
de geração são explícitos:

- `Task_Create` conserva um `do/while (0)` vazio e uma restrição GNU C de template vazio
  para antecipar o endereço do ponteiro de falha antes da seleção do endereço dos dados.
- `Tasks_DestroyPriorityRange` usa um template vazio com clobber de `r5` para conservar a
  alocação do ponteiro de continuação.
- `Tasks_IwramFree` vincula a variável do predecessor a `r1`.
- `Heap_EwramAlloc` faz uma releitura `volatile` do tamanho depois de escrever o link do
  nó dividido, reproduzindo a leitura adicional da ROM.

Os templates não contêm instruções. Não há opcodes embutidos, função naked, máscaras de
comparação, recortes ou correções posteriores. Cada `.text` completa, incluindo pools e
alinhamento, deve ser idêntica à região da ROM. As referências de algoritmo do motor SAT-R/sa2
ajudaram na leitura; a prova é o binário compilado deste projeto comparado com a ROM USA.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target task_create
.\.venv\Scripts\python.exe tools\match.py --target iwram_alloc
.\.venv\Scripts\python.exe tools\match.py --target tasks_destroy_priority
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os relatórios e hashes estão em `build/matching/<id>/report.json`, com o agregado em
`build/matching/summary.json`. Os novos controles negativos alteram o limite de slots,
a inserção de prioridades iguais, o arredondamento IWRAM e o teste de união de blocos EWRAM;
todos precisam reprovar depois de recompilar e linkar a cópia alterada do C.

## Estado do projeto

Nesta etapa, o conjunto passou a **52 funções e 13.484 bytes com matching integral**. São 51 alvos com
`-O2 -mthumb-interwork`; a reconstrução anterior da fila de mapas continua com `-O1` e
seus metadados de labels documentados separadamente.

As chamadas de `Task_Create` aos dois alocadores agora têm corpos C validados, assim como
a destruição por faixa usada no reset da inicialização. Ainda permanecem externos os
destrutores específicos registrados pelo jogo e o trampoline `_call_via_r1`. Há outras
rotinas do sistema de tarefas que não fazem parte destes dez alvos.

A continuação de [reset serial, buffers e áudio](reset_services_matching.md) concluiu
`0x08114D70`, `0x080010C4`, `0x08000FDC`, `0x0810AEEC` e quatro serviços auxiliares.
A etapa seguinte concluiu o [callback serial](serial_irq_matching.md) e a
[parada de trilha](music_track_stop_matching.md); os três serviços de
[pacotes seriais](serial_packets_matching.md) levam o total atual a
**224 funções e 33.032 bytes iguais**, incluindo a continuação de
[sequências e fade](sequences_initialization_matching.md), que concluiu `0x080C863C`
e onze dependências. O callback filho `0x080F2FD0` e doze dependências também foram concluídos em
[apresentação inicial](boot_presentation_matching.md). Outros serviços transitivos permanecem externos.
Ainda faltam a ROM inteira, execução por frame em emulador e a camada de hardware do port PC.
