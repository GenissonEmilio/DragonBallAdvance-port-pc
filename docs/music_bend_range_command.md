# Comando de alcance do pitch bend BENDR

`MusicEvent_BendRange`, em `0x0810A674`, está reconstruído em **C para o port nativo
Windows x64**. O build GBA usa **assembly separado com 20/20 bytes idênticos à ROM USA
BDVE rev0**, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 20 | Todos os bytes iguais: 18 de instruções e 2 de padding zero |
| C candidato agbcc GCC 2.9-arm-000512 | 20 | 5 diferenças na imagem completa |
| C candidato GCC 3.4.6 Thumb | 20 | 5 diferenças na imagem completa |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
Na etapa de alcance do bend, a região `0x0810A4AC..0x0810A688` contém **476 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xC1`, slot 16 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`), grava o parâmetro sem sinal em `track+0x0F` e acrescenta a máscara
`0x0C` ao status existente. O leitor incrementa o cursor antes de ler e filtrar o
parâmetro. O port preserva essa ordem mesmo com sobreposição de campos e cursor.
Um endereço rejeitado pelo filtro produz alcance zero.

Todos os valores de 0 a 255 são conservados. Não há subtração de 64, saturação em
127 nem interpretação do alcance como byte com sinal. O bend em `track+0x0E`
permanece intacto e é interpretado com sinal pelo cálculo de pitch. As flags
solicitam recálculo e propagação da frequência às notas existentes.

Em unidades de 1/256 de semitom, a contribuição do bend é
`4 * signed(track[0x0E]) * unsigned(track[0x0F])`. Assim, bend -64 com alcance 2
contribui -2 semitons; alcance zero ou bend zero anulam essa contribuição.
Transposição, afinação e modulação continuam somadas separadamente:

```text
pitch = 4 * (signed(track[0x0C]) + signed(track[0x0E]) * unsigned(track[0x0F]))
pitch += 256 * (signed(track[0x0A]) + signed(track[0x0B])) + unsigned(track[0x0D])
se track[0x18] == 0: pitch += 16 * signed(track[0x16])
coarse = floor(pitch / 256) & 255
fine = pitch & 255
```

O cálculo de frequência soma o `coarse` com sinal à nota original e aplica o limite
inferior zero. Os limites próprios das rotinas PCM/CGB e o truncamento do byte
`coarse` são preservados, inclusive em alcances altos. Uma mudança de alcance
atualiza a frequência da nota existente no mesmo canal. Nos canais CGB, acrescenta
a flag de pitch `0x02`; volume, pan, instrumento e nota original são preservados.

## Fontes e comparação de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventBendRange`.
- API: [audio_helpers.h](../port/include/audio_helpers.h).
- Assembly GBA: [music_event_bend_range.s](../asm/music_event_bend_range.s).
- C ARM não correspondente: [music_event_bend_range.c](../nonmatching/music_event_bend_range.c).
- Validação: [verify_music_bend_range.py](../tools/verify_music_bend_range.py) e
  [test_music_bend_range.py](../tests/test_music_bend_range.py).

O original salva LR em `r12`, usa o parâmetro filtrado em `r3` e mantém a faixa em
`r1`. Os dois candidatos C usam duas restrições GNU C vazias para expressar esse
fluxo de registradores, sem incorporar instruções assembly. Seus 14 bytes
intermediários coincidem; prólogo e retorno diferem. As imagens completas têm
20 bytes e cinco diferenças. Os candidatos permanecem fora do matching C.

O gate compara todo o `.text` linkado no endereço original, incluindo os dois
bytes de padding zero. Rejeita seções alocadas extras e relocations restantes.
Não há máscaras, recortes ou alteração do assembly gerado. O assembly separado
é contado à parte dos fontes C com matching.

## Validação desta etapa

Passaram **2.497 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 parâmetros com quatro estados e
  outros 256 bytes de status.
- 60 sobreposições de memória e 16 parâmetros em endereços filtrados.
- 512 casos aleatórios com seed fixa.
- 312 sequências de criação de nota e 312 alterações de alcance de uma nota existente.

As **624 sequências do player real** somam **1.248 atualizações**. Os oito alcances
`0,1,2,12,64,127,128,255` foram cruzados com os oito bytes de bend
`0,1,63,64,127,128,191,255` nos dois modos, totalizando 128 sequências dirigidas.
Os demais alcances também entram em sequências reais, variando transposição,
afinação e modulação. O pitch é conferido por aritmética independente; cada uma
das 624 frequências esperadas vem de uma chamada independente à rotina PCM/CGB da ROM.

RAM, leituras observadas e callbacks coincidiram. A validação também confere SP,
registradores preservados, flags de pitch e conservação dos demais campos da nota.
Nenhum serviço novo usa fallback ARM no lado nativo. O despachante aceita tanto
o endereço par quanto o ponteiro Thumb e mantém os endereços GBA como inteiros de 32 bits.

Passaram os **12 testes próprios**, incluindo mutações de campo, flags, filtro,
padding, clamp indevido e alcance com sinal. Os **15 corpora nativos de áudio**
foram reexecutados com os fontes e headers atuais, além dos gates dos **242 alvos C
e 18 assembly**. A suíte geral daquela etapa continha **335 testes** e não foi reexecutada
integralmente; a última execução completa continua sendo a de 290 testes da etapa de instrumento.

Unicorn ARM926 fornece comparação funcional; estes resultados não validam ciclos
do ARM7TDMI, dispositivos completos ou boot do jogo inteiro. A equivalência
comportamental do executável Windows é registrada separadamente do matching GBA.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_bend_range
.\.venv\Scripts\python.exe tools\verify_music_bend_range.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_bend_range.py -v
```

Evidências: `build/native_music_bend_range_validation/report.json`,
`build/assembly_matching/music_event_bend_range/report.json`,
`build/next/music_bend_range/tests_target.log` e `build/verification.json`.

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

Ainda não há executável nativo jogável. Faltam mixer, backend de áudio/vídeo/entrada,
inicialização integrada, recursos, saves e sistemas de gameplay, seguidos de validação
durante o jogo completo. A contagem de slots não representa um percentual do port.
Veja o [estado atual](port_status.md).

O [atraso do LFO](music_lfo_delay_command.md) foi integrado na etapa seguinte, com
12 bytes assembly exatos, doze testes próprios e reexecução dos dezesseis corpora nativos.
