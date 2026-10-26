# Processamento e construção de pacotes seriais

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
As duas rotinas solicitadas e seu validador de checksum foram reconstruídos em
C/GNU C com **404/404 bytes iguais à ROM**, após compilação e link completos.
Todos usam agbcc GCC 2.9-arm-000512, `-O2 -mthumb-interwork`.

| Função | Fonte | Início | Fim exclusivo | Bytes |
|---|---|---|---|---:|
| `Serial_ProcessPacket` | `src/serial_process_packet.c` | `0x0811509C` | `0x08115108` | 108 |
| `Serial_ValidatePacket` | `src/serial_validate_packet.c` | `0x08115108` | `0x08115144` | 60 |
| `Serial_MakePacket` | `src/serial_make_packet.c` | `0x08115144` | `0x08115230` | 236 |

O `BL` em `0x081150A8` chama o validador, que tem prólogo e retorno próprios.
Ele é uma terceira função, e não uma continuação do processador de pacotes.

## Formato e checksum

O word serial de 32 bits tem a seguinte organização observada:

| Bits | Conteúdo |
|---|---|
| 31..28 | Tipo, quatro bits |
| 27..4 | Conteúdo, 24 bits |
| 3..0 | Checksum, quatro bits |

O checksum é o XOR dos sete nibbles superiores. O validador lê
`gSerialLastReceived` em `0x03000880`, guarda o nibble inferior, desloca o word
quatro bits e calcula o XOR do tipo com os seis nibbles de conteúdo.
Retorna **0 para checksum igual** e **1 para checksum diferente**.

## Recepção: `Serial_ProcessPacket`

O argumento de etapa é truncado para oito bits. O tipo recebido é capturado
antes da chamada ao validador; os caminhos seguintes relêem o word para obter
o conteúdo. Se o checksum falhar, a função retorna 1 sem atualizar o valor salvo.

| Etapa | Operações depois do checksum válido | Retorno 0 |
|---:|---|---|
| 1 | Salva `conteúdo & 1` em `gSerialPacketValue`, `0x03000884` | Tipo recebido igual a 1 |
| 2 | Confere o tipo e compara o conteúdo inteiro de 24 bits com o valor salvo | Tipo 2 e conteúdo igual |
| 3 | Confere apenas o tipo | Tipo recebido igual a 3 |
| Outras | Não há operação de etapa | Nunca; retorna 1 |

Na etapa 1, a escrita ocorre **antes** de conferir o tipo. Portanto, checksum
válido com tipo errado ainda pode atualizar o bit salvo e retornar 1. Na etapa 2,
a comparação usa os 24 bits completos; não se limita ao bit zero.

Os retornos dão significado ao caminho do [callback de interrupção](serial_irq_matching.md):
o retorno 1 reinicia o handshake, enquanto 0 permite avançar de 1 para 2 e de 2
para 3; na etapa 3, o retorno 0 conserva essa etapa.

## Transmissão: `Serial_MakePacket`

A etapa também é truncada para oito bits. O compilador gera uma tabela de cinco
entradas em `0x08115160..0x08115174`, a partir do `switch` C:

| Etapa | Bloco | Tipo transmitido | Conteúdo |
|---:|---|---:|---|
| 1 | `0x08115174` | 1 | 1 |
| 2 | `0x08115198` | 2 | `gSerialPacketValue & 0xFFFFFF` |
| 3 | `0x081151D0` | 4 | Byte `gInitByte030065EC`, em `0x030065EC` |
| 4 | `0x08115200` | 1 | 1 |
| 5 | `0x08115200` | 1 | 1 |

Cada caminho calcula o XOR, aplica `& 0xF` ao checksum e o combina com o pacote.
As etapas 1, 4 e 5 retornam `0x10000010`. A etapa 3 envia **tipo 4**, embora o
processador na etapa 3 espere **tipo 3** na recepção. Essa diferença foi preservada;
o funcionamento completo entre pares ainda precisa ser observado em execução.

Para etapas fora de 1..5, a sequência original salta diretamente para
`0x08115222` e copia o **valor de entrada de `r1`** para `r0`. O caminho anterior
não modifica `r1`. A reconstrução captura esse registrador com uma restrição GNU C
vazia na entrada, evitando ler uma variável C sem inicialização ou inventar um
retorno zero. Esse detalhe depende da ABI ARM e exigirá uma decisão explícita na
camada do port PC. As chamadas do callback reconstruído usam etapas 1, 2 e 3.

## Geração de código e comparação integral

`Serial_ProcessPacket` é C estruturado, sem inline assembly. O validador usa uma
expressão de bloco e **uma restrição vazia** para conservar o word deslocado como
origem da extração do tipo. A construção usa **cinco restrições vazias**: a captura
de `r1` e duas por caminho nas etapas 2 e 3, para conservar o pacote e a conversão
explícita do tipo para byte. Os vínculos a registradores constam do fonte e as
restrições estão declaradas no manifesto e nos relatórios.

Todos os templates são strings vazias; não há instruções ou opcodes inseridos
neles. O assembler recebe a saída intacta do compilador. O linker resolve os
endereços originais antes de comparar a `.text` inteira, incluindo a tabela,
literais, padding e o último literal depois do retorno de `Serial_MakePacket`.

| Função | Instruções | Literais | Tabela | Zeros de alinhamento | Total |
|---|---:|---:|---:|---:|---:|
| `Serial_ProcessPacket` | 94 | 12 | 0 | 2 | 108 |
| `Serial_ValidatePacket` | 54 | 4 | 0 | 2 | 60 |
| `Serial_MakePacket` | 186 | 24 | 20 | 6 | 236 |

Não há pós-processamento do assembly, recorte de bytes ou máscaras de diferenças.
Os nomes novos descrevem a análise; não se afirma que sejam os símbolos ou o C históricos.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target serial_process_packet
.\.venv\Scripts\python.exe tools\match.py --target serial_validate_packet
.\.venv\Scripts\python.exe tools\match.py --target serial_make_packet
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Esse marco levou o conjunto de 62 funções e 14.668 bytes a 65 funções e 15.072 bytes
iguais à ROM. A continuação de [sequências e fade](sequences_initialization_matching.md)
leva o total atual a **224 funções e 33.032 bytes**, com **190 testes aprovados, sem skips**.
Os controles negativos dos pacotes
alteram a condição do checksum, o bit salvo, a comparação de eco, os nibbles
percorridos, a máscara do checksum, a máscara de conteúdo, o tipo transmitido e
a entrada 5 da tabela. Cada cópia alterada é recompilada e precisa reprovar.

Relatórios: `build/matching/serial_process_packet/report.json`,
`build/matching/serial_validate_packet/report.json` e
`build/matching/serial_make_packet/report.json`. A auditoria agregada está em
`build/verification.json`. Esta é validação de código compilado contra a ROM;
ainda faltam teste de comunicação em execução, ROM inteira reconstruída e port PC.
