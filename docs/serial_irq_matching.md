# Callback serial com matching integral

ROM USA `BDVE`, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
`Serial_IrqHandler`, em `src/serial_irq.c`, reconstrói a região
**`0x08114E6C..0x0811509C`: 560/560 bytes iguais à ROM**. O fim é exclusivo.
O compilador é o agbcc GCC 2.9-arm-000512, `-O2 -mthumb-interwork`.

A comparação inclui todos os blocos, os seis endereços da tabela de saltos,
os literais e o alinhamento. Os dois últimos literais estão depois do epílogo,
em `0x08115094` e `0x08115098`.

## Fluxo e estados

Na entrada, o callback copia o registrador de dados serial de 32 bits para
`gSerialLastReceived`, para o timer e escreve o reload `0x8000`. Depois despacha
o byte `gSerialAuxByte`. A tabela ocupa `0x08114EB8..0x08114ED0`:

| Estado | Bloco na ROM | Comportamento observado |
|---:|---|---|
| 0 | `0x08114ED0` | Handshake, seleção das duas palavras de 16 bits e resposta |
| 1 | `0x08114F94` | Retorno não zero do helper volta a 0; zero avança para 2 |
| 2 | `0x08114FD4` | Retorno não zero do helper volta a 0; zero avança para 3 |
| 3 | `0x08115014` | Retorno não zero do helper volta a 0; zero conserva 3 |
| 4 | `0x08115054` | Desabilita o bit `0x80` de IE e retorna |
| 5 | `0x08115054` | Mesmo bloco do estado 4 |
| Outros | `0x08115054` | Mesmo bloco de desativação |

No estado 0, `lane` escolhe a ordem das duas palavras recebidas. O contador de
handshake avança quando as palavras conferem com os complementos de 16 bits
esperados. A sequência em `0x08D271D8` contém `0x494E`, `0x544E`, `0x4E45`,
`0x4F44`: os oito bytes ASCII **`NINTENDO`**, em little endian. Depois das quatro
palavras, a confirmação `0x8002` muda o estado para 1 e prepara o primeiro pacote.
Comparações que falham reiniciam o contador conforme os caminhos presentes na ROM.

Nos estados 1, 2 e 3, o retorno não zero de `Serial_ProcessPacket` zera o contador,
preenche os 12 bytes auxiliares com zero por `Bios_CpuSet` e volta ao estado 0.
Cada caso mantém seu próprio zero local na pilha: `sp+0`, `sp+4` e `sp+8`.
Depois, `Serial_MakePacket` recebe o estado atual; o resultado é salvo em
`gSerialLastSent` e escrito no registrador serial.

Os caminhos ativos terminam com `SIOCNT |= 0x80` e controle do timer `0xC1`.
O caminho de desativação faz `IME = 0`, `IE &= 0xFF7F`, `IME = 1` e retorna,
sem passar por esse reinício. O valor anterior de IME não é salvo.

## Estado de memória e geração em C

| Símbolo | Endereço | Uso |
|---|---|---|
| `gSerialHandshake` / `gSerialAuxState` | `0x03000870` | Duas views do bloco auxiliar de 12 bytes |
| `gSerialLastSent` | `0x0300087C` | Última palavra de resposta |
| `gSerialLastReceived` | `0x03000880` | Snapshot de entrada do callback |
| `gSerialAuxByte` | `0x03006FE0` | Estado do despacho |

Os campos usados pela rotina estão em `include/serial.h`. Os nomes descrevem a
engenharia reversa; não são símbolos históricos recuperados. A view mantém a
compatibilidade com os serviços serial já reconstruídos.

O fonte usa GNU C com variáveis vinculadas a registradores, uma expressão de
bloco e **sete templates assembly vazios**. Eles conservam o endereço de IO
através da chamada, a extração das palavras, a duração do primeiro resultado,
o complemento truncado, a ordem de cálculo do índice e o segundo resultado vivo
durante a escrita do complemento. Não contêm instruções nem dados executáveis.
O compilador gera a tabela de saltos a partir do `switch` C.

Não há opcodes embutidos, função naked, edição da saída do compilador, recorte
da seção ou máscaras de comparação. O binário é linkado no endereço original
antes de comparar a seção inteira com a ROM.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target serial_irq
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os novos controles negativos recompilam cópias do C com a confirmação `0x8002`
alterada, a entrada 5 da tabela trocada por 6 e a máscara IE alterada. Todos
precisam reprovar. O teste geral também compara os bytes da tabela e dos pools.
Os relatórios ficam em `build/matching/serial_irq/`.

O conjunto atual tem **224 funções e 33.032 bytes iguais à ROM**, com **190 testes
aprovados, sem skips**. Inclui a [parada de trilha](music_track_stop_matching.md),
que usa um perfil de compilação alternativo.

`Serial_ProcessPacket` (`0x0811509C`), seu validador de checksum (`0x08115108`)
e `Serial_MakePacket` (`0x08115144`) agora têm matching, conforme
[serial_packets_matching.md](serial_packets_matching.md). O wrapper BIOS continua externo.
Essa validação não substitui um teste de comunicação entre duas instâncias do jogo
nem representa o build de uma ROM inteira ou do port PC.
