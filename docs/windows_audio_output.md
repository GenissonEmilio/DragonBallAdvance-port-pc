# Saída PCM e temporização no Windows

O projeto agora tem um **executável nativo de áudio**, `build/windows_audio/dbaa_audio.exe`,
com saída **WASAPI compartilhada por eventos**, fila limitada, conversão estéreo PCM16
a 48 kHz e cadência de frames baseada em **QPC e waitable timer**.
Esse executável exercita o subsistema de áudio; o jogo completo ainda não é jogável.

O [runtime C](../port/native/audio_runtime.c) carrega a ROM USA fornecida localmente,
mantém EWRAM/IWRAM/I/O e chama a inicialização C, o serviço VSync e
`Dbaa_AudioMain → Dbaa_SoundMain`. Não executa instruções ARM no processo nativo.
A [plataforma Windows](../port/windows/audio_main.c) fornece dispositivo, espera e loop.
Os fontes anteriores de áudio e os **62 bindings** foram preservados.

## Executar

Na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe tools\build_windows_audio.py
.\build\windows_audio\dbaa_audio.exe --rom .\baserom.gba --demo --frames 600
```

`--demo` ativa uma **onda triangular sintética baixa**, passada pelo mixer C original
reconstruído. Ela não é uma música do jogo. Sem essa opção, os players saem pausados
da inicialização e a saída fica silenciosa até que o código chamador configure áudio.
O ganho padrão é 64/256, aplicado depois do PCM bruto; o volume do dispositivo não é alterado.

```powershell
.\build\windows_audio\dbaa_audio.exe --demo --frames 180 --wav .\build\windows_audio\demo.wav
.\build\windows_audio\dbaa_audio.exe --demo --frames 1800 --report .\build\windows_audio\run.json
```

`--wav` seleciona explicitamente o modo offline. Falha ao abrir o dispositivo retorna
erro; não há troca silenciosa para WAV. `--mode 1..12` seleciona frequência, `--gain 0..256`
define ganho da aplicação e Ctrl+C encerra a execução. A ROM é verificada por tamanho
e CRC32 `7D7306DF` no executável; os verificadores exigem também o SHA-1 USA conhecido
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

## Clock e sequência dos buffers

O relógio virtual usa **16.777.216 ciclos/s**, **1.232 ciclos/linha** e
**280.896 ciclos/frame**, ou aproximadamente **59,7275 frames/s**.
Todos os 12 tamanhos da tabela da ROM dividem exatamente esse período:

| Amostras/frame | Ciclos/amostra (Timer0) |
|---:|---:|
| 96 | 2926 |
| 132 | 2128 |
| 176 | 1596 |
| 224 | 1254 |
| 264 | 1064 |
| 304 | 924 |
| 352 | 798 |
| 448 | 627 |
| 528 | 532 |
| 608 | 462 |
| 672 | 418 |
| 704 | 399 |

O serviço VSync é a contraparte C de `0x0810A6D8`: verifica o lock, decrementa/recarrega
o contador e mantém a sequência de controles DMA1/DMA2. Esse serviço novo do host tem
**validação comportamental**, sem novo matching C GBA. O original usa dois literais em
um pool compartilhado posterior, além dos literais locais.

Em cada tick, o runtime executa VSync e depois o wrapper/mixer. O bloco consumido
é `N × (período − contador)`. O mixer escreve o próximo bloco, voltando ao início
quando o contador é 1. A saída preserva essa **antecedência de um bloco**; o primeiro
bloco depois da inicialização é silêncio.

O plano A segue os bits de roteamento/volume DirectSound e, no modo `0xA90E` do jogo,
alimenta o canal direito; o plano B alimenta o esquerdo. A conversão usa retenção de
amostra com fase inteira, ganho e clamp PCM16. O PCM8 original não é modificado.
O número acumulado de amostras de saída é:

```text
floor(frames × 280896 × 48000 / 16777216)
```

Os deadlines QPC também vêm do índice absoluto do frame, sem acumular arredondamento
de sleeps. Leituras de VCOUNT em esperas de configuração avançam uma linha virtual;
isso permite terminar as esperas leave/enter originais. Não é um modelo de ciclos
por instrução ARM7TDMI.

## Saída e falhas observáveis

WASAPI usa `GetCurrentPadding` e `GetBuffer/ReleaseBuffer`, com evento do endpoint.
Há preenchimento inicial, fila de 16.384 frames estéreo e drenagem limitada no encerramento.
O código nunca sobrescreve áudio pendente: overflow produz erro. Se o consumidor pedir
mais amostras do que há na fila, a falta é preenchida com zero e contabilizada.

O loop registra esvaziamentos do endpoint separadamente das faltas da fila. Recupera
até oito frames atrasados sem descartar ticks; atraso maior produz erro explícito.
Timers de alta resolução são usados quando disponíveis, com fallback para waitable
timer normal, sem mudar a resolução global do sistema.

Os HRESULTs são propagados, os recursos COM/handles são liberados, e invalidação do
dispositivo termina com erro. Reabertura automática após hotplug ainda não foi implementada.
O relatório mede o relógio do stream e o tempo de execução da API, não a latência até o alto-falante.

## Evidência

Passaram **160 sequências e 3.200 frames**, com **8.038 execuções da ROM**:

- **1.166.400 amostras estéreo PCM8 de origem** coincidiram nos dados da RAM e
  nos blocos produzidos/consumidos.
- RAM/I/O e acessos ordenados do VSync e wrapper coincidiram com a ROM.
- **2.571.520 frames estéreo a 48 kHz** coincidiram com um cálculo separado por
  timestamps, cobrindo canais, ganho, clipping, loops, reverb e pausa/retomada.
- **1.316 cenários de VSync** cobriram todas as contagens byte, locks, períodos e
  controles DMA, alcançando as **33 instruções** do corpo original.
- **30.018 pontos de deadline QPC** coincidiram com a razão inteira, incluindo
  índices além de 24 horas e frequências de contador diferentes.
- Uma execução **virtual** de **36.000 frames** gerou e consumiu **28.931.396 frames
  estéreo**, em 108.000 pacotes, sem deriva de contagem ou falhas de fila.

O [verificador PCM](../tools/verify_windows_audio.py) usa Unicorn como referência
externa. Cópia/fill BIOS e I/O seguem os modelos já documentados; a pilha morta
`0x03007000..0x030077FF` é excluída, e leituras de literais do código copiado não
entram no trace de dados. O PCM16/48 kHz é uma política do host validada separadamente;
não existe esse formato na ROM.

O [teste explícito de dispositivo](../tools/verify_windows_audio_device.py) executou:

| Teste WASAPI | Frames GBA | Resultado |
|---|---:|---|
| Normal, aproximadamente 30 s | 1800 | 1.446.569 frames estéreo consumidos; zero faltas na fila, zero overflow e zero esvaziamentos do endpoint |
| Pausa forçada de 50 ms | 120 | Um esvaziamento detectado e dois frames de recuperação; nenhum tick descartado |

No teste normal, o intervalo medido da API foi **30,1344 s**, frente a **30,1369 s**
ideais. O maior atraso de um tick foi **17,684 ms**; houve um frame de recuperação.
O endpoint local informou **48 kHz, estéreo, 32 bits**, e seu relógio avançou.
Essas medidas são do teste desta máquina, sem garantia de prazo rígido do Windows.
Não houve gravação de loopback, alteração de volume global nem confirmação humana
de escuta física.

Os **10 testes novos** passaram, incluindo mutações de contador, bloco DMA, canais,
clock de conversão, largura de registrador, deadline e preenchimento de underrun.
Há **501 testes descobertos**. A suíte geral não foi reexecutada; os 108 testes e
25 corpora da etapa anterior permanecem evidência histórica sobre os mesmos fontes.
Os 379 arquivos daquela etapa foram conferidos e continuam inalterados.

O total GBA permanece **242 alvos C/GNU C + 23 assembly = 265 alvos e 36.576 bytes**.
Os arquivos e imagens GBA anteriores foram rechecados; não houve nova recompilação
geral nem novos bytes de matching nesta etapa.

```powershell
.\.venv\Scripts\python.exe tools\verify_windows_audio.py
.\.venv\Scripts\python.exe tools\verify_windows_audio_device.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_windows_audio.py -v
```

Evidências: `build/native_windows_audio_validation/report.json`,
`build/windows_audio_device_validation/report.json`,
`build/next/windows_audio/tests_target.log`, `build/next/windows_audio/audit.json`
e `build/verification.json`. Os fontes estão na [API do runtime](../port/native/audio_runtime.h),
no [build](../tools/build_windows_audio.py) e nos [testes](../tests/test_windows_audio.py).

## Próxima fronteira

As [APIs de seleção/início/parada](song_playback_native.md) e a reprodução de uma
música original foram integradas na continuação. Ainda faltam
**síntese dos quatro canais PSG/CGB**; comportamento geral de FIFO/DMA/timers/IRQ;
recuperação de dispositivo e controle de deriva entre clock de hardware e QPC
em sessões longas. O modelo atual cobre a sequência PCM/Timer0 normal do driver.
Não reproduz o circuito analógico, filtro/bias do DAC ou toda a máquina GBA.

O loop entregue é de áudio. A ligação ao loop completo do jogo, janela/vídeo,
controles, recursos, saves e gameplay continuam pendentes. A abertura ainda não
roda como jogo Windows. Veja o [estado do port](port_status.md).

Referências de API e constantes: [WASAPI Initialize](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclient-initialize),
[renderização](https://learn.microsoft.com/en-us/windows/win32/coreaudio/rendering-a-stream),
[flags de conversão](https://learn.microsoft.com/en-us/windows/win32/coreaudio/audclnt-streamflags-xxx-constants),
[QPC](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps),
[timer](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createwaitabletimerexw),
[clock GBA](https://github.com/mgba-emu/mgba/blob/master/include/mgba/internal/gba/gba.h)
e [período de vídeo](https://github.com/mgba-emu/mgba/blob/master/include/mgba/internal/gba/video.h).
