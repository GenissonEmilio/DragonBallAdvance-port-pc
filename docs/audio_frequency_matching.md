# Music_CalculateFrequency e frequências PCM/CGB nativas

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

`Music_CalculateFrequency` foi reconstruída em C e reproduz **100/100 bytes**, sem diferenças,
em `0x0810AC90..0x0810ACF4`. A implementação usa o perfil padrão `agbcc` GCC 2.9-arm-000512,
`-O2 -mthumb-interwork`, sem assembly inline ou restrições de registradores. O binário inclui
92 bytes de instruções e oito bytes de literais. A ferramenta compara o tamanho inteiro e
rejeita seções alocadas adicionais e relocations restantes.

O agregado passa a **242 alvos C/GNU C, 33.856 bytes**, e **23 alvos assembly, 2.720 bytes**:
**265 alvos e 36.576 bytes idênticos à ROM**. A última suíte geral (instrumento) passou em **290 testes**, sem skips.
Os 168 bytes C de `Cgb_CalculateFrequency` já tinham matching; esta etapa acrescenta seu
binding nativo, sem contá-los novamente.

## Cálculo PCM

O código está em `src/music_calculate_frequency.c`. Recebe o endereço do cabeçalho da
amostra, nota e ajuste fino de oito bits. Notas acima de 178 são saturadas em 178 com ajuste
255. Cada byte do mapa fornece um índice de frequência nos quatro bits inferiores e um
deslocamento nos quatro superiores. São consultadas a nota atual e a seguinte.

Definindo `high(a, b)` como os bits 63..32 do produto unsigned de 64 bits:

```text
ajuste = high(frequência_seguinte - frequência_base, ajuste_fino << 24)
resultado = high(cabeçalho_da_amostra.frequency, frequência_base + ajuste)
```

A subtração e a soma intermediárias conservam a aritmética unsigned de 32 bits. O campo da
amostra está em `wave+4`. O resultado é o valor usado pelo driver para avançar a amostra;
a síntese, mixagem e saída de áudio continuam sendo etapas separadas.

A chamada GBA ainda resolve `Audio_MultiplyHigh` em `0x0810A074`: uma ponte Thumb/ARM
com `UMULL`, externa ao conjunto de alvos reconstruídos. A versão nativa expressa as duas
multiplicações diretamente com `uint64_t` e não chama essa rotina ARM. O matching dos
100 bytes comprova também os dois destinos BL, sem afirmar reconstrução completa do driver.

A referência C `MidiKeyToFreq` do
[SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a.c)
ajudou a identificar o cálculo. Endereços, limites, instruções e resultado foram conferidos
contra esta ROM. O perfil compatível não identifica exclusivamente o SDK histórico.

## Cálculo CGB e integração

`port/audio/audio_helpers.c` exporta `Dbaa_MusicCalculateFrequency` e
`Dbaa_CgbCalculateFrequency`. `Dbaa_AudioCall` atende `0x0810AC90` e `0x0810B78C`, tanto como
endereços pares quanto como ponteiros Thumb. Nesta etapa o total passou de nove para onze endereços de áudio atendidos em C.
A continuação de [notas/canais](sound_update_track_hybrid.md) elevou o total a treze,
e o [término de notas sustentadas](music_end_tie_hybrid.md) acrescentou o décimo quarto.
Os [comandos de LFO e modulação](music_modulation_commands.md) e seu leitor elevaram o total a dezessete. A etapa de [memória e comandos estendidos](music_memory_commands.md) elevou o total a 31; a continuação de [padrões e repetição](music_pattern_commands.md) elevou o total atual a 35.
Os endereços dos dados GBA permanecem `uint32_t`; o host fornece as
leituras little-endian, sem truncar ponteiros do processo Windows de 64 bits.

O canal CGB 4 consulta a tabela de ruído: notas até 20 usam o primeiro elemento; as demais
subtraem 21 e saturam no índice 59. Os outros canais usam períodos `int16_t`: notas até 35
zeram nota e ajuste; as demais subtraem 36 e saturam em 130/255. A interpolação mantém o
deslocamento aritmético dos números negativos. O C99 nativo usa divisão com arredondamento
explicitamente definido para conservar esse comportamento. Os argumentos são reduzidos a
oito bits, inclusive quando o despachante recebe valores `uint32_t` maiores.

| Dados consultados | Endereço | Bytes acessíveis nesta rotina |
|---|---|---:|
| Mapa de notas PCM | `0x08A674F0` | 180 |
| Frequências PCM | `0x08A675A4` | 48 |
| Mapa de notas CGB | `0x08A675EC` | 132 |
| Períodos CGB signed | `0x08A67670` | 24 |
| Ruído CGB | `0x08A67688` | 60 |

Esses intervalos descrevem os acessos observados e os limites do cálculo. Os dados ainda são
lidos da ROM pelo host; a etapa não extrai o banco completo de instrumentos e músicas.

## Validação

`tools/verify_audio_frequency.py` compila a DLL Windows x64 e compara o C com a execução das
rotinas originais em Unicorn ARM926, incluindo a transição Thumb/ARM do produto alto. A ROM
é a referência dos resultados; Python não recalcula a fórmula esperada. O corpus contém
**237.568 casos**:

- 18.432 PCM: 256 notas, seis ajustes finos e doze frequências da amostra, de zero a `0xFFFFFFFF`.
- 18.432 CGB: todos os 256 valores de canal, doze limites de nota e seis ajustes finos.
- 196.608: três varreduras completas de 256 notas por 256 ajustes, para PCM, CGB tonal e ruído.
- 4.096: argumentos de 32 bits e frequências aleatórias, com seeds fixos.

Comparam o resultado de 32 bits e a ordem, largura e valores das leituras de tabelas/amostra.
O verificador rejeita qualquer callback de fallback para ARM ou escrita da função nativa;
na referência ARM, confere pilha, registradores preservados e ausência de escrita fora da
pilha temporária. A CPU de referência não modela ciclos ARM7TDMI ou dispositivos GBA.

O player integrado passou novamente nos **1.128 cenários**, cobrindo suas 290 instruções,
e os demais auxiliares nos **768 cenários**. Os cinquenta e nove alvos nativos atuais não foram delegados ao ARM.
Notas, comandos, player seguinte e parada CGB ainda usam callbacks sintéticos nesse teste.

Os oito testes novos também verificam mutações deliberadas: limite de nota e deslocamento
do C GBA, metade alta do produto, saturação PCM, arredondamento CGB, limite de ruído e tentativa
de delegar a frequência ao ARM. Uma implementação alterada deve falhar contra a referência.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target music_calculate_frequency
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match_assembly.py --all
.\.venv\Scripts\python.exe tools\verify_audio_frequency.py
.\.venv\Scripts\python.exe tools\verify_music_player.py --cases 1000
.\.venv\Scripts\python.exe tools\verify_audio_helpers.py --cases 64
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Evidências locais: `build/matching/music_calculate_frequency/report.json`,
`build/native_audio_frequency_validation/report.json`, `build/native_music_validation/report.json`,
`build/native_audio_helpers_validation/report.json`, `build/verification.json` e
`build/next/audio_frequency/audit_frequency.py`/`audit_frequency.json`.

A continuação de [notas e canais](sound_update_track_hybrid.md) integrou `0x0810AA00` ao C nativo
e reproduziu seus bytes em assembly separado. Os handlers de eventos da tabela estão ligados;
o [mixer PCM](pcm_mixer_native.md) também foi ligado ao C nativo. Os próximos passos
são serviços transitivos, saída de som e dispositivos. O port completo ainda precisa de gameplay, recursos, backend de vídeo,
entrada, áudio e saves, integração e comparação durante o jogo. Ainda não há executável
jogável; o [estado do port](port_status.md) detalha o trabalho restante.
