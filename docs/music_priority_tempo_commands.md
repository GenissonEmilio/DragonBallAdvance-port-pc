# Comandos de prioridade e tempo

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

Os comandos de prioridade (`0x0810A5D4`) e tempo (`0x0810A5E0`) estão reconstruídos em
**C para o port nativo**. A reprodução dos bytes do build GBA usa **assembly separado**:
12/12 e 20/20 bytes, respectivamente, sem diferenças. Os candidatos ARM C ainda diferem
e permanecem em `nonmatching/`, fora da contagem de matching C.

| Alvo | Endereço USA | Instruções | Padding | Total | Matching GBA |
|---|---|---:|---:|---:|---|
| `MusicEvent_Priority` | `0x0810A5D4` | 10 | 2 | 12 | Assembly |
| `MusicEvent_Tempo` | `0x0810A5E0` | 20 | 0 | 20 | Assembly |
| **Total novo** | | **30** | **2** | **32** | |

Os binários completos foram linkados nos endereços originais e comparados com a ROM,
incluindo os dois zeros de alinhamento. Não há máscaras, truncamento do candidato,
seções alocadas omitidas, relocations restantes ou pós-processamento do assembly.
Com as reconstruções anteriores, o trecho `0x0810A4AC..0x0810A5F4` possui
**328 bytes contínuos idênticos**.

O conjunto atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. A última suíte geral, na etapa de instrumento, passou em
**290 testes, sem skips**. O despachante do port atende **59 endereços de áudio em C**.

## Comportamento reconstruído

A tabela original de comandos usa os slots 9 e 10, opcodes `0xBA` e `0xBB`.
Ambos chamam `Music_ReadCommandFiltered` em `0x0810A548`, já reconstruído na etapa de
[padrões e repetição](music_pattern_commands.md). O leitor incrementa `track+0x40`
antes de ler o byte e aplicar o filtro de endereço. A ordem é mantida mesmo com
parâmetros sobrepostos aos campos da trilha ou do player.

Prioridade grava o byte filtrado em `track+0x1D`. O processador de notas combina esse
valor com `player+9` e satura a prioridade do canal em 255. Isso é diferente do campo
de prioridade geral do player; o teste integrado confere a prioridade efetivamente
atribuída a uma nota real, incluindo a saturação.

Tempo dobra o byte e grava o resultado em `player+0x1C`. Em seguida lê o fator
unsigned de 16 bits em `player+0x1E`, multiplica com precisão de 32 bits, desloca o
produto oito bits à direita e grava os 16 bits inferiores em `player+0x20`:

```c
base = parameter * 2;
interval = ((base * scale) >> 8) & 0xFFFF;
```

O produto máximo é `510 * 65535 = 33422850`; cabe em 32 bits. O truncamento ocorre
na escrita final de 16 bits, depois do deslocamento. Truncar o produto antes, ou tratar
o fator como signed, muda o resultado. A escrita do tempo base precede a leitura do
fator. O novo intervalo passa a ser usado pela próxima chamada do player; os ticks
já acumulados na atualização atual não são substituídos pelo comando.

## C nativo e matching GBA

As implementações `Dbaa_MusicEventPriority` e `Dbaa_MusicEventTempo` estão em
[audio_helpers.c](../port/audio/audio_helpers.c), com API em
[audio_helpers.h](../port/include/audio_helpers.h). `Dbaa_AudioCall` resolve os dois
endereços com ou sem bit Thumb. Chamadas ao leitor também são resolvidas em C.
Os endereços do jogo ficam em inteiros de 32 bits, com memória little-endian fornecida
pelo host; ponteiros Windows x64 não são truncados.

No GBA, as duas rotinas guardam LR em `r12`, chamam um leitor que retorna o byte em
`r3` e preserva `r0/r1`, e retornam por `BX r12`. A referência da biblioteca m4a usa
a mesma convenção: [m4a0.s do SA2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A ROM local é a referência para validar os bytes e endereços.

As restrições GNU C vazias dos candidatos evitam cópias dispensáveis dos registradores,
mas os compiladores testados ainda geram um prólogo/epílogo diferente:

| Candidato atual | Bytes ROM | agbcc: bytes / diferenças | GCC 3.4.6: bytes / diferenças |
|---|---:|---:|---:|
| Prioridade | 12 | 12 / 5 | 12 / 5 |
| Tempo | 20 | 24 / 8 | 24 / 14 |

Os candidatos atuais estão em [music_event_priority.c](../nonmatching/music_event_priority.c)
e [music_event_tempo.c](../nonmatching/music_event_tempo.c). As referências exatas estão
em [music_event_priority.s](../asm/music_event_priority.s) e
[music_event_tempo.s](../asm/music_event_tempo.s). Nenhum byte desses dois alvos é
atribuído à contagem C com matching. Compiladores e assembly gerado permanecem inalterados.

## Validação comportamental

[verify_music_priority_tempo.py](../tools/verify_music_priority_tempo.py) compara o C
Windows x64 com as rotinas da ROM executadas em Unicorn. Passaram **3.525 cenários**:

- 7 controles dirigidos para prioridade, limites de cálculo, alias do cursor e filtro.
- 256 bytes de prioridade e 2.560 combinações dos 256 bytes de tempo com dez fatores.
- 22 parâmetros sobrepostos aos campos da trilha/player, 32 origens filtradas e
  oito casos com as próprias estruturas sobrepostas.
- 512 casos aleatórios com seed fixa.
- 128 sequências do player real, com **256 atualizações** no total.

As sequências reais exigem que os dois comandos e o leitor sejam alcançados. Na primeira
atualização verificam a prioridade do canal, o tempo base, o intervalo calculado, a
posição do cursor e a criação da nota. A segunda atualização parte da memória resultante
e confere que o novo intervalo determina quantos ticks foram processados.

As comparações verificam RAM do jogo, leituras observadas, callbacks, SP e registradores
preservados. As **13 instruções** dos comandos foram percorridas, sem contar padding
como cobertura. Não houve fallback para ARM. A referência usa Unicorn ARM926 para o
subconjunto funcional; isso não valida ciclos do ARM7TDMI, o hardware completo ou o boot.

Os controles negativos alteram destino da prioridade, multiplicador, fator signed,
truncamento prematuro do produto e leitor sem filtro. Cada alteração precisa falhar.
Os oito corpora anteriores também foram reexecutados com os fontes e headers atuais.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_priority
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_tempo
.\.venv\Scripts\python.exe tools\verify_music_priority_tempo.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

Esse inventário cobre a tabela, sem representar percentual do jogo. O port ainda não
é jogável: mixer, backend de áudio/vídeo/entrada, recursos, saves e gameplay precisam
ser integrados e validados em execução completa. Veja o [estado do port](port_status.md).

O [comando de volume](music_volume_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, nove testes próprios e reexecução dos doze corpora nativos.

O [comando de pan](music_pan_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos treze corpora nativos.

O [pitch bend](music_pitch_bend_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos quatorze corpora nativos.
