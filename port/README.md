# Base nativa

A [saída PCM Windows](../docs/windows_audio_output.md) está implementada em
`native/audio_runtime.c` e `windows/audio_main.c`. O executável de áudio usa
WASAPI, fila, VSync e QPC. Existe também uma prévia nativa da primeira fase;
veja a [integração e suas limitações](../docs/native_game_integration.md).
O port completo ainda não está concluído.

```powershell
.\.venv\Scripts\python.exe tools\build_windows_audio.py
.\build\windows_audio\dbaa_audio.exe --rom .\baserom.gba --demo --frames 600
```

`--demo` ativa uma onda sintética baixa; `--wav arquivo.wav` exporta offline.
A configuração normal inicia os players pausados. `--song 1` toca a música
original de ID 1; `--stop-at`, `--restart-at` e `--stop-all-at` agendam controles
por quadro. Veja a [validação das APIs e música original](../docs/song_playback_native.md).
O PSG/CGB e o WASAPI já estão ligados à prévia integrada. O
[build Windows](../docs/windows_native_build.md) usa uma
[thread de apresentação](../docs/async_window_native.md) separada do produtor
de áudio. A mistura final das músicas com CGB ainda requer comparação com a ROM.

`audio/music_player_update.c` é a primeira rotina com implementação para o host e comparação
funcional contra a rotina ARM original. A interface está em `include/music_player.h`.

`DbaaMusicHost` mantém endereços de dados GBA como `uint32_t` e recebe callbacks do host:

- `read(user, address, width)`: lê inteiro little-endian de 1, 2 ou 4 bytes.
- `write(user, address, value, width)`: armazena os bits inferiores dessa largura.
- `call(user, target, a0, a1, a2)`: resolve o endereço de rotina para uma implementação C nativa,
  retornando o resultado dos serviços com retorno definido; resultados void são ignorados. Deve aceitar alvos Thumb com bit 0 ativado.

O código não emula CPU. A validação usa Unicorn apenas como referência para comparar a ROM
e executar auxiliares ainda não ligados a implementações C nativas. O backend definitivo
precisa fornecer esses bindings, memória, recursos e dispositivos do jogo.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_player.py --cases 1000
```

O comando compila uma DLL de teste Windows x64 em `build/native_music_validation/`.
Ela não é o executável do jogo. O assembly GBA fica separado em `asm/music_player_update.s`;
seu matching não é atribuído ao C nativo. Veja o
[relatório da rotina](../docs/music_player_update_hybrid.md) e o
[estado do port](../docs/port_status.md).

`audio/audio_helpers.c` e `include/audio_helpers.h` acrescentam cópia/validação da tabela,
limpeza, remoção, fim/parada de trilha, wrappers com callbacks em RAM, fade e volume/pitch.
O player usa `Dbaa_AudioCall` para resolver 66 endereços em C e só delega alvos restantes
a `host->call`. O backend do jogo não precisa executar ARM para esses 66 endereços.

```powershell
.\.venv\Scripts\python.exe tools\verify_audio_helpers.py --cases 64
```

A validação dos auxiliares contém 768 cenários, incluindo leituras observadas, sentinelas e
callbacks substituídos. O [relatório da etapa](../docs/audio_helpers_matching.md) distingue
os 80 bytes C e 76 assembly adicionados ao matching dos testes de comportamento nativo.

Os cálculos PCM (`0x0810AC90`) e CGB (`0x0810B78C`) também usam C nativo. O produto
PCM usa `uint64_t`, e o CGB conserva o arredondamento aritmético dos períodos negativos.
A interface lê as tabelas da ROM pelo host; esses valores continuam sendo passos/períodos
do driver original. Mixer e saída PCM foram implementados nas continuações;
a síntese PSG/CGB continua pendente.

```powershell
.\.venv\Scripts\python.exe tools\verify_audio_frequency.py
```

Esse corpus contém 237.568 comparações com a execução original, incluindo três varreduras
completas de 256 notas por 256 ajustes finos. Veja [frequências PCM/CGB](../docs/audio_frequency_matching.md).

`Dbaa_SoundUpdateTrack` resolve `0x0810AA00` no despachante: lê parâmetros opcionais da nota,
seleciona canais PCM/CGB, resolve instrumentos divididos/percussão e instala envelope, volume
e frequência. `Dbaa_MusicClearModulation` resolve `0x0810AC40`. O corpus adicional usa o
callback real de notas em 128 execuções do player, além dos casos isolados.

```powershell
.\.venv\Scripts\python.exe tools\verify_sound_update_track.py --cases 1024
```

Veja [notas e seleção de canais](../docs/sound_update_track_hybrid.md). O matching dos
512 bytes GBA pertence ao assembly; o C nativo é validado por comportamento.

`Dbaa_MusicEventEndTie` resolve `0x0810AC00` (comando `0xCE`, slot 29). Reaproveita a nota
anterior quando o parâmetro é omitido e marca apenas o primeiro canal elegível para liberação,
comparando a nota original em `channel+0x11`. Os elos da lista e o restante do canal são preservados.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_end_tie.py --cases 512
```

O corpus passou em 1.472 cenários, incluindo 64 execuções do player criando e liberando uma
nota sustentada. Veja [término de notas sustentadas](../docs/music_end_tie_hybrid.md).

`Dbaa_MusicEventLfoSpeed` (`0x0810AC68`, evento `0xC2`) e `Dbaa_MusicEventModDepth`
(`0x0810AC7C`, evento `0xC4`) consomem um byte com `Dbaa_MusicReadCommandByte`
(`0x0810AC5C`). Parâmetro zero limpa modulação e fase; os demais valores preservam esses
campos. O leitor incrementa o cursor antes de ler o byte, inclusive quando há sobreposição.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_modulation.py --cases 512
```

Os três bindings passaram em 2.576 cenários, incluindo 128 execuções do player com os
comandos reais. São 12 bytes C/GNU C e 40 bytes assembly com matching GBA separado.
Veja [LFO e modulação](../docs/music_modulation_commands.md).

`Dbaa_MusicEventMemoryAccess` (`0x0810BFAC`, evento `0xB9`) implementa operações de bytes e
comparações com saltos condicionais. `Dbaa_MusicEventExtended` (`0x0810C104`, evento `0xCD`)
despacha os 12 slots estendidos observados. GOTO, fim, amostra e setters de instrumento/eco
resolvem em C os 14 novos endereços, elevando o despachante a 31.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_memory.py --cases 512
```

O corpus passou em 2.042 cenários, com 128 execuções do player e 264 instruções originais
cobertas. Os novos 664 bytes GBA têm matching C/GNU C. Veja [memória e comandos estendidos](../docs/music_memory_commands.md).

Os [padrões, retornos e repetições](../docs/music_pattern_commands.md) acrescentam quatro
serviços C (`0x0810A548`, `0x0810A574`, `0x0810A590`, `0x0810A5A4`), totalizando 35 endereços.
A validação própria compara 4.056 cenários com a ROM, incluindo 384 execuções do player real.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_patterns.py
```

[Prioridade e tempo](../docs/music_priority_tempo_commands.md) acrescentam `0x0810A5D4` e
`0x0810A5E0`, elevando o despachante a 37 serviços C. O corpus compara 3.525 cenários,
incluindo 128 sequências de duas atualizações do player real.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_priority_tempo.py
```

A [transposição](../docs/music_key_shift_command.md), em `0x0810A5F4`, acrescenta o 38º serviço C.
O corpus passou em 2.385 cenários, incluindo 512 sequências com notas novas e existentes.

```powershell
.\.venv\Scripts\python.exe tools\verify_music_key_shift.py
```

O [comando de instrumento](../docs/music_voice_command.md), `0x0810A608`, acrescenta o
39º serviço C nativo. Copia o timbre em três acessos ordenados, preservando o filtro da
ROM e o índice bruto. A validação passou em 2.283 cenários, com 320 sequências do player
e 384 atualizações; inclui PCM/CGB, instrumentos agrupados/rítmicos e troca durante notas
ativas. O build GBA usa assembly separado com 48/48 bytes idênticos; o candidato ARM C
permanece não correspondente. Na etapa de instrumento, 27/36 slots tinham binding nativo;
a continuação de volume abaixo atualiza esse inventário.

O [comando de volume](../docs/music_volume_command.md), `0x0810A638`, acrescenta o
40º serviço C nativo. Usa o leitor filtrado, grava `track+0x12` e solicita atualização
de volume pela máscara `0x03`. Passou em 2.385 cenários, com 512 sequências e 1.024
atualizações do player. O GBA usa assembly separado com 20/20 bytes idênticos; os
candidatos ARM C continuam diferentes em cinco bytes. Os nove testes próprios e os
doze corpora de áudio passaram nesta etapa; a última suíte geral é a de 290 testes da
etapa anterior. Na etapa de volume, 28/36 slots tinham binding nativo; restavam sete eventos
e a configuração de frequência, além de mixer/backend e integração do jogo.

O [comando de pan](../docs/music_pan_command.md), `0x0810A64C`, acrescenta o 41º serviço C
nativo. Subtrai 64 do parâmetro filtrado, grava `track+0x14` e solicita atualização dos
volumes pela máscara `0x03`. Passou em 2.385 cenários, com 512 sequências e 1.024
atualizações do player. O GBA usa assembly separado com 20/20 bytes idênticos; os
candidatos C ARM têm 24 bytes e oito diferenças. Os doze testes próprios e os treze
corpora de áudio passaram; a última suíte geral é a de 290 testes da etapa de instrumento.
Na etapa de pan, 29/36 slots tinham binding nativo; restavam seis eventos e a configuração
de frequência, além de mixer/backend e integração do jogo.

O [pitch bend](../docs/music_pitch_bend_command.md), `0x0810A660`, acrescenta o 42º serviço C
nativo. Subtrai 64 do parâmetro filtrado, grava `track+0x0E` e solicita atualização do
pitch pela máscara `0x0C`. Passou em 2.483 cenários, com 610 sequências e 1.220
atualizações do player. O GBA usa assembly separado com 20/20 bytes idênticos; os
candidatos C ARM têm 24 bytes e oito diferenças. Os doze testes próprios e os quatorze
corpora de áudio passaram; a última suíte geral é a de 290 testes da etapa de instrumento.
Na etapa de pitch bend, 30/36 slots tinham binding nativo; restavam cinco eventos e a configuração
de frequência, além de mixer/backend e integração do jogo.

O [alcance do bend](../docs/music_bend_range_command.md), `0x0810A674`, acrescenta o 43º
serviço C nativo. Grava o parâmetro filtrado sem sinal em `track+0x0F` e solicita atualização
do pitch pela máscara `0x0C`. Passou em 2.497 cenários, com 624 sequências e 1.248
atualizações do player. O GBA usa assembly separado com 20/20 bytes idênticos; ambos os
candidatos C ARM têm 20 bytes e cinco diferenças. Os doze testes próprios e os quinze
corpora de áudio passaram; a última suíte geral é a de 290 testes da etapa de instrumento.
Na etapa de alcance do bend, 31/36 slots tinham binding nativo; restavam quatro eventos e a configuração
de frequência, além de mixer/backend e integração do jogo.

O [atraso do LFO](../docs/music_lfo_delay_command.md), `0x0810A688`, acrescenta o 44º
serviço C nativo. Grava o parâmetro filtrado em `track+0x1B`, preservando contador,
fase e flags da nota atual. Passou em 2.397 cenários, com 512 sequências, 1.792
atualizações e 33.923 ticks do player. O GBA usa assembly separado com 12/12 bytes
idênticos; ambos os candidatos C ARM têm 12 bytes e cinco diferenças. Os doze testes
próprios e os dezesseis corpora de áudio passaram; a última suíte geral é a de 290
testes da etapa de instrumento. Na etapa de atraso do LFO, 32/36 slots tinham binding nativo;
restavam três eventos e a configuração de frequência, além de mixer/backend e integração do jogo.

O [tipo de modulação](../docs/music_mod_type_command.md), `0x0810A694`, acrescenta o 45º
serviço C nativo. Atualiza `track+0x18` e acrescenta `0x0F` às flags apenas quando
o valor muda. Passou em 3.185 cenários, com 1.044 sequências e 2.088 atualizações.
O GBA usa assembly separado com 24/24 bytes idênticos; ambos os candidatos C ARM
têm 28 bytes e oito diferenças. Os doze testes próprios e os dezessete corpora de
áudio passaram; a última suíte geral é a de 290 testes da etapa de instrumento.
Na etapa de tipo de modulação, 33/36 slots tinham binding nativo; restavam dois eventos e a
configuração de frequência, além de mixer/backend e integração do jogo.

A [afinação](../docs/music_tune_command.md), `0x0810A6AC`, acrescenta o 46º serviço C
nativo. Subtrai 64 do parâmetro filtrado, grava `track+0x0C` e solicita recálculo e
propagação do pitch, sem escalar pelo alcance do bend. Passou em 2.495 cenários,
com 610 sequências e 1.220 atualizações. O GBA usa assembly separado com 20/20
bytes idênticos; ambos os candidatos C ARM têm 24 bytes e oito diferenças.
Os doze testes próprios e os dezoito corpora de áudio passaram; a última suíte
geral é a de 290 testes da etapa de instrumento. Na etapa de afinação, 34/36 slots
tinham binding nativo; restavam PORT e a configuração de frequência,
além de mixer/backend e integração do jogo.

O [PORT](../docs/music_port_command.md), `0x0810A6C0`, acrescenta o 47º serviço C
nativo. Consome seletor cru e valor filtrado e emite uma escrita de largura 1 em
`0x04000060 + seletor`. O host deve preservar ordem, quantidade e largura dos
acessos a I/O e implementar seus efeitos nos dispositivos. Passou em 3.471 cenários,
com 512 sequências reais do player e 3.983 escritas observadas num espelho de I/O.
Isso ainda não valida efeitos de hardware ou saída audível. O GBA usa assembly
separado com 24/24 bytes idênticos; os candidatos C ARM têm 28 bytes e 15/18 diferenças.
Os doze testes próprios e os dezenove corpora de áudio passaram. Após `Sound_Extend`,
Na etapa PORT, 35/36 slots tinham binding nativo; restavam frequência, mixer/backend e integração do jogo.

[Sound_SetFrequency e Sound_VSyncOn](../docs/sound_frequency_native.md) acrescentam
dois bindings, chegando a 49 e cobrindo os 36 slots da tabela. Os cálculos preservam
overflow de 32 bits e divisão signed; o host recebe escritas de timer/DMA com as
larguras originais e deve fazer VCOUNT progredir durante as duas esperas.
Passaram 1.718 cenários e 1.750 execuções com relógio roteirizado e espelho de I/O,
além dos quinze testes próprios e vinte corpora de áudio. Os 164 e 60 bytes do
C GBA foram revalidados e já pertenciam ao total. Naquela etapa ainda faltavam
serviços transitivos, mixer, dispositivos e integração do jogo para produzir áudio jogável.

O [modo e VSync-off](../docs/sound_mode_native.md) acrescentam os bindings 50 e 51.
O modo preserva campos zerados e coordena Off → frequência → On; Off interrompe
DMA conforme o bit de controle e limpa exatamente 792 words PCM. O nativo faz
essa operação fixa em C; a referência modela CpuSet e não usa uma imagem da BIOS.
Passaram 1.714 cenários, 1.810 execuções, 33 testes direcionados e os 21 corpora
de áudio. Os 152 e 124 bytes GBA já estavam no matching. A inicialização e extensão
foram ligadas na continuação descrita abaixo.

A [inicialização e extensão](../docs/sound_initialization_native.md) acrescentam
os bindings 52 a 54, incluindo Sound_Dummy. O C nativo limpa 4.016 bytes de
SoundInfo/PCM e 256 bytes CGB, copia a tabela e aplica seus nove patches,
preservando ordem de I/O, guards e ponteiros Thumb. Passaram 1.008 cenários,
1.328 execuções, 51 testes direcionados e os 22 corpora de áudio. Os 532 bytes
GBA já estavam no matching C. Na etapa de inicialização, Cgb_Stop e Cgb_Update foram apenas instalados.
A continuação abaixo os executa em C nativo.

Os [serviços CGB](../docs/cgb_native.md) acrescentam os bindings 55 a 57:
Dbaa_CgbStop, Dbaa_CgbUpdateVolume e Dbaa_CgbUpdate. A atualização mantém os
envelopes, transferências word de wave RAM, arredondamento por bias, roteamento
e escritas repetidas de trigger. Passaram 7.717 cenários, 7.925 execuções, 69
testes direcionados e os 23 corpora de áudio. Os 1.284 bytes GBA já estavam no
matching C. Naquela etapa o mixer ainda estava pendente; sua integração vem abaixo.
Dispositivos, saída de áudio e jogo integrado continuam pendentes.

O [mixer PCM](../docs/pcm_mixer_native.md) acrescenta o kernel C
`include/pcm_mixer_impl.h` e liga `0x0810A084`, junto à entrada do player
`0x0810A724`, ao despachante: 59 endereços resolvidos. O C preserva os bytes
PCM, envelopes, reverb, loops, ganho e interpolação. Passaram 1.884 cenários,
2.436 execuções, 87 testes direcionados e os 24 corpora de áudio. O build GBA
usa assembly separado com 1.064 bytes exatos; o C ARM de 1.532 bytes é excluído
do matching. O mixer já gera buffers; faltam saída de som, tempo/dispositivos,
inicialização de alto nível e integração do jogo. A continuação abaixo liga esse nível.

A [inicialização de alto nível](../docs/audio_startup_native.md) liga
`Dbaa_AudioInitialize` (`0x0810AD34`), `Dbaa_AudioMain` (`0x0810ADAC`)
e `Dbaa_MusicPlayerOpen` (`0x0810B474`), totalizando 62 bindings.
A cópia de 1.024 bytes para RAM faz parte do estado; o mixer nativo executa C.
São quatro players, 27 trilhas e 36 slots de comandos configurados pela sequência
real. Passaram 1.288 cenários, 1.392 execuções, 96 atualizações pelo wrapper,
108 testes direcionados e os 25 corpora de áudio. Os 252 bytes C GBA já eram
contados e foram revalidados. Naquela etapa ainda faltavam APIs de músicas e a saída de som.

A [integração do áudio ao jogo](../docs/game_audio_native.md) liga 66 serviços,
PSG, mistura digital e WASAPI ao executável nativo Windows. O consumidor mantém
os 1.446.569 pares estéreo do corpus original; o jogo passou em 5.000 quadros com
janela e 4.018.027 pares preservados no dispositivo. Ainda faltam estabilidade
longa, paridade do jogo completo, save de campanha e cobertura de fases/modos.

A [EEPROM do jogo](../docs/eeprom_native.md) agora usa seus 512 bytes reais.
O arquivo inicial coincide integralmente com a ROM e é aceito por ela; também
foram verificados reboots e substituição protegida do save no Windows. O build
atual fica em `build/next/game_save`; estabilidade de áudio e gravação de
progresso real da campanha permanecem pendentes.
