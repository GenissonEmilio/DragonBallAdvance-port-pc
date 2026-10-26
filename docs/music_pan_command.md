# Comando de pan PAN

`MusicEvent_Pan`, em `0x0810A64C`, está reconstruído em **C para o port nativo Windows x64**.
O build GBA usa **assembly separado com 20/20 bytes idênticos à ROM USA BDVE rev0**,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`. Os candidatos C ARM têm 24 bytes,
com oito diferenças na comparação completa; ficam explicitamente em `nonmatching/`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 20 | Todos os bytes iguais à ROM; 9 instruções, sem padding |
| C candidato agbcc GCC 2.9-arm-000512 | 24 | 8 diferenças, incluindo os bytes extras |
| C candidato GCC 3.4.6 Thumb | 24 | 8 diferenças, incluindo os bytes extras |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
A região `0x0810A4AC..0x0810A660` na etapa de pan contém **436 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xBF`, slot 14 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`), subtrai `0x40`, grava o byte em `track+0x14` e preserva o status
acrescentando a máscara `0x03`. O leitor incrementa o cursor antes de ler e filtrar
o parâmetro. O nativo conserva essa ordem em sobreposições com os campos da faixa.

O armazenamento é de oito bits. O cálculo posterior interpreta o byte com sinal:

| Parâmetro | Byte armazenado | Pan com sinal |
|---:|---|---:|
| 0 | `0xC0` | -64 |
| 64 | `0x00` | 0 |
| 127 | `0x3F` | 63 |
| 128 | `0x40` | 64 |
| 191 | `0x7F` | 127 |
| 192 | `0x80` | -128 |
| 255 | `0xBF` | -65 |

O comando não restringe o parâmetro a 127 nem satura a subtração. O cálculo de volumes
combina duas vezes esse pan com o pan auxiliar e, quando aplicável, a modulação. Só
depois limita o resultado a `[-128,127]` e calcula os lados direito/esquerdo. As flags
solicitam recálculo e propagação aos canais existentes; canais CGB recebem a flag de
atualização de volume. Volume bruto, volume mestre, frequência e instrumento permanecem
preservados ao alterar o pan de uma nota ativa.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventPan`.
- API: [audio_helpers.h](../port/include/audio_helpers.h). O despachante aceita o endereço
  par e o ponteiro Thumb e conserva os endereços GBA como inteiros de 32 bits.
- Referência GBA: [music_event_pan.s](../asm/music_event_pan.s).
- C ARM não correspondente: [music_event_pan.c](../nonmatching/music_event_pan.c).
- Validação: [verify_music_pan.py](../tools/verify_music_pan.py) e
  [test_music_pan.py](../tests/test_music_pan.py).

O original salva LR em `r12`, recebe o parâmetro filtrado em `r3` e conserva a faixa em
`r1`. Os candidatos usam duas restrições GNU C vazias, sem incorporar instruções assembly.
Os 16 bytes intermediários coincidem; o prólogo/epílogo dos compiladores gera diferenças
e quatro bytes extras. O gate compara os 24 bytes inteiros do candidato com os 20 da ROM,
incluindo a diferença de tamanho. Nenhum candidato C é contado como matching.

A convenção também aparece na referência local do
[m4a0.s do SA2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A ROM local determina os bytes e endereços usados na prova.

O gate de assembly compara o `.text` completo linkado no endereço original, sem máscaras,
recortes ou edição do assembly gerado. Rejeita seções alocadas extras e relocations
restantes. As nove instruções ocupam os 20 bytes; não há literal pool nem padding.
Os bytes assembly são contabilizados separadamente dos compilados de C.

## Validação desta etapa

Passaram **2.385 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 parâmetros com quatro estados e
  outros 256 bytes de status.
- 60 sobreposições e 16 parâmetros em endereços filtrados.
- 512 casos aleatórios com seed fixa.
- 256 sequências de criação de nota e 256 de mudança de pan em uma nota existente.

As **512 sequências do player real** somam **1.024 atualizações**. Cobrem PCM/CGB,
pan auxiliar, modulação, volumes bruto/mestre, truncamentos e saturação. Conferem por
aritmética independente os volumes da faixa e dos canais. Casos dirigidos verificam
esquerda, centro, direita e a mudança de sinal nos valores altos. As notas existentes
conservam canal, frequência, instrumento, amostra e volumes bruto/mestre; canais CGB
recebem a flag de volume correta. RAM, leituras observadas e callbacks foram iguais.
SP e registradores preservados também são verificados. Nenhum serviço novo usa fallback
ARM no lado nativo.

Os **doze testes próprios passaram**, incluindo mutações de campo, máscara, preservação
de status, bias, clamp indevido e filtro. Os **treze corpora nativos** foram reexecutados
com os fontes e headers atuais. Os gates recompilaram os 242 alvos C e os 16 assembly.
A última suíte geral passou em **290 testes na etapa de instrumento**; a suíte daquela etapa
tinha 311 testes descobertos e não foi reexecutada integralmente nesta etapa.

Unicorn ARM926 é usado para comparação funcional. A prova não valida ciclos do ARM7TDMI,
mixer/dispositivos completos, boot integral nem matching dos bytes do executável Windows.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_pan
.\.venv\Scripts\python.exe tools\verify_music_pan.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_pan.py -v
```

Evidências: `build/native_music_pan_validation/report.json`,
`build/assembly_matching/music_event_pan/report.json`, `build/next/music_pan/tests_target.log`
e `build/verification.json`. Os testes atuais e a suíte geral histórica são registrados separadamente.

## Port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada, inicialização
integrada, recursos, saves e sistemas de gameplay, seguidos de comparação durante o jogo
completo. O número de slots não representa um percentual do port.
Veja o [estado atual](port_status.md).

O [pitch bend](music_pitch_bend_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos quatorze corpora nativos.
