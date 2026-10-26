# Tarefa de sequência, primeiro filho e fade

ROM USA `BDVE`, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
`0x080C863C` e onze dependências foram reconstruídas em C/GNU C:
**1.556/1.656 bytes iguais à ROM**. Todas usam agbcc GCC 2.9-arm-000512,
`-O2 -mthumb-interwork`, com compilador e assembly emitido preservados.

| Função | Endereço | Fonte | Bytes completos |
|---|---|---|---:|
| `Func_080C863C` | `0x080C863C` | `src/sequence_create.c` | 328 |
| `Sequence_Prepare` | `0x080C8964` | `src/sequence_prepare.c` | 104 |
| `Sequence_Run` | `0x080C8784` | `src/sequence_run.c` | 196 |
| `Sequence_Finish` | `0x080C88F0` | `src/sequence_finish.c` | 116 |
| `Sequence_OnDestroy` | `0x080C88EC` | `src/sequence_destroy.c` | 4 |
| `Sequence_StartAfterBoot` | `0x080C8898` | `src/sequence_after_boot.c` | 72 |
| `BootSequence_Initialize` | `0x080F3368` | `src/boot_sequence_initialize.c` | 136 |
| `BootSequence_OnDestroy` | `0x080F33F0` | `src/boot_sequence_destroy.c` | 4 |
| `Func_0800C0C8` | `0x0800C0C8` | `src/fade_create.c` | 264 |
| `ScreenFade_Commit` | `0x0800C230` | `src/fade_commit.c` | 108 |
| `ScreenFade_Run` | `0x0800C29C` | `src/fade_run.c` | 200 |
| `ScreenFade_OnDestroy` | `0x0800C38C` | `src/fade_destroy.c` | 24 |

Os dois destruidores vazios contêm `BX lr` e dois zeros de alinhamento.
São entradas comprovadas pelos ponteiros passados a `Task_Create`. Os nomes novos
descrevem a análise e não são símbolos históricos recuperados.

## O que faz `0x080C863C`

`Game_CreateCounterTask` chama essa função com `(0, 0, 4, 0)`, depois de criar a
tarefa contadora. A assinatura agora explicita ID de 16 bits, dois argumentos
de oito bits e um callback de conclusão. Ela limpa o byte `+0x16` do contexto
em `0x02028110` e cria outra tarefa: dados de **20 bytes**, prioridade `0x200`,
flags `0x10`, preparação em `0x080C8964` e destrutor em `0x080C88EC`.
O endereço dos dados conserva a seleção EWRAM/IWRAM determinada pelo alocador.

| Offset dos dados | Campo observado |
|---|---|
| `+0` | Estado inicial 0 |
| `+1` | Segundo argumento |
| `+2` | Segundo argumento + 1, truncado para byte |
| `+3` | Modo de conclusão, terceiro argumento |
| `+4` | ID de sequência, primeiro argumento |
| `+8` | Contador de 32 bits, inicialmente 0 |
| `+0xC` | Cursor VRAM, inicialmente `0x06010000` |
| `+0x10` | Callback opcional de conclusão |

O byte `gSequenceClearFlags[id]`, em `0x08A48250`, decide a limpeza gráfica.
Para ID 0 ele vale 1. Nesse caminho, a função:

1. Zera o shadow de controle de vídeo em `0x03003C00`.
2. Faz três preenchimentos DMA de 64 bytes, usando os char bases dos três primeiros
   backgrounds, com controle `0x85000010` e leitura do controle após cada disparo.
3. Zera os valores de limpeza dos backgrounds 2, 1 e 0 e configura seus retângulos
   como `(0, 0, 255, 64)`, na mesma ordem da ROM.
4. Preenche os **96 KiB de VRAM**, `0x06000000..0x06018000`, com zero por
   `Bios_CpuFastSet`, controle `0x01006000`.

Os três DMAs e o preenchimento final reutilizam a mesma célula local de 32 bits.
As views em `include/sequences.h` mantêm os offsets e larguras de acesso.

## Caminho da inicialização e conclusão

`Sequence_Prepare` consulta a tabela de inicializadores em `0x08A482AC`. Uma
entrada nula instala `Sequence_Finish`. Uma entrada válida recebe o endereço do
cursor VRAM, os dados da sequência e o endereço do contador; depois instala
`Sequence_Run` como próximo callback.

Para o ID inicial 0, a tabela contém **`0x080F3369`**, com bit Thumb:
`BootSequence_Initialize`, agora reconstruída. Ela limpa `0x01000000` de
`gSystemFlags`, cria um filho com **44 bytes**, prioridade `0x200`, flags `0x10`,
e callback `0x080F2FD0`. Zera os 44 bytes, salva os ponteiros para a sequência,
contador e cursor, registra o dado ROM `0x08A63B2C` e incrementa o estado do pai.
O formato completo desse dado ROM continua pendente.

`Sequence_Run` incrementa o contador e instala a conclusão quando o estado é zero.
Conserva também o caminho de tecla `0x8`, a exceção do ID `0x46`, as máscaras
`0x40` e `0x20080`, a solicitação de fade de modo 4, a limpeza dos shadows de
janela, `gDisplayControlShadow &= 0x9FFF` e o contador forçado a 10000.
No caminho que cria o fade, retorna antes de testar o estado nessa passagem.

`Sequence_Finish` guarda o modo e o callback, zera a primeira cor da paleta BG,
ativa o bit 0, máscara `0x1`, em `gSystemFlags` e destrói a tarefa. Modo 12 não
chama continuação. Nos outros modos, usa o callback opcional ou a tabela de
conclusão em `0x08A48418`.

No caminho inicial, modo 4 e callback nulo selecionam a entrada
**`0x080C8899`**, também reconstruída: `Sequence_StartAfterBoot`. Ela destrói
as tarefas na faixa `[0, 0xFFFF)`, com limite superior exclusivo, esvazia as filas gráficas pelos índices,
zera a contagem de sprites de fundo e chama **`Func_080C863C(0x4D, 0, 1, 0)`**.
Assim, a inicialização segue para outra sequência através de dados e callbacks
identificados na ROM.

## Serviço de fade

`Func_0800C0C8` remove o fade anterior, se houver, e cria uma tarefa de 12 bytes,
prioridade **`0xFFFE`**, flags 4. `gScreenFadeTask` é um alias do word já mapeado
em `0x02029EB4`. O modo é truncado para oito bits; o `switch` gera uma tabela de
oito ponteiros em `0x0800C148..0x0800C168`.

| Modos | Flags iniciais | Passo signed de 16 bits | Valor inicial e alvo |
|---|---:|---:|---|
| 1, 5 | 2 | `+0x400` | 0 até `0x1000` ou `0x800` |
| 3, 7 | 3 | `+0x400` | 0 até `0x1000` ou `0x800` |
| 2, 6 | 0 | `-0x200` | `0x1000` ou `0x800` até 0 |
| 4, 8 | 1 | `-0x200` | `0x1000` ou `0x800` até 0 |

Os modos 2 e 4 começam com atraso 6. O commit escreve nos shadows de blend:
`0x80` ou `0xC0`, combinado com a máscara `0x3F`, e intensidade
`(valor >> 8) & 0x1F`. O callback preserva as comparações signed, os limites,
o atraso e o bit `0x10` que solicita destruição. O destrutor limpa os shadows
de blend e o ponteiro global da tarefa.

## Prova, extensões GNU C e limites

Cada `.text` foi linkada no endereço original e comparada por inteiro, incluindo
literais, a tabela do fade e todos os zeros de alinhamento. Não há recorte,
máscaras de diferenças, opcodes embutidos ou edição do assembly emitido.

O criador de sequência usa **três restrições vazias**, para o zero inicial e as
bases RAM. A atualização do fade usa **uma**, conservando o ponteiro em `r0`
antes do commit; o corpo do commit ignora esse registrador. O inicializador do
filho usa **uma**, para conservar o endereço da célula zero antes da escrita e
da chamada BIOS. Todos os templates são strings vazias e constam do manifesto.
Os outros nove fontes não contêm inline assembly. Há macros GNU C com expressão
de bloco para conservar a resolução dos dados da tarefa.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target sequence_create
.\.venv\Scripts\python.exe tools\match.py --target boot_sequence_initialize
.\.venv\Scripts\python.exe tools\match.py --target fade_create
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Nesta etapa, o conjunto passou de 65 funções e 15.072 bytes para **77 funções e 16.628 bytes
iguais à ROM**. Os **50 testes passaram, sem skips**, incluindo os 77 alvos e
controles negativos de prioridade, tamanho do preenchimento, callback, tecla,
guardas de skip, modo 12, sequência seguinte, estado do pai e limites do fade.
Relatórios individuais em `build/matching/<id>/report.json`; agregado em
`build/matching/summary.json`; auditoria em `build/verification.json`.

A continuação [apresentação inicial](boot_presentation_matching.md) concluiu
**`BootSequence_Run` (`0x080F2FD0`)** e doze dependências: o conjunto atual tem
**224 funções, 33.032 bytes iguais e 190 testes aprovados**. Outros inicializadores
e conclusões das tabelas, o serviço de paleta, wrappers BIOS e trampolines Thumb
permanecem externos. Ainda faltam o build da ROM inteira, teste por frame em emulador e o port PC.
