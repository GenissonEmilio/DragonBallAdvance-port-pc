# Comando de pitch bend BEND

`MusicEvent_PitchBend`, em `0x0810A660`, está reconstruído em **C para o port nativo Windows x64**.
O build GBA usa **assembly separado com 20/20 bytes idênticos à ROM USA BDVE rev0**,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`. Os candidatos C ARM têm 24 bytes
e oito diferenças na comparação completa; ficam explicitamente em `nonmatching/`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 20 | Todos os bytes iguais à ROM; 9 instruções, sem padding |
| C candidato agbcc GCC 2.9-arm-000512 | 24 | 8 diferenças, incluindo os bytes extras |
| C candidato GCC 3.4.6 Thumb | 24 | 8 diferenças, incluindo os bytes extras |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
Na etapa de pitch bend, a região `0x0810A4AC..0x0810A674` contém **456 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xC0`, slot 15 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`), subtrai `0x40`, grava o byte em `track+0x0E` e preserva o status
acrescentando `0x0C`. O leitor incrementa o cursor antes de ler e filtrar o parâmetro.
O nativo preserva essa ordem, inclusive quando parâmetro, cursor e campos se sobrepõem.

O byte armazenado é interpretado depois com sinal. `0` produz -64, `64` produz zero,
`127` produz 63 e `255` produz -65. Os 256 parâmetros são aceitos pelo handler;
não há clamp artificial em 127 nem saturação da subtração.

A máscara solicita recálculo e propagação do pitch aos canais existentes. O alcance
em `track+0x0F` é um byte **sem sinal**. A contribuição do bend para o pitch em unidades
de 1/256 de semitom é `4 * bend_signed * alcance`. Por exemplo, parâmetro zero com
alcance 2 contribui -512, ou -2 semitons. Centro 64 ou alcance zero anulam essa contribuição;
transposição, afinação e modulação ainda podem contribuir separadamente.

O cálculo completo conserva os sinais, truncamentos e a quantização da ROM:

```text
pitch = 4 * (signed(track[0x0C]) + signed(track[0x0E]) * unsigned(track[0x0F]))
pitch += 256 * (signed(track[0x0A]) + signed(track[0x0B])) + unsigned(track[0x0D])
se track[0x18] == 0: pitch += 16 * signed(track[0x16])
coarse = floor(pitch / 256) & 255
fine = pitch & 255
```

O cálculo da frequência soma o `coarse` interpretado com sinal à nota original e aplica
o limite inferior zero. As rotinas PCM/CGB conservam seus próprios limites. Os valores
altos de alcance podem fazer o byte `coarse` dar a volta; o port reproduz esse comportamento.
Notas novas recebem a frequência calculada; notas existentes permanecem no mesmo canal
e recebem a atualização, com a flag de pitch `0x02` nos canais CGB. Volume e instrumento
não são solicitados para atualização por esse comando.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventPitchBend`.
- API: [audio_helpers.h](../port/include/audio_helpers.h). O despachante aceita o endereço
  par e o ponteiro Thumb e usa endereços GBA como inteiros de 32 bits.
- Referência GBA: [music_event_pitch_bend.s](../asm/music_event_pitch_bend.s).
- C ARM não correspondente: [music_event_pitch_bend.c](../nonmatching/music_event_pitch_bend.c).
- Validação: [verify_music_pitch_bend.py](../tools/verify_music_pitch_bend.py) e
  [test_music_pitch_bend.py](../tests/test_music_pitch_bend.py).

O original salva LR em `r12`, recebe o parâmetro filtrado em `r3` e conserva a faixa em
`r1`. Os candidatos usam duas restrições GNU C vazias, sem incorporar instruções assembly.
Os 16 bytes intermediários coincidem. O prólogo/epílogo dos compiladores gera diferenças
e quatro bytes extras; os 24 bytes completos são comparados com os 20 da ROM. Nenhum
candidato C é contado como matching.

A convenção também aparece na referência local do
[m4a0.s do SA2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A ROM local determina os bytes e endereços usados na prova.

O gate compara o `.text` completo linkado no endereço original e rejeita seções alocadas
extras e relocations restantes. Não há máscaras, recortes nem edição do assembly gerado.
As nove instruções ocupam os 20 bytes, sem literais nem padding. Os bytes assembly
permanecem separados dos compilados de C nas contagens.

## Validação desta etapa

Passaram **2.483 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 parâmetros com quatro estados e
  outros 256 bytes de status.
- 60 sobreposições e 16 parâmetros em endereços filtrados.
- 512 casos aleatórios com seed fixa.
- 305 sequências de criação de nota e 305 de mudança de bend em uma nota existente.

As **610 sequências do player real** somam **1.220 atualizações**. Cobrem os alcances
`0,1,2,12,64,127,128,255`; sete parâmetros de borda são cruzados com os oito alcances
nos dois modos, totalizando 112 sequências dirigidas. Os demais casos variam também
transposição, afinação e modulação.

O pitch calculado é conferido por aritmética independente. Cada uma das 610 frequências
esperadas vem de uma chamada independente à rotina PCM/CGB da ROM. As notas existentes
conservam canal, nota original, instrumento, amostra, envelope, volumes e pan; canais CGB
recebem a flag correta de pitch. RAM, leituras observadas e callbacks foram iguais.
SP e registradores preservados também são conferidos. Nenhum serviço novo usa fallback
ARM no lado nativo.

Os **doze testes próprios passaram**, incluindo mutações de campo, máscara, preservação
de status, bias, clamp indevido e filtro. Os **quatorze corpora nativos** foram reexecutados
com os fontes e headers atuais. Os gates recompilaram os 242 alvos C e os 17 assembly.
A última suíte geral passou em **290 testes na etapa de instrumento**; a suíte daquela etapa
tinha 323 testes descobertos e não foi reexecutada integralmente nesta etapa.

Unicorn ARM926 é usado para comparação funcional. A prova não valida ciclos do ARM7TDMI,
mixer/dispositivos completos, boot integral nem matching de bytes do executável Windows.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_pitch_bend
.\.venv\Scripts\python.exe tools\verify_music_pitch_bend.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_pitch_bend.py -v
```

Evidências: `build/native_music_pitch_bend_validation/report.json`,
`build/assembly_matching/music_event_pitch_bend/report.json`,
`build/next/music_pitch_bend/tests_target.log` e `build/verification.json`.
Os testes atuais e a suíte geral histórica são registrados separadamente.

## Port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada, inicialização
integrada, recursos, saves e sistemas de gameplay, seguidos de comparação durante o jogo
completo. A contagem de slots não representa um percentual do port.
Veja o [estado atual](port_status.md).

O [alcance do bend](music_bend_range_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos quinze corpora nativos.
