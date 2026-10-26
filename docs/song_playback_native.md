# Início, parada e música original no Windows

Etapa de 22/10/2026, ROM USA BDVE rev0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

As quatro APIs agora têm implementações C nativas e bindings no despachante:

| Serviço | Endereço USA | C GBA recompilado e comparado |
|---|---|---:|
| `Music_StartSong` | `0x0810ADB8` | 44 bytes |
| `MusicPlayer_Start` | `0x0810B4EC` | 228 bytes |
| `MusicPlayer_Stop` | `0x0810B5D0` | 64 bytes |
| Parada global | `0x0810AEEC` | 44 bytes |

Os **380 bytes completos** continuam iguais à ROM, incluindo pools e padding.
Essas funções já pertenciam aos 242 alvos C; não aumentam os totais de matching.
O port passa de 62 para **66 endereços atendidos em C nativo**.
O assembly GBA de `MusicPlayer_Update` permanece separado do C para Windows.

## Comportamento e dados

O início conserva a seleção do player, o bloqueio mágico, a prioridade, a parada
dos canais anteriores, a inicialização das trilhas e o modo solicitado no header.
A parada individual conserva os bits de estado, pausa o player e limpa seus canais;
a global visita os quatro players.

A tabela em `0x08A69068` contém **970 entradas**, terminando em `0x08A6AEB8`,
endereço do header vazio compartilhado. Há 192 entradas com trilhas e 194 headers
distintos, incluindo headers sem trilhas. A tabela mistura músicas e efeitos.
`build/native_song_validation/catalog.json` registra os dados e ponteiros de cada entrada.

`Dbaa_AudioRuntimeStartSong` aceita IDs de 0 a 969.
`Dbaa_AudioRuntimeStopPlayer` aceita índices de 0 a 3.
`Dbaa_AudioRuntimeStopAll` executa a parada global.
Argumentos inválidos são rejeitados pelo host. A API GBA original continua
truncando o ID para 16 bits, comportamento validado separadamente.

## Comparação com a ROM

`tools/verify_song_playback.py` passou em **2.880 cenários**:
970 IDs da tabela, prioridades, limites de trilhas, modos, bloqueios, truncamento,
parada e acessos de modulação/volume/pitch PCM/CGB.
Foram cobertas as **172 instruções executáveis** das quatro APIs.

A música **ID 1**, header `0x08D0E854`, usa 14 trilhas e o primeiro player.
Uma execução de **1.800 quadros** inclui início no quadro 0, parada no 600,
reinício no 608 e parada global no 1.792. A cada quadro foram comparados:

- RAM/I/O persistentes e a sequência de leituras/escritas;
- blocos PCM8 produzidos e consumidos, byte a byte;
- seleção do bloco DMA e conversão independente por timestamps para PCM16.

Coincidiram **475.200 amostras estéreo PCM8 consumidas** e **1.446.569 amostras
estéreo a 48 kHz**. O SHA-256 do PCM16 é:

`454d7c15b0f31c978ba11c2beb0dadc02152253aed456fb98efb88583b24f43c`.

A execução real revelou diferenças de ordem de acesso nos auxiliares de volume,
prioridade e modulação. O C foi corrigido; testes de mutação preservam essas
regressões. A DLL nativa não executa ARM nem delega rotinas desconhecidas à ROM.

## Dispositivo Windows

`tools/verify_song_device.py` compara o WAV exportado integralmente com o PCM
derivado da ROM e toca a mesma sequência via WASAPI compartilhado por eventos.
O checksum FNV-1a dos buffers submetidos coincide:
`051f790bb9359803`.

O teste entregou **1.446.569 frames estéreo em 30,1576599 segundos**, sem underrun,
overflow, falhas ou esvaziamento do endpoint. O maior atraso QPC foi 16,1877 ms.
O formato da aplicação é PCM16 estéreo/48 kHz; o endpoint usa estéreo/48 kHz/32 bits.
Não houve captura de loopback nem confirmação humana de escuta.

Não houve atividade CGB nos 1.800 quadros observados dessa música. Isso permite
testar seu PCM sem a síntese PSG ainda pendente; não demonstra que todo o catálogo
dispensa PSG. A comparação não cobre o circuito analógico do GBA.

Uma varredura adicional, somente nativa, exercitou as **192 entradas com trilhas**
em **227.040 quadros**, sem falhas de memória ou chamadas desconhecidas.
Ela encontrou atividade CGB em nove músicas: IDs 4, 7, 11, 13, 14, 16, 19, 21 e 23.
Isso confirma a necessidade de implementar PSG para completar o áudio do jogo.
Esse levantamento está em `build/next/song_playback/catalog_native_exercise.json`;
ele não acrescenta uma comparação de PCM contra a ROM para todo o catálogo.

## Reproduzir

```powershell
.\.venv\Scripts\python.exe tools\build_windows_audio.py
.\build\windows_audio\dbaa_audio.exe --rom .\baserom.gba --song 1 --frames 1800
```

Para repetir a sequência usada na prova, acrescente:

```powershell
--stop-at 600 --restart-at 608 --stop-all-at 1792
```

`--wav arquivo.wav` exporta offline. `--demo` continua sendo a onda sintética
e não pode ser usado junto com `--song`. O ganho padrão 64 é da aplicação
e preserva os bytes PCM8 do mixer.

## Limite desta entrega

O executável continua sendo o subsistema de áudio. A inicialização completa,
janela/vídeo, controles, gameplay, saves e validação das fases ainda precisam
ser integrados. O [estado do port](port_status.md) acompanha esse trabalho.
PSG, comportamento geral dos dispositivos, hotplug e correção de deriva entre
clocks em sessões longas também permanecem pendentes.

A auditoria final revalidou os **265 alvos GBA**, os **25 corpora nativos** e a
suíte completa de **514 testes**, além dos 13 testes novos desta etapa. São
389 entradas de fonte/configuração congeladas. As evidências consolidadas estão
em `build/next/song_playback/audit.json` e `build/verification.json`.
