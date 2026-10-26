# Áudio ligado ao jogo nativo

O executável experimental em `build/next/game_audio/bin/dbaa_game.exe` executa
o jogo em C, com o mixer reconstruído, o PSG independente e saída WASAPI. As
APIs de início/parada de músicas estão na ponte de 66 serviços de áudio.
Nenhum interpretador ARM/Thumb é compilado nesse executável. A ROM local
continua necessária para os recursos, tabelas e a geração do código.

## Comparações independentes

| Camada | Resultado | Limite da conclusão |
|---|---|---|
| Código GBA | 265 alvos, 36.576 bytes exatos | Não inclui as traduções C geradas nem o componente PSG |
| Produtor da música 1 | 1.800 quadros; RAM, I/O, barramento e PCM8 iguais à ROM | Corpus específico, sem vozes CGB ativas |
| Consumidor do jogo | 1.446.569 pares PCM16/48 kHz iguais ao corpus imutável acima | Usa os buffers desse produtor, com o centro DAC pós-BIOS em 512 |
| PSG | 160.000 amostras digitais e 1.490 escritas iguais ao I/O/scheduler original do mGBA | Sem execução de ROM/CPU ou medição analógica |
| Virada do relógio PSG | 4.040 observações atravessando `2^32` ciclos, nas quatro resoluções SOUNDBIAS | Mesma referência digital independente |
| Mistura digital | 150.528 casos e 37.632 chamadas à mistura original do mGBA | Roteamento, proporção de volume e saturação DAC; não é matching de código GBA |

O PCM16 do corpus tem SHA-256
`454d7c15b0f31c978ba11c2beb0dadc02152253aed456fb98efb88583b24f43c`
e FNV-1a64 `051f790bb9359803`. Os relatórios ficam em
`build/native_game_audio_validation`, `build/native_psg_bias_validation`,
`build/native_psg_wrap_validation` e `build/native_digital_mixer_validation`.

O teste de dispositivo compara duas execuções do jogo com os mesmos arquivos
iniciais e entradas: uma offline e outra pelo WASAPI. Ele exige os mesmos
quadros efetivamente executados, estado resumido, ciclos, PCM completo, imagem
final e saves. Confere também quantidade e hash dos bytes submetidos pelo
worker ao WASAPI. Isso demonstra a preservação do PCM nativo na saída digital;
não demonstra que todo o áudio do jogo já coincide com uma execução da ROM.

## Integração e temporização

`port/windows/game_audio.c` recebe o relógio do runtime e as escritas de I/O
com sua largura original. Depois do VBlank de áudio ele localiza o bloco PCM
que o driver original está consumindo. A amostragem usa um relógio racional de
48 kHz, intervalo fechado nas bordas do timer e ganho 64. O PSG acompanha os
eventos de hardware e as mudanças de resolução SOUNDBIAS.

`port/audio/digital_mixer.c` aplica o roteamento dos dois FIFOs e do PSG,
saturação de dez bits em torno de SOUNDBIAS e conversão final para PCM16.
`port/windows/wasapi_sink.c` mantém COM e as interfaces WASAPI em um worker,
com fila, eventos, pré-buffer, drenagem e diagnóstico. O backend Win32 ajusta
gradualmente seu relógio usando a ocupação dessa fila, sem reamostrar,
duplicar ou descartar o PCM gerado pelo jogo.

O worker pede a classe `Pro Audio` do
[MMCSS do Windows](https://learn.microsoft.com/en-us/windows/win32/procthread/multimedia-class-scheduler-service)
e restaura a prioridade ao terminar. O diagnóstico registra essa ativação,
ocupação do endpoint, intervalos entre blocos e esvaziamentos da fila. A
thread do jogo também pede a classe `Games`. Após a correção da EEPROM, uma
execução anterior registrou três esvaziamentos por atraso do produtor. Com o
MMCSS no produtor passaram sessões de **5.000 e 20.000 quadros** com janela,
zero esvaziamentos e zero erros. A sessão longa entregou **16.072.761 pares
estéreo**, FNV-1a64 `199d7f590635ad76`, iguais aos da execução offline. Estado
resumido, imagem final e saves também coincidiram. Os relatórios ficam em
`build/native_game_timing_device_validation/report.json` e
`build/native_game_timing_long_validation/report.json`. O executável desta
etapa fica em `build/next/game_timing/bin/dbaa_game.exe`. A etapa posterior
corrigiu bloqueios GDI observados no build a partir dos fontes separando a
thread da janela. As sessões de 5.000 e 20.000 quadros também passaram nessa
variante; o [relatório da janela assíncrona](async_window_native.md) descreve
as falhas preservadas e a correção. O build público em `build/windows_native`
usa esse backend.

Os testes de regressão do consumidor alteram deliberadamente a borda do timer,
a rotação DMA e o plano estéreo; os da mistura alteram roteamento, proporção
PSG e saturação. Todos exigem que essas regressões sejam detectadas pelo oráculo.

```powershell
.\.venv\Scripts\python.exe tools\verify_game_audio_pcm.py
.\.venv\Scripts\python.exe tools\verify_digital_mixer.py
.\.venv\Scripts\python.exe tools\verify_native_psg.py --out-dir build\native_psg_bias_validation
.\.venv\Scripts\python.exe tools\verify_psg_wrap.py
.\.venv\Scripts\python.exe -m unittest tests.test_game_audio_pcm tests.test_native_digital_mixer
```

## Trabalho restante

A fidelidade do consumo FIFO durante escritas DMA e a paridade do PCM de uma
sessão completa ainda precisam de referência. Nove músicas CGB passaram em
14.892 quadros de comparação do driver com a ROM: estado, operações de memória
e buffers PCM8 iguais, usando o modelo isolado de I/O. Isso ainda não compara
a síntese PSG e a mistura final dessas músicas. Mudança de dispositivo e suspender/retomar
permanecem pendentes. Não houve confirmação humana de escuta
nem medição analógica. Vídeo, estado, combate, colisões, persistência dos saves,
fases, chefes e modos continuam no escopo do port completo.
