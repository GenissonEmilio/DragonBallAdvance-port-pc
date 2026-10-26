# MusicPlayer_Start e serviços de áudio da inicialização

**`MusicPlayer_Start`, em `0x0810B4EC`, foi reconstruída em GNU C: 228/228 bytes iguais à ROM USA.**
A etapa também concluiu cinco dependências de abertura/configuração do áudio: **seis funções,
716 bytes completos**. O agregado atual tem **224 funções, 33.032 bytes idênticos e 190 testes aprovados**.

## Alvos e método

| Função | Endereço USA | Bytes completos |
|---|---|---:|
| `MusicPlayer_Start` | `0x0810B4EC` | 228 |
| `MusicPlayer_Open` | `0x0810B474` | 120 |
| `MusicPlayer_Clear` | `0x0810B120` | 20 |
| `Sound_VSyncOff` | `0x0810B3BC` | 124 |
| `Sound_VSyncOn` | `0x0810B438` | 60 |
| `Sound_SetFrequency` | `0x0810B22C` | 164 |

São **610 bytes de instruções, 96 de literais e 10 de alinhamento**, todos comparados.
Cada função foi compilada e linkada no endereço original com agbcc GCC 2.9-arm-000512,
`-O2 -mthumb-interwork`. O compilador e o assembly gerado não foram modificados.
O perfil compatível não identifica exclusivamente o SDK histórico do jogo.

A função principal usa **18 restrições vazias expandidas de GNU C**, `MusicPlayer_Open`
usa **uma** e `Sound_SetFrequency` usa **nove**. Elas conservam registradores, temporários e
ordem das operações sem emitir instruções. A função principal explicita três blocos e seus
saltos com `goto` de C; não há templates de instruções, bytes de código embutidos ou metadados
novos de labels. As outras três funções são C sem inline assembly.
As contagens constam de `config/functions.usa.json` e dos relatórios de compilação.

`reference/music_player_start.c` oferece a leitura comportamental com loops estruturados.
Esse arquivo é excluído do build e não é apresentado como matching. O fonte que produz o
binário idêntico é `src/music_player_start.c`.

O SHA-256 dos 228 bytes é `52f0b5b1ba337a053c8dde6375741ce06e164f80a4ba2ee07175d1e4808da85c`.

## Decisão de início e estado do player

A função retorna sem modificar o player se `lock != 0x68736D53`.
O byte `player+0x0B`, mantido como campo `priority`, controla a verificação de prioridade;
a prioridade corrente da música fica em **`+0x09`**, campo `songPriority`.

Quando a verificação está ligada, a prioridade é aplicada se há música e a primeira trilha
está com `0x40`, ou se a metade baixa de `status` é diferente de zero e o status assinado
não é negativo. Uma música nova com prioridade menor que a corrente é rejeitada.
As duas leituras e os tamanhos de acesso ao status foram preservados.

Ao aceitar a música, incrementa o lock, zera status e contador, grava o header e o banco de
instrumentos, atualiza a prioridade e inicializa os campos temporais em `+0x1C..+0x24` com
`150, 256, 150, 0, 0`. A interpretação completa desses contadores ainda depende do processador
de trilhas, mas esses valores e offsets estão provados.

Percorre até `min(trilhas da música, capacidade do player)`. Em cada registro de **80 bytes**,
chama `MusicTrack_Stop`, grava status `0xC0`, zera a lista de canais e instala o ponteiro do
script da trilha em `+0x40`. Nos slots excedentes do player, para a trilha e grava status zero.
Se o modo do header tem `0x80`, encaminha o byte completo para `Func_0810B2D0`, já reconstruída.
Por fim restaura `0x68736D53` no lock.

## Abertura, limpeza e encadeamento

`MusicPlayer_Open` trunca o argumento de contagem para u8, retorna para zero e limita a
capacidade a **16 trilhas**. O protótipo público recebe u32 e faz essa truncagem dentro do
corpo, preservando a ordem do binário. O chamador anterior em `audio_initialize.c` foi
recompilado e continua igual à ROM.

Com o lock do som válido, bloqueia a estrutura, chama `MusicPlayer_Clear`, instala buffer,
capacidade e status `0x80000000`, e desativa cada trilha. Preserva o processador e o primeiro
player anteriores nos offsets `+0x38/+0x3C`. Depois coloca o novo player no início da cadeia
e registra **`MusicPlayer_Update`, `0x0810A724`**, agora [reconstruído separadamente](music_player_update_hybrid.md). Restaura os dois locks.

`MusicPlayer_Clear` é o **wrapper de 20 bytes** que chama o ponteiro em `0x03001CFC`, por
`_call_via_r1`. Na tabela original, a entrada 35 em `0x08A67460` aponta para `0x0810A4AD`;
a cópia da tabela começa em `0x03001C70`, produzindo essa célula. O callback original em
`0x0810A4AC` zera **64 bytes**, com quatro stores múltiplos. Esse callback de baixo nível
continua externo e não foi contado como função C reconstruída nesta etapa.
O header agora representa os 64 bytes do player e conserva os offsets usados pelos alvos antigos.

## Frequência, timer e DMA

`Sound_SetFrequency` seleciona `(mode & 0xF0000) >> 16` e lê o índice menos um na tabela de
halfwords `0x08A675D4`. Foram conferidas as primeiras doze entradas:
`96, 132, 176, 224, 264, 304, 352, 448, 528, 608, 672, 704`.
A função não verifica limites; a extensão total da tabela não foi estabelecida apenas por
essas leituras.

Ela grava as amostras por frame e calcula, com divisões inteiras assinadas pelo helper original:

- `pcmFrames = 1584 / samples`;
- `sampleRate = (597275 * samples + 5000) / 10000`;
- `sampleReciprocal = ((0x01000000 / sampleRate) + 1) >> 1`;
- recarga do timer 0: `-(280896 / samples)`, truncada para 16 bits.

Desliga o timer, grava sua recarga, chama `Sound_VSyncOn`, espera sair da linha 159 e retornar
a ela, e habilita o timer com `0x80`. O loop de espera e a ordem dos acessos voláteis permanecem.

O modo `0x0095FC00` usado na inicialização seleciona a entrada 5: **264 amostras por frame,
6 frames por buffer PCM, taxa calculada de 15.768 e recarga `0xFBD8`**. Esses números são resultados
estáticos do algoritmo e dos dados da ROM, sem medição de áudio em execução.

`Sound_VSyncOff` aceita locks `magic` e `magic+1`, soma 10, verifica o bit de repetição dos
DMA1/2, faz as escritas originais de parada e limpa os dois buffers PCM. O preenchimento
começa em `sound+0x350` e tem `0x318` palavras, **3.168 bytes**.

`Sound_VSyncOn` atua quando o lock difere do magic, grava `0xB600` nos controles altos dos
DMA1/2, preserva a leitura do byte `sound+4`, zera esse byte e subtrai 10 do lock.
O teste não foi restringido artificialmente a um único lock suspenso.

## Dados usados pela abertura

A tabela de quatro players em `0x08A69038` tem capacidades **16, 4, 5 e 2**. Seus campos de
verificação de prioridade são zero nessa ROM. `PostBoot_Run` pede a música **1**:

- header `0x08D0E854`, player 0;
- **14 trilhas**, prioridade 0, modo `0x80`;
- banco de instrumentos `0x08A6871C`;
- scripts das trilhas lidos e conferidos individualmente em `player_tables.json`.

Assim, o fluxo reconstruído prepara 14 trilhas e desativa as duas restantes da capacidade de 16.
Isso conecta a função solicitada à abertura sem afirmar que o mixer já foi executado ou portado.

## Verificação e continuação

```powershell
.\.venv\Scripts\python.exe tools\match.py --target music_player_start
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os oito novos testes fazem **20 alterações negativas recompiladas**, cobrindo lock, prioridade,
limites e estados de trilhas, tempos, modo, capacidade e cadeia de players, DMA, limpeza PCM,
fórmula de frequência, timer e espera de scanline. Cada alteração precisa reprovar na comparação.
A suíte completa passou com **190 testes, sem skips**.

Também foi conferida a concatenação dos binários completos de `Sound_VSyncOff`, `Sound_VSyncOn`,
`MusicPlayer_Open`, `MusicPlayer_Start` e `MusicPlayer_Stop`: **596 bytes contínuos** em
`0x0810B3BC..0x0810B610`. A parada do player já estava reconstruída e não foi recontada nos 716 bytes novos.

Evidências locais: `build/matching/summary.json`, relatórios individuais, `build/verification.json`,
`build/next/player_flow.json`, `player_tables.json` e `audit_213.py`/`audit_213.json`.

A continuação concluiu [Sound_Initialize, Sound_Extend e quatro serviços CGB](sound_initialization_matching.md).
A etapa seguinte concluiu [`Cgb_Update`, fade e volume/pitch](audio_update_matching.md).
[`MusicPlayer_Update` (`0x0810A724`)](music_player_update_hybrid.md) foi concluído pela divisão C nativo/assembly GBA. Permanecem
originais utilitários e comandos da biblioteca, além do mixer com trecho copiado para RAM. A análise da entrada `0x0810A084` não delimitou o mixer inteiro: o salto para
RAM é continuação de processamento, não um retorno de função.
O estado e os marcos necessários para o executável PC estão em [port_status.md](port_status.md).
