# Comando de transposição KEYSH

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

`MusicEvent_KeyShift`, em `0x0810A5F4`, está reconstruído em **C para o port nativo**.
A reprodução do build GBA usa **assembly separado com 20/20 bytes idênticos**.
O candidato ARM C tem 20 bytes, mas ainda difere em cinco; permanece em `nonmatching/`,
fora da contagem de C com matching.

| Alvo | Endereço USA | Instruções | Padding | Total | Matching GBA |
|---|---|---:|---:|---:|---|
| `MusicEvent_KeyShift` | `0x0810A5F4` | 18 | 2 | 20 | Assembly |

O binário completo foi linkado no endereço original e comparado com a ROM, incluindo
os dois zeros de alinhamento. Não há máscaras, recortes, seções alocadas omitidas,
relocations restantes ou edição do assembly gerado. A região reconstruída de áudio
`0x0810A4AC..0x0810A608` na etapa KEYSH soma **348 bytes contínuos idênticos**.

O agregado atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. A última suíte geral, na etapa de instrumento, passou em
**290 testes, sem skips**. O despachante nativo atende **59 endereços de áudio em C**.

## Comportamento

O comando ocupa o slot 11 da tabela de música e usa o opcode `0xBC`. Ele chama
`Music_ReadCommandFiltered` (`0x0810A548`), grava o byte em `track+0x0A` e preserva as
flags existentes, acrescentando a máscara `0x0C` ao status em `track+0`.

A rotina armazena os oito bits do parâmetro. O cálculo posterior de pitch interpreta
a transposição como um valor com sinal: `0x00` é zero, `0x7F` é +127, `0x80` é -128
e `0xFF` é -1. A máscara solicita recálculo e propagação do pitch para os canais ativos.
O leitor incrementa o cursor antes de ler o parâmetro e aplica o filtro de endereço;
a versão nativa preserva a ordem, inclusive quando parâmetro e campos da trilha se sobrepõem.

Na criação de uma nota, o cálculo de volume/pitch atualiza os campos calculados da
trilha, e o processador de notas usa essa transposição na frequência. Para uma nota
já ativa, o final da atualização do player recalcula a frequência do mesmo canal.
O byte da nota original no canal continua preservado. Frequências PCM e CGB conservam
os limites observados nas rotinas anteriores; a verificação usa os resultados da ROM.

## Implementações e prova de bytes

O C nativo é `Dbaa_MusicEventKeyShift`, em
[audio_helpers.c](../port/audio/audio_helpers.c), com declaração em
[audio_helpers.h](../port/include/audio_helpers.h). `Dbaa_AudioCall` aceita o endereço
com ou sem bit Thumb e também resolve o leitor em C. Os endereços do GBA continuam
inteiros de 32 bits; os ponteiros do host Windows x64 não são truncados.

O original salva LR em `r12`, chama o leitor que retorna em `r3`, altera o campo e as
flags, e retorna por `BX r12`. Essa convenção também está documentada na referência
[m4a0.s do SA2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A ROM local fornece os bytes e endereços usados no gate.

| Candidato atual | Bytes ROM | Bytes C | Diferenças |
|---|---:|---:|---:|
| agbcc GCC 2.9-arm-000512 | 20 | 20 | 5 |
| GCC 3.4.6 Thumb | 20 | 20 | 5 |

O candidato usa duas restrições GNU C vazias, sem instruções embutidas. Os compiladores
continuam gerando um prólogo/epílogo diferente. O fonte está em
[music_event_key_shift.c](../nonmatching/music_event_key_shift.c); a referência exata
está em [music_event_key_shift.s](../asm/music_event_key_shift.s). Os 20 bytes novos
são contabilizados como assembly. Compiladores e arquivos gerados permanecem inalterados.

## Validação nativa

[verify_music_key_shift.py](../tools/verify_music_key_shift.py) compara o C Windows x64
com as rotinas originais executadas em Unicorn. Passaram **2.385 cenários**:

- 5 controles dirigidos para valores negativos, flags, filtro e alias do cursor.
- 1.024 combinações dos 256 parâmetros com quatro estados e outros 256 bytes de status.
- 60 casos de parâmetros sobrepostos e 16 origens filtradas.
- 512 casos aleatórios com seed fixa.
- 256 sequências de criação de nota e 256 de alteração de uma nota existente.

As **512 sequências reais** executam duas atualizações do player cada, totalizando
**1.024 atualizações**. Cobrem todos os 256 parâmetros nos dois modos e canais PCM/CGB.
Conferem a execução do comando e do leitor, o campo de transposição, o pitch calculado,
a frequência, o cursor, a permanência da nota no mesmo canal e a flag de atualização CGB.
Cada frequência esperada é calculada por uma chamada independente à rotina PCM/CGB da
ROM, com a nota somada à transposição signed e o limite inferior zero.

Todas as comparações exigem igualdade da RAM do jogo, dos callbacks e das leituras
observadas, além de SP e registradores preservados. As **oito instruções** do comando
foram percorridas; os dois bytes de padding entram na comparação binária e ficam fora
da medida de cobertura. Não houve fallback para ARM nos 59 endereços ligados ao nativo.

Os testes negativos alteram o campo, a máscara de pitch, a preservação das flags e o
leitor com filtro. As alterações precisam ser detectadas. Os nove corpora anteriores
foram reexecutados com os fontes e headers atuais. A referência usa Unicorn ARM926 para
comparação funcional do código; não constitui validação de ciclos do ARM7TDMI, boot
completo do GBA ou matching de bytes do binário Windows.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_key_shift
.\.venv\Scripts\python.exe tools\verify_music_key_shift.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Mixer, backend de áudio/vídeo/entrada, recursos, saves e
sistemas de gameplay precisam de integração e validação durante a execução completa.
O número de slots mede essa tabela, sem representar um percentual do jogo.
Veja o [estado atual do port](port_status.md).

O [comando de volume](music_volume_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, nove testes próprios e reexecução dos doze corpora nativos.

O [comando de pan](music_pan_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos treze corpora nativos.

O [pitch bend](music_pitch_bend_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos quatorze corpora nativos.
