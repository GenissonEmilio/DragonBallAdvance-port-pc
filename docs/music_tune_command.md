# Comando de afinação TUNE

`MusicEvent_Tune`, em `0x0810A6AC`, está reconstruído em **C para o port nativo
Windows x64**. O build GBA usa **assembly separado com 20/20 bytes idênticos à ROM USA
BDVE rev0**, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 20 | Todos iguais: 9 instruções, sem literais ou padding |
| C candidato agbcc GCC 2.9-arm-000512 | 24 | 8 diferenças, incluindo quatro bytes extras |
| C candidato GCC 3.4.6 Thumb | 24 | 8 diferenças, incluindo quatro bytes extras |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
Na etapa de afinação, a região `0x0810A4AC..0x0810A6C0` contém **532 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xC8`, slot 23 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`), subtrai `0x40`, grava o byte em `track+0x0C` e acrescenta `0x0C`
às flags existentes. O leitor incrementa o cursor antes de ler e filtrar o parâmetro.
O port preserva essa ordem, inclusive com sobreposição de campos e cursor.

O byte armazenado é interpretado com sinal pelo cálculo de pitch. Não há clamp
em 127 ou saturação da subtração. Um endereço rejeitado pelo filtro produz zero
antes da subtração, resultando em afinação -64. Alguns exemplos:

| Parâmetro | Byte armazenado | Afinação com sinal | Contribuição em semitons |
|---:|---:|---:|---:|
| 0 | 192 | -64 | -1 |
| 64 | 0 | 0 | 0 |
| 127 | 63 | 63 | 0,984375 |
| 128 | 64 | 64 | 1 |
| 191 | 127 | 127 | 1,984375 |
| 192 | 128 | -128 | -2 |
| 255 | 191 | -65 | -1,015625 |

A unidade é **1/64 de semitom**. A contribuição da afinação em unidades de 1/256
de semitom é `4 * signed(track[0x0C])`; ela não é multiplicada pelo alcance do bend.
O cálculo completo conserva transposição, afinação fina adicional, bend e modulação:

```text
pitch = 4 * (signed(track[0x0C]) + signed(track[0x0E]) * unsigned(track[0x0F]))
pitch += 256 * (signed(track[0x0A]) + signed(track[0x0B])) + unsigned(track[0x0D])
se track[0x18] == 0: pitch += 16 * signed(track[0x16])
coarse = floor(pitch / 256) & 255
fine = pitch & 255
```

As flags solicitam recálculo e propagação do pitch às notas existentes. O canal,
nota original, instrumento, amostra, envelope, volumes e pan são conservados.
Os canais CGB recebem a flag de pitch `0x02`; os limites próprios das rotinas
PCM/CGB e o limite inferior zero da nota ajustada são mantidos.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventTune`.
- API: [audio_helpers.h](../port/include/audio_helpers.h).
- Assembly GBA: [music_event_tune.s](../asm/music_event_tune.s).
- C ARM não correspondente: [music_event_tune.c](../nonmatching/music_event_tune.c).
- Validação: [verify_music_tune.py](../tools/verify_music_tune.py) e
  [test_music_tune.py](../tests/test_music_tune.py).

O original salva LR em `r12`, recebe o parâmetro filtrado em `r3` e mantém a faixa
em `r1`. Os candidatos usam duas restrições GNU C vazias, sem incorporar instruções
assembly. Seus 16 bytes intermediários coincidem; prólogo e retorno diferem.
As imagens completas têm 24 bytes e oito diferenças contra os 20 da ROM.
Permanecem explicitamente fora do matching C.

O gate compara todo o `.text` linkado no endereço original e rejeita seções alocadas
extras e relocations restantes. Não há máscaras, recortes ou alterações no assembly
gerado. Os bytes do assembly separado são contabilizados à parte dos fontes C com matching.

## Validação desta etapa

Passaram **2.495 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 parâmetros com quatro estados e
  outros 256 bytes de status.
- 72 sobreposições de memória e 16 parâmetros em endereços filtrados.
- 512 casos aleatórios com seed fixa.
- 305 sequências com criação de nota e 305 mudanças de afinação de uma nota existente.

As **610 sequências do player** somam **1.220 atualizações**. Os sete parâmetros
de borda `0,64,127,128,191,192,255` são cruzados com os oito alcances de bend
`0,1,2,12,64,127,128,255` nos dois modos, totalizando 112 sequências dirigidas.
Elas conferem que TUNE mantém sua contribuição inclusive com alcance zero.
Os demais parâmetros também variam bend, transposição, afinação fina adicional e modulação.

O pitch é conferido por aritmética independente; cada uma das 610 frequências
esperadas vem de uma chamada independente à rotina PCM/CGB da ROM. A nota existente
permanece no mesmo canal, com bend, volume, pan, instrumento e nota original preservados.
RAM, leituras observadas e callbacks coincidiram. SP e registradores preservados
também são conferidos. Nenhum serviço novo usa fallback ARM no lado nativo.

Passaram os **12 testes próprios**, incluindo mutações de campo, máscara,
preservação de flags, subtração, filtro e clamp indevido. Os **18 corpora nativos
de áudio** foram reexecutados com os fontes e headers atuais, além dos gates dos
**242 alvos C e 21 assembly**. A suíte geral daquela etapa continha **371 testes** e não foi
reexecutada integralmente; a última execução completa continua sendo a de 290
testes da etapa de instrumento. Na primeira execução, três testes de mutação não
chegaram à comparação porque o Windows Code Integrity bloqueou suas DLLs temporárias.
A suíte completa foi repetida pelo procedimento normal, com os registros de bloqueio
e os dois logs preservados. As políticas de segurança foram mantidas. O teste passou
a incluir a saída da ferramenta na mensagem de falha quando falta o artefato de comparação.

Unicorn ARM926 fornece comparação funcional. Os resultados não validam ciclos do
ARM7TDMI, dispositivos completos ou boot integral. A equivalência comportamental
Windows é registrada separadamente do matching de bytes GBA.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_tune
.\.venv\Scripts\python.exe tools\verify_music_tune.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_tune.py -v
```

Evidências: `build/native_music_tune_validation/report.json`,
`build/assembly_matching/music_event_tune/report.json`,
`build/next/music_tune/tests_target.log` e `build/verification.json`.

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada,
inicialização integrada, recursos, saves e sistemas de gameplay, seguidos de
validação durante o jogo completo. Veja o [estado atual](port_status.md).

O [PORT](music_port_command.md) foi integrado na etapa seguinte: 24 bytes assembly
exatos, doze testes próprios e reexecução dos dezenove corpora de áudio.
