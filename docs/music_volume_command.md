# Comando de volume VOL

`MusicEvent_Volume`, em `0x0810A638`, foi reconstruído em **C para o port nativo Windows x64**.
O build GBA usa **assembly separado com 20/20 bytes idênticos à ROM USA BDVE rev0**,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`. Os candidatos C ARM continuam
explicitamente em `nonmatching/`: ambos têm 20 bytes e diferem em cinco.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 20 | Todos os bytes iguais à ROM, incluindo 2 de alinhamento |
| C candidato agbcc GCC 2.9-arm-000512 | 20 | 5 bytes diferentes |
| C candidato GCC 3.4.6 Thumb | 20 | 5 bytes diferentes |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
A região `0x0810A4AC..0x0810A64C` na etapa de volume contém **416 bytes contínuos idênticos**.

## Comportamento

O opcode `0xBE`, slot 13 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`), grava o byte em `track+0x12` e preserva o status existente acrescentando
a máscara `0x03`. Os oito bits do parâmetro são preservados; não há limite artificial
em 127. O leitor incrementa o cursor antes de ler o parâmetro e aplica o filtro de
endereço. O C nativo mantém essa ordem, inclusive em sobreposições com o cursor/status.

A máscara solicita recálculo dos volumes da faixa e sua propagação aos canais ativos.
O cálculo combina volume do comando, volume mestre/fade, pan e modulação, preservando
os truncamentos e deslocamentos da ROM. As notas novas recebem os volumes calculados;
notas já ativas são atualizadas no mesmo canal. Canais CGB recebem a flag de atualização
de volume. O comando não solicita mudança de pitch nem de instrumento.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventVolume`.
- API: [audio_helpers.h](../port/include/audio_helpers.h). O despachante aceita endereço
  par e ponteiro Thumb; os endereços GBA permanecem inteiros de 32 bits.
- Referência GBA: [music_event_volume.s](../asm/music_event_volume.s).
- C ARM não correspondente: [music_event_volume.c](../nonmatching/music_event_volume.c).
- Validação: [verify_music_volume.py](../tools/verify_music_volume.py) e
  [test_music_volume.py](../tests/test_music_volume.py).

O original salva LR em `r12`, recebe o parâmetro filtrado em `r3` e conserva a faixa em
`r1`. Os compiladores emitem outro prólogo/epílogo. Os 14 bytes intermediários já
coincidem, mas a comparação completa reprova os cinco bytes diferentes. O candidato
usa duas restrições GNU C vazias; não incorpora instruções assembly. A convenção do
SDK também aparece na referência local do
[m4a0.s do SA2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A ROM local determina os bytes e endereços usados na prova.

O gate compara o `.text` completo linkado no endereço original, incluindo as oito
instruções e os dois zeros finais. Rejeita seções alocadas extras e relocations restantes.
Não há máscaras, recortes, substituição de bytes nem edição do assembly gerado.
Os bytes assembly são contabilizados separadamente dos compilados de C.

## Validação desta etapa

Passaram **2.385 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 parâmetros com quatro estados e
  outros 256 bytes de status.
- 60 sobreposições de memória e 16 parâmetros em endereços filtrados.
- 512 casos aleatórios com seed fixa.
- 256 sequências de criação de nota e 256 de mudança do volume de uma nota existente.

As **512 sequências do player real** somam **1.024 atualizações** e cobrem PCM/CGB.
Os volumes calculados da faixa e dos canais são conferidos por aritmética independente,
incluindo pan, modulação, truncamento e saturação. Os casos de notas existentes
verificam a identidade do canal, a flag CGB e a preservação de frequência, instrumento
e amostra. RAM, leituras observadas e callbacks foram iguais; SP e registradores
preservados também são conferidos. Nenhum serviço novo usa fallback ARM no lado nativo.

Os **nove testes próprios passaram**, incluindo mutações de campo, máscara, preservação
de status e filtro do parâmetro. Os **doze corpora de áudio foram reexecutados** com os
fontes e headers atuais. Os gates recompilaram os 242 alvos C e os 17 alvos assembly.
A última suíte geral passou em **290 testes na etapa de instrumento**; a suíte daquela etapa
tinha 299 testes descobertos e não foi reexecutada integralmente nesta etapa.

Unicorn ARM926 é usado para comparação funcional. Esta prova não valida os ciclos do
ARM7TDMI, o mixer/dispositivos completos, boot integral ou bytes do executável Windows.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_volume
.\.venv\Scripts\python.exe tools\verify_music_volume.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_volume.py -v
```

Evidências locais: `build/native_music_volume_validation/report.json`,
`build/assembly_matching/music_event_volume/report.json`, `build/next/music_volume/tests_target.log`
e `build/verification.json`. O relatório distingue os nove testes atuais da suíte geral histórica.

## Port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Mixer, backend de áudio/vídeo/entrada, inicialização integrada,
recursos, saves e sistemas de gameplay ainda precisam de implementação e validação durante
o jogo completo. A contagem de slots não representa um percentual do port.
Veja o [estado atual](port_status.md).

O [comando de pan](music_pan_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos treze corpora nativos.

O [pitch bend](music_pitch_bend_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos quatorze corpora nativos.
