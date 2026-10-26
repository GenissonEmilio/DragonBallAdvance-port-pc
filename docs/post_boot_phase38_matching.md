# Callback 0x080F02EC e encerramento da abertura

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes são descritivos, atribuídos neste projeto.

## Resultado

O callback solicitado, **`0x080F02EC`**, foi reconstruído em C estruturado,
sem asm, com **24/24 bytes iguais à ROM**. Carrega o fundo de índice 14 e
registra a fase seguinte. A continuação acrescentou **25 funções e 1.528
bytes completos**: 1.308 de instruções, 184 de literais e 36 de alinhamento.

O agregado atual tem **224 funções, 33.032 bytes iguais à ROM e 190 testes
aprovados, sem skips**. O bloco local inteiro em **`0x080EE654..0x080F0910`**
agora está coberto: **96 funções e 8.892 bytes contínuos**, sem lacunas nem
sobreposições. Isso inclui inicialização, fases, carregadores locais, fade,
cortina, scroll, movimento circular dos sprites, skip e destruição dessa abertura.
Chamadas a serviços externos continuam vinculadas aos endereços da ROM.

| Função | Endereço USA | Bytes completos |
|---|---|---:|
| `PostBoot_Phase38` | `0x080F02EC` | 24 |
| `PostBoot_Phase39` | `0x080EEC3C` | 144 |
| `PostBoot_Phase40` | `0x080F0304` | 40 |
| `PostBoot_Phase41` | `0x080EECCC` | 116 |
| `PostBoot_Phase47` | `0x080EED40` | 116 |
| `PostBoot_Phase42` | `0x080F032C` | 60 |
| `PostBoot_Phase43` | `0x080F0368` | 40 |
| `PostBoot_Phase44` | `0x080F0390` | 40 |
| `PostBoot_Phase45` | `0x080F03B8` | 68 |
| `PostBoot_Phase46` | `0x080F03FC` | 28 |
| `PostBoot_Phase48` | `0x080F0418` | 28 |
| `PostBoot_CreateRing` | `0x080F05CC` | 148 |
| `PostBoot_RingOnDestroy` | `0x080F0660` | 4 |
| `PostBoot_RingRun` | `0x080F0664` | 76 |
| `PostBoot_RingBegin` | `0x080F06B0` | 12 |
| `PostBoot_RingInitContract` | `0x080F06BC` | 68 |
| `PostBoot_RingContract` | `0x080F0700` | 56 |
| `PostBoot_RingSpin` | `0x080F07AC` | 56 |
| `PostBoot_RingHold` | `0x080F0738` | 48 |
| `PostBoot_RingInitSpin` | `0x080F0768` | 68 |
| `PostBoot_RingRelease` | `0x080F07E4` | 76 |
| `PostBoot_RingTail` | `0x080F0830` | 24 |
| `PostBoot_RingStep` | `0x080F0848` | 44 |
| `PostBoot_RingDraw` | `0x080F0874` | 36 |
| `PostBoot_PositionRing` | `0x080EF950` | 108 |

Todos os novos alvos usam agbcc GCC 2.9-arm-000512 com **`-O2 -mthumb-interwork`**.
Vinte e três fontes não usam asm. Dois usam **três templates vazios** no total:
um no criador da tarefa circular e dois no cálculo das posições. Conservam
o endereço do zero temporário, a extração do ângulo e a ordem de soma do
deslocamento de cada sprite. **Nenhum template emite instruções.**
Os três constam de `compiler_barriers` no manifesto e nos relatórios.

## Últimas fases do pai

A fase 38 carrega a entrada **14**; a fase anterior já carregou a 13.
Na ROM, as entradas 13/14 selecionam BGs **1/2**, recursos **77/54**,
paletas **14/1**; a entrada 14 pede espelhamento horizontal.

A fase 39 aguarda `elapsed >= timeline[step]`, incrementa o passo e calcula
a duração pelo limite seguinte. Cria scrolls para as entradas **13 e 14**,
slots **0 e 1**, e habilita os dois fundos em duas escritas. Os novos pares
signed da tabela `0x08A4E3F0` são **(-140, 16)** e **(215, 16)**.
A implementação de scroll já reconstruída mantém velocidade e aceleração
em ponto fixo; não força o último valor ao parâmetro de destino.

A fase 40 aguarda outro limite e incrementa o passo. A fase 41, se
`flags & 2` estiver limpo, aguarda o tempo e cria fade **0 → 16**, controle
**`0xFF`**. Preserva um único incremento de `step` antes de ler a duração.
Ativa `0x10` e agenda a fase 42, que aguarda o limite e aplica **`0xF0FF`**
ao controle de vídeo, desligando os quatro BGs.

A fase 43 destrói a tarefa da cortina, quando presente, e limpa seu ponteiro.
A fase 44 grava **`0x1040`** no controle de vídeo e zera os três shadows de
blend. A fase 45 aguarda a tabela, incrementa o passo, cria a tarefa circular
e ativa **`0x1000`** no pai. A fase 46 espera a tarefa limpar esse bit.

A fase 47 testa **`flags & 1`**, aguarda o próximo limite e cria o último
fade **0 → 16**, controle **`0xBF`**. A fase 48 espera `0x10` ser liberado,
ativa **`0x40000000`** e grava **NULL** no callback. O despachante já
reconstruído `PostBoot_Update` reconhece esse sinal e troca o callback da tarefa
para `PostBoot_Finish`, que será executado na próxima atualização da tarefa.
O encerramento existente destrói a tarefa, libera os nove sprites e
restaura a capacidade de tiles, além de sinalizar conclusão à sequência pai.

No caminho que começa com passo zero, a continuação usa estes limites absolutos
do contador de atualizações do pai; não representam uma medição em emulador:

| Passo | Tempo | Uso |
|---:|---:|---|
| 24 | 375 | Início do segundo par de scrolls |
| 25 | 395 | Duração dos scrolls / espera da fase 40 |
| 26 | 410 | Início do fade de fundos |
| 27 | 430 | Fim previsto do fade / desativação dos BGs |
| 28 | 471 | Criação da tarefa circular |
| 29 | 484 | Limite da contração inicial |
| 30 | 509 | Fim da espera antes de girar |
| 31 | 565 | Limite do giro / liberação do pai |
| 32 | 566 | Início do fade final |
| 33 | 600 | Limite usado para sua duração |

Foram verificados **34 valores** do roteiro. Esses acessos não provam a
extensão total da tabela. A ordem real depende do agendamento das tarefas,
que ainda precisa ser acompanhada por frame em emulador.

## Tarefa circular de sete sprites

`PostBoot_CreateRing` cria uma tarefa de **52 bytes**, prioridade **`0x400`**,
flags zero e destrutor vazio. Zera os dados por `CpuSet`, compartilha os
sprites **2 a 8** preparados pelo pai e salva a tarefa em `child3` (`+0x1E4`).

`PostBoot_RingRun` copia `elapsed` e `step` do pai a cada chamada, invoca a
fase e escreve o passo de volta no pai **somente se o retorno for zero**.
Todas as fases reconstruídas desse filho retornam zero. Essa sincronização
é o que permite à tarefa circular consumir os próximos tempos do roteiro.

Os campos de ângulo e raio usam **16 bits fracionários**:

- `RingBegin` agenda a preparação da contração, sem desenhar.
- `RingInitContract` começa com raio **200**, ângulo, velocidade e aceleração
  angular zero. Define velocidade radial **(-146 * 65536) / tempo restante**,
  aceleração radial zero, e agenda `RingContract`.
- `RingContract` integra o movimento, testa o limite, incrementa o passo
  quando necessário e desenha. Depois `RingHold` apenas aguarda e desenha.
- `RingInitSpin` zera a velocidade angular e usa aceleração angular
  **`0xC000`**. A velocidade radial é **(-30 * 65536) / tempo restante**,
  com aceleração radial zero. Desenha e agenda `RingSpin`.
- `RingSpin` integra, testa o limite, incrementa o passo e desenha.
- `RingRelease` divide a velocidade angular por quatro por shift signed,
  muda a aceleração angular para **`-0x6000`**, a velocidade radial para
  **`0xBBBBB`** e a aceleração radial para **`0x6000`**. Limpa `0x1000`
  no pai, integra e desenha; agenda `RingTail`.
- `RingTail` continua integrando e desenhando até a limpeza do pai.
  Liberar o pai não destrói imediatamente a tarefa circular.

`RingStep` preserva a ordem: velocidade angular += aceleração, ângulo +=
velocidade, velocidade radial += aceleração, raio += velocidade. Converte
ângulo por shift signed e raio para **unsigned de 16 bits** antes da posição.

`PostBoot_PositionRing` usa uma tabela signed em **`0x08D26750`**, com
amplitude **±16384**. Foram conferidas 1.280 amostras acessíveis pela rotina:
os pontos 0/256/512/768/1024 valem 0/16384/0/-16384/0, e as últimas 256
amostras repetem as primeiras 256. A extensão total não foi presumida.

Para cada sprite `i` em **0..6**, a lógica é:

```text
base = ângulo & 1023
fase = (146 * i + 110 + base) & 1023
x = ((raio * seno[fase + 256]) >> 14) + 120
y = ((raio * seno[fase]) >> 14) + 80
```

O centro é **(120, 80)**. As coordenadas são armazenadas em campos de 16 bits.
`RingDraw` chama `Graphics_DrawSprite` para os sete sprites; o corpo desse
renderizador em **`0x08110CA0`** agora tem [matching em C/GNU C](graphics_draw_sprite_matching.md). Os nomes e a forma do
movimento vêm do código; a identidade visual dos sprites não foi confirmada
por execução ou inspeção de assets nesta etapa.

## Validação e dependências restantes

```powershell
.\.venv\Scripts\python.exe tools\match.py --target post_boot_phase38
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Cada `.text` é linkada no endereço original e comparada integralmente,
incluindo literais e padding. Não há edição de assembly, compilador modificado,
opcodes embutidos, relocations pendentes, truncamento ou máscara de diferenças.
A auditoria também concatena os 96 binários em ordem de endereço e compara
todos os 8.892 bytes do bloco local com a ROM, sem lacunas ou sobreposições.

Os novos controles negativos alteram fundo e próximo callback, tempo e slot
dos scrolls, guardas e controles de fade, vídeo e destruição, sinal de conclusão,
prioridade e sprite inicial da tarefa circular, sincronização com o pai,
contração, giro, liberação, integração, quantidade de sprites e geometria.
Todos exigem rejeição após recompilar o C alterado.

Relatórios locais: `build/matching/summary.json`, subpastas individuais e
`build/verification.json`. A classificação dos novos bytes está em
`build/next/phase38_flow.json`; as leituras de tabelas em `phase38_tables.json`;
a auditoria final em `build/next/audit_193.py` e `audit_193.json`.

Não resta callback local pendente nesse bloco. O [desenho de sprites, alocador OAM, serviço de paleta e memset](graphics_draw_sprite_matching.md) também têm matching.
A [animação `0x0810FD70`, seus doze comandos e a paleta OBJ](sprite_animation_matching.md) também têm matching.
O [início do player e cinco serviços de áudio](music_player_start_matching.md) também têm matching.
Permanecem externos o processador de músicas `0x0810A724`, inicialização de áudio e outros wrappers/helpers.
O matching é por função;
ainda faltam o build completo da ROM, validação por frame e o port PC.
