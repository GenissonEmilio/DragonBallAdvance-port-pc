# Modo de áudio e VSync-off no port nativo

`Func_0810B2D0` (`0x0810B2D0`) e `Sound_VSyncOff` (`0x0810B3BC`) estão integradas
em **C Windows x64** como `Dbaa_SoundMode` e `Dbaa_SoundVSyncOff`.
O C GBA foi revalidado com **152/152 e 124/124 bytes idênticos** à ROM USA BDVE rev0,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

Esses 276 bytes já pertenciam ao matching e não foram somados novamente.
O total permanece em **242 funções C/GNU C, 33.856 bytes, mais 23 alvos assembly,
2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Nesta etapa havia **51 serviços nativos**;
os 36 slots da tabela após `Sound_Extend` continuam ligados. As dependências
transitivas do áudio e a integração do jogo ainda precisam ser concluídas.

## Modo de áudio

A rotina só aceita `sound->lock == 0x68736D53`. Incrementa o lock durante a
operação e restaura o valor inicial ao terminar. Cada campo de modo zerado
preserva o estado existente:

| Bits do argumento | Efeito quando habilitado |
|---|---|
| 0..7 | Grava reverb em `sound+5`, retirando o bit 7; `0x80` permite gravar zero |
| 8..11 | Grava número de canais em `sound+6` e zera os 12 bytes de status, com stride `0x40` |
| 12..15 | Grava volume em `sound+7` |
| Máscara `0xB00000` | Reescreve os bits 6..7 do byte `0x04000089` a partir dos bits 20..21, preservando os seis bits inferiores |
| 16..19 | Chama VSync-off e depois SetFrequency, nessa ordem |

O bit 23 pode habilitar a escrita de bias mesmo quando os bits 20..21 são zero;
o bit 22 é ignorado. O número de canais não altera o tamanho do laço de limpeza:
ele sempre percorre 12 status, sem zerar os demais campos dos canais.

A cadeia completa preserva as releituras do ponteiro global. O modo mantém o
ponteiro inicial para restaurar seu lock; Off, SetFrequency e On relêem o global.
Os testes incluem uma troca controlada desse ponteiro durante a cadeia.

## VSync-off e limpeza PCM

O guard unsigned `lock - 0x68736D53 <= 1` aceita somente o valor mágico ou
o valor mágico mais um. A rotina soma 10 ao lock e então:

1. Lê os words DMA em `0x040000C4` e `0x040000D0`. Para cada word com bit 25 ligado,
   escreve `0x84400004` nesse endereço.
2. Grava halfword `0x400` em `0x040000C6` e `0x040000D2`.
3. Zera exatamente **792 words / 3.168 bytes**, de `sound+0x350` até `sound+0xFAF`.

O original usa `CpuSet` com controle `0x05000318` e uma origem zero na pilha.
Os flags `CS_FILL32` estão definidos como `5<<24` na
[libtonc do devkitPro](https://github.com/devkitPro/libtonc/blob/master/include/tonc_bios.h).
O nativo resolve essa operação fixa com escritas de 32 bits pelo host, sem
executar ARM, chamar BIOS ou introduzir um binding genérico de CpuSet.

## Validação

O corpus passou em **1.714 cenários e 1.810 execuções**:

- Todos os 256 parâmetros de reverb e todos os valores de canais/volume.
- Todos os bytes do registrador de bias, as 16 combinações dos bits de controle
  e os bits ignorados do modo.
- Os 16 índices de frequência, condições DMA, guards de lock e seis posições
  de SoundInfo em EWRAM/IWRAM.
- 48 casos de releitura do ponteiro global.
- 32 ciclos de modo → Off → On → novo modo, com estado carregado entre chamadas.
- Oito controles dirigidos e 512 casos aleatórios determinísticos.

RAM, PCM e acessos ordenados coincidiram com a execução da ROM e com um modelo
independente de estado. Foram observadas **3.867 escritas em I/O**, **1.041 leituras
de VCOUNT** e **514 preenchimentos de referência**. A cobertura chegou a **195
instruções**: 68 de modo, 46 de Off e 81 de SetFrequency/On.

**A referência usa um modelo controlado de CpuSet, não uma imagem da BIOS.**
O hook confere SWI, controle, alinhamento e origem zero; materializa 792 escritas.
As instruções da ROM do jogo são executadas em Unicorn ARM926. O I/O é um espelho
plano, e VCOUNT usa sequências finitas. Esses resultados não validam ciclos,
efeitos reais de DMA/timer/FIFO, temporização real ou som audível.

Os gates GBA comparam todo o `.text` no endereço original, incluindo literais e
padding, sem máscaras ou recortes e sem alterar assembly gerado. Passaram os
**242 alvos C e 22 assembly**, os **21 corpora de áudio** e **33 testes direcionados**:
18 próprios desta etapa e 15 de frequência reexecutados após ampliar o verificador.
A suíte geral contém **416 testes** e não foi reexecutada integralmente; a última
execução completa continua sendo a de 290 testes da etapa de instrumento.

Fontes: [C nativo](../port/audio/audio_helpers.c), [API](../port/include/audio_helpers.h),
[C GBA do modo](../src/audio_mode.c), [C GBA de Off](../src/sound_vsync_off.c),
[verificador](../tools/verify_sound_mode.py), [modelo de referência](../tools/verify_sound_frequency.py)
e [testes](../tests/test_sound_mode_native.py).

```powershell
.\.venv\Scripts\python.exe tools\match.py --target audio_mode
.\.venv\Scripts\python.exe tools\match.py --target sound_vsync_off
.\.venv\Scripts\python.exe tools\verify_sound_mode.py --cases 512
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_sound_*native.py' -v
```

Evidências: `build/native_sound_mode_validation/report.json`,
`build/matching/audio_mode/report.json`, `build/matching/sound_vsync_off/report.json`,
`build/next/sound_mode/tests_target.log` e `build/verification.json`.

A continuação integrou [Sound_Initialize, Sound_Extend e Dummy](sound_initialization_native.md),
chegando a 54 serviços nativos, com 51 testes direcionados e os 22 corpora
reexecutados. A continuação de [CGB](cgb_native.md) ligou Stop, Update e Volume,
chegando a 57 serviços. O [mixer PCM](pcm_mixer_native.md) foi integrado depois,
chegando a 59 endereços. O jogo Windows ainda precisa de backend, recursos, saves, gameplay e
validação durante a execução completa. Veja o [estado do port](port_status.md).
