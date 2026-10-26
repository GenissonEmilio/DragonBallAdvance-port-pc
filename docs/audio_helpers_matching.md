# Cópia da tabela e auxiliares de áudio: matching e integração nativa

ROM USA `BDVE`, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

`Sound_CopyCommandTable` foi reconstruída com a mesma divisão usada na biblioteca m4a:
**C para o port e assembly separado para reproduzir sua convenção de chamada no GBA**.
A etapa também concluiu dois auxiliares em C com matching e a limpeza de 64 bytes em assembly.

| Região reconstruída | Endereço | Instruções | Literais | Padding | Total | Fonte do matching GBA |
|---|---|---:|---:|---:|---:|---|
| `Audio_Clear64` | `0x0810A4AC` | 22 | 0 | 2 | 24 | Assembly |
| `Audio_UnlinkChannel` | `0x0810A4C4` | 32 | 0 | 0 | 32 | GNU C |
| `MusicEvent_Fine` | `0x0810A4E4` | 46 | 0 | 2 | 48 | GNU C |
| Cópia, leitura filtrada e validador | `0x0810A514` | 46 | 4 | 2 | 52 | Assembly |
| **Total novo** | | **146** | **4** | **6** | **156** | |

Os quatro binários completos concatenados reproduzem **156/156 bytes contínuos** em
`0x0810A4AC..0x0810A548`, sem diferenças. O bloco de 52 bytes inclui três entradas compartilhadas;
ele é contado uma vez, sem duplicar os bytes dos auxiliares.

O agregado agora contém **242 alvos C/GNU C e 33.856 bytes**, mais **23 alvos assembly e
2.720 bytes**: **265 alvos e 36.576 bytes idênticos à ROM**. Há **290 testes validados na última suíte geral (instrumento), sem skips**. O C do port é validado por comportamento, separado do matching ARM.

## Sound_CopyCommandTable e o validador compartilhado

A entrada em `0x0810A514` contém 22 bytes de instruções, seguidos de dois zeros de alinhamento.
Ela guarda o retorno em `r12`, carrega a origem `0x08A67460` e copia **36 words, 144 bytes**.
Cada leitura é passada ao validador em `0x0810A52E`, que recebe endereço em `r2` e valor em `r3`.
Depois a word é escrita, os ponteiros avançam quatro bytes e o contador signed é decrementado.
Ao retornar, `r0` aponta para `destino + 144`.

O literal da origem está em `0x0810A544` e também é usado pelo validador. Por isso a comparação
não se limita aos 22 bytes da entrada: inclui o bloco inteiro de **52 bytes**, seu literal,
o alinhamento, a entrada `Sound_ReadByteFiltered` em `0x0810A52C` e o verificador de endereço.

O verificador aceita um valor quando `endereço >> 25` é diferente de zero. No outro caminho,
compara o endereço com o literal da tabela e testa `endereço >> 14`; quando rejeita, zera `r3`.
Nesta ROM a tabela está em `0x08A67460`, portanto o caminho abaixo de `0x02000000` rejeita os
valores. A reconstrução conserva as instruções originais, incluindo os testes que esse
posicionamento da tabela torna inalcançáveis.

A entrada de leitura **carrega o byte antes de validar o endereço**. O C nativo mantém essa
ordem; a ferramenta diferencial observa as leituras de origem, além dos resultados e da RAM.
Um controle negativo que antecipa a rejeição, mantendo o mesmo valor final zero, precisa falhar
por remover essa leitura observável.

O destino usado pela inicialização é `0x03001C70`. As 36 entradas originais foram conferidas,
incluindo os callbacks de remoção e limpeza nas posições 34 e 35, com bit Thumb ativado.
`Sound_Extend` continua substituindo os mesmos nove slots analisados anteriormente.

## Remoção, encerramento e limpeza

`Audio_UnlinkChannel` só altera a lista quando `channel+0x2C` possui um proprietário. Atualiza
o próximo ponteiro do anterior ou a cabeça da trilha; depois atualiza o anterior do próximo e
zera apenas o proprietário do canal removido. Não apaga os ponteiros de vizinhança do próprio
canal. Isso permite que o chamador continue percorrendo a lista depois da remoção.

O C usa quatro restrições vazias, sem instruções assembly embutidas, com agbcc
`-O2 -mthumb-interwork -fprologue-bugfix`. A última opção já existia no compilador usado e
evita o salvamento desnecessário de LR nessa função folha; o compilador permanece inalterado.

`MusicEvent_Fine` percorre os canais, marca `0x40` nos status cujo `status & 0xC7` é não zero,
remove cada canal pelo auxiliar anterior e zera o status da trilha. Seu C usa o perfil GCC 3.4.6
já registrado e cinco templates vazios para conservar a alocação original. Os **48 bytes**,
incluindo dois de alinhamento, coincidem integralmente. O comando é distinto de `MusicTrack_Stop`,
que zera os canais e a cabeça sem fazer a mesma remoção de vizinhos.

`Audio_Clear64` escreve quatro grupos de quatro words zeradas e preserva `r4` por `r12`,
sem quadro de pilha. Seu assembly contém **24 bytes completos**. A versão C de host escreve
exatamente 64 bytes e retorna o cursor avançado. Os testes usam sentinelas fora da área para
detectar limpeza incompleta ou excessiva.

## Integração ao port nativo

Os fontes estão em `port/audio/audio_helpers.c` e `port/include/audio_helpers.h`.
`MusicPlayer_Update` agora usa `Dbaa_AudioCall`, que resolve estes **62 endereços em C**, incluindo a continuação de
[frequências PCM/CGB](audio_frequency_matching.md):

| Endereço GBA | Serviço nativo |
|---|---|
| `0x0810A084` | Mixer PCM: C nativo e assembly GBA separado |
| `0x0810A724` | Entrada do player C para o callback real do mixer |
| `0x0810AD34` | Inicialização de alto nível do áudio |
| `0x0810ADAC` | Wrapper de frame do mixer |
| `0x0810B474` | Abertura e encadeamento de player |
| `0x0810A4AC` | Limpeza de 64 bytes |
| `0x0810A4C4` | Remoção de canal |
| `0x0810A4E4` | Encerramento de trilha |
| `0x0810A514` | Cópia e validação da tabela |
| `0x0810A548` | Leitor com avanço e filtro de endereço |
| `0x0810A554` | Salto da trilha |
| `0x0810A574` | Chamada de padrão |
| `0x0810A590` | Retorno de padrão |
| `0x0810A5A4` | Repetição de trecho |
| `0x0810A5D4` | Prioridade da trilha |
| `0x0810A5E0` | Tempo base e intervalo do player |
| `0x0810A5F4` | Transposição e flags de pitch |
| `0x0810A608` | Seleção de instrumento |
| `0x0810A638` | Volume da faixa e flags |
| `0x0810A64C` | Pan da faixa e atualização estéreo |
| `0x0810A660` | Pitch bend e atualização das frequências |
| `0x0810A674` | Alcance do bend e atualização das frequências |
| `0x0810A688` | Atraso configurado do LFO |
| `0x0810A694` | Tipo de modulação e recálculo de pitch/estéreo |
| `0x0810A6AC` | Afinação e atualização das frequências |
| `0x0810A6C0` | PORT: escrita de byte no I/O pelo host |
| `0x0810A98C` | Parada da trilha |
| `0x0810AA00` | Processamento de notas e seleção de canais |
| `0x0810AC00` | Término de uma nota sustentada |
| `0x0810AC40` | Reinício da modulação |
| `0x0810AC5C` | Leitura do byte e avanço do cursor |
| `0x0810AC68` | Velocidade do LFO |
| `0x0810AC7C` | Intensidade da modulação |
| `0x0810AC90` | Frequência PCM |
| `0x0810B78C` | Frequência CGB tonal/ruído |
| `0x0810B10C` | Wrapper de remoção, consultando o callback em RAM |
| `0x0810B22C` | Configuração de frequência, timer e espera por VCOUNT |
| `0x0810AFF0` | Extensão CGB e nove patches da tabela |
| `0x0810B134` | Inicialização de SoundInfo, PCM, tabela e frequência |
| `0x0810B2D0` | Modo: reverb, canais, volume, bias e cadeia de frequência |
| `0x0810B3BC` | VSync-off: parada DMA e limpeza PCM |
| `0x0810B834` | Parada CGB com argumento byte e escritas de largura 1 |
| `0x0810B884` | Volume CGB, sustain e pan |
| `0x0810B8EC` | Atualização dos quatro canais CGB e wave RAM |
| `0x0810C224` | Callback vazio inicial (Sound_Dummy) |
| `0x0810B438` | VSync-on: DMA e restauração do lock |
| `0x0810B120` | Wrapper de limpeza, consultando o callback em RAM |
| `0x0810B610` | Fade do player |
| `0x0810B6D8` | Volume/pan/pitch da trilha |
| `0x0810BFAC` | Memória e condições |
| `0x0810C104` | Despachante estendido |
| `0x0810C124` | Fim pelo callback da tabela |
| `0x0810C138` | Ponteiro da amostra |
| `0x0810C180` | Tipo do instrumento |
| `0x0810C194` | Ataque |
| `0x0810C1A8` | Decaimento |
| `0x0810C1BC` | Sustentação |
| `0x0810C1D0` | Liberação |
| `0x0810C1E4` | Volume de eco |
| `0x0810C1F0` | Comprimento de eco |
| `0x0810C1FC` | Comprimento CGB |
| `0x0810C210` | Sweep/pan |

Essas chamadas deixam de ser executadas em ARM no lado nativo da validação. O despachante
aceita endereços pares ou ponteiros Thumb e preserva a consulta aos callbacks instalados em
`0x03001CF8/0x03001CFC`; não presume que eles nunca sejam substituídos. Alvos ainda não
implementados seguem para `host->call`. Os resultados de serviços void não têm significado.

O código usa endereços de dados de 32 bits e callbacks de memória little-endian; não trunca
ponteiros nativos de 64 bits. Os deslocamentos signed são expressos com aritmética definida
para volume, pitch e LFO. Os destinos de cópia/limpeza e as estruturas testadas são alinhados
como os usados pelo jogo; o corpus não modela acessos word desalinhados do ARM7TDMI.

## Verificação

Foram aprovados **768 cenários de auxiliares**, 64 seeds para cada um de 12 caminhos:
cópia, limpeza, remoção, fim, parada, fade, volume/pitch, dois wrappers, filtro, leitura filtrada
e player usando o comando de fim real. Incluem cabeça/meio/cauda de listas, canal sem
proprietário, extremos signed, wrap de contadores, callbacks substituídos e 12 limites de endereço.

Comparam RAM, leituras observadas, efeitos/argumentos dos callbacks e resultados com significado
definido. O checker original devolve seu resultado em `r3`; a API C o devolve normalmente.
Além disso, o player integrado aos novos auxiliares voltou a passar nos **1.128 cenários** e
a percorrer suas **290 instruções originais**. A ferramenta confirma que nenhum dos 59
endereços auxiliares foi delegado ao ARM no lado nativo.

Os 13 testes novos também recompilam mutações deliberadas: elo anterior, máscara de canais,
contagem da cópia, deslocamento do filtro, registradores da limpeza, passo do fade, tamanho
da limpeza, callback em RAM e ordem da leitura. Os testes gerais recompilam todos os alvos C;
o gate assembly verifica separadamente seus 23 alvos e rejeita seções alocadas extras.

```powershell
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match_assembly.py --all
.\.venv\Scripts\python.exe tools\verify_audio_helpers.py --cases 64
.\.venv\Scripts\python.exe tools\verify_music_player.py --cases 1000
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Evidências: `build/matching/summary.json`, `build/assembly_matching/summary.json`,
`build/native_audio_helpers_validation/report.json`, `build/native_music_validation/report.json`,
`build/verification.json` e `build/next/audio_helpers/audit_audio.py`/`audit_audio.json`.

Essa é validação isolada de lógica e CPU com callbacks controlados, não um boot de GBA ou
execução do jogo completo. A continuação de [frequências PCM/CGB](audio_frequency_matching.md) integrou os dois cálculos.
A etapa de [notas e canais](sound_update_track_hybrid.md) integrou o processador de notas,
elevando o total a treze endereços; o [término de notas sustentadas](music_end_tie_hybrid.md)
acrescentou o décimo quarto. Os [comandos de LFO e modulação](music_modulation_commands.md)
e o auxiliar de leitura elevaram o total a dezessete. A etapa de [memória e comandos estendidos](music_memory_commands.md) acrescentou outros quatorze, totalizando 31. As continuações ligaram todos os slots da tabela, incluindo frequência, e o [mixer PCM](pcm_mixer_native.md); ainda faltam serviços transitivos, saída de som e integração geral. Gameplay, recursos e backend
continuam necessários para o jogo Windows; veja [port_status.md](port_status.md).

Os quatro serviços da continuação estão detalhados em [padrões e repetição](music_pattern_commands.md).

A continuação de [prioridade e tempo](music_priority_tempo_commands.md) acrescentou dois bindings, totalizando 37.

A etapa de [transposição](music_key_shift_command.md) elevou o total a 38 bindings. A [seleção de instrumento](music_voice_command.md)
acrescentou o 39º binding, com 48 bytes assembly exatos e validação do C nativo.

O [comando de volume](music_volume_command.md) acrescentou o 40º binding nativo e
20 bytes assembly exatos. Sua validação própria passou em 2.385 cenários; os doze
corpora de áudio foram reexecutados com os fontes atuais.

O [comando de pan](music_pan_command.md) acrescentou o 41º binding nativo e
20 bytes assembly exatos. Sua validação passou em 2.385 cenários; os treze corpora
de áudio foram reexecutados com os fontes atuais.

O [pitch bend](music_pitch_bend_command.md) acrescentou o 42º binding nativo e
20 bytes assembly exatos. Sua validação passou em 2.483 cenários; os quatorze corpora
de áudio foram reexecutados com os fontes atuais.

O [alcance do bend](music_bend_range_command.md) acrescentou o 43º binding nativo e
20 bytes assembly exatos. Sua validação passou em 2.497 cenários; os quinze corpora
de áudio foram reexecutados com os fontes atuais.

O [atraso do LFO](music_lfo_delay_command.md) acrescentou o 44º binding nativo e
12 bytes assembly exatos. Sua validação passou em 2.397 cenários, com 33.923 ticks
musicais; os dezesseis corpora de áudio foram reexecutados com os fontes atuais.

O [tipo de modulação](music_mod_type_command.md) acrescentou o 45º binding nativo e
24 bytes assembly exatos. Sua validação passou em 3.185 cenários; os dezessete
corpora de áudio foram reexecutados com os fontes atuais.

A [afinação](music_tune_command.md) acrescentou o 46º binding nativo e
20 bytes assembly exatos. Sua validação passou em 2.495 cenários; os dezoito
corpora de áudio foram reexecutados com os fontes atuais.

O [PORT](music_port_command.md) acrescentou o 47º binding nativo e 24 bytes assembly
exatos. Passou em 3.471 cenários, com 3.983 escritas observadas; os dezenove corpora
foram reexecutados. A semântica dos dispositivos e a saída audível continuam pendentes.

A [configuração de frequência e VSync-on](sound_frequency_native.md) integra dois bindings,
totalizando 49. Seus 164 e 60 bytes GBA já pertenciam ao matching C e foram revalidados.
Os vinte corpora de áudio passaram; todos os 36 slots têm binding C nativo.

O [modo e VSync-off](sound_mode_native.md) acrescentam dois bindings, totalizando 51.
Os 152 e 124 bytes GBA já pertenciam ao matching C e foram revalidados. Passaram
33 testes direcionados e os 21 corpora de áudio; a referência usa CpuSet modelado.

A [inicialização e extensão](sound_initialization_native.md) acrescentam três
bindings, incluindo Dummy, totalizando 54. Seus 532 bytes GBA já estavam no
matching C. Passaram 51 testes direcionados e os 22 corpora de áudio.
Naquela etapa, os callbacks Cgb_Update e Cgb_Stop foram apenas instalados.
A continuação de [CGB nativo](cgb_native.md) integrou ambos e o auxiliar Volume,
chegando a 57 bindings, com 7.717 cenários, 69 testes direcionados e os 23 corpora.

O [mixer PCM](pcm_mixer_native.md) acrescentou 1.064 bytes assembly exatos e seu
C nativo. O mixer e a entrada já existente do player agora têm binding direto,
totalizando 59 endereços. Passaram 1.884 cenários, 87 testes direcionados e os
24 corpora de áudio. Saída de som e dispositivos continuam pendentes.

A [inicialização de alto nível e o wrapper](audio_startup_native.md) acrescentaram
três bindings, incluindo `MusicPlayer_Open`, chegando a 62 endereços.
Passaram 1.288 cenários, 1.392 execuções, 108 testes direcionados e os 25 corpora
de áudio. Os 252 bytes C/GNU C GBA já pertenciam ao matching. A cadeia instalada
de quatro players executou 96 atualizações pelo wrapper; APIs de músicas,
dispositivos, saída de áudio e jogo integrado continuam pendentes.
