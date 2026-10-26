# Callback 0x080EEA7C, cortina de sprites e scroll

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes são descritivos, atribuídos neste projeto.

## Resultado

O callback solicitado, **`0x080EEA7C`**, foi reconstruído em C estruturado,
sem asm, com **148/148 bytes iguais à ROM**. A etapa acrescentou
**16 funções e 1.724 bytes completos**: 1.530 de instruções, 176 de literais
e 18 de alinhamento. O agregado atual tem **224 funções, 33.032 bytes iguais
e 190 testes aprovados, sem skips**.

| Função | Endereço USA | Bytes completos |
|---|---|---:|
| `PostBoot_Phase30` | `0x080EEA7C` | 148 |
| `PostBoot_Phase31` | `0x080EEB10` | 156 |
| `PostBoot_Phase32` | `0x080F0224` | 24 |
| `PostBoot_Phase33` | `0x080F023C` | 24 |
| `PostBoot_Phase34` | `0x080EEBAC` | 144 |
| `PostBoot_Phase35` | `0x080F0254` | 40 |
| `PostBoot_Phase36` | `0x080F027C` | 88 |
| `PostBoot_Phase37` | `0x080F02D4` | 24 |
| `PostBoot_CreateCurtain` | `0x080EF568` | 232 |
| `PostBoot_CurtainOnDestroy` | `0x080F0580` | 4 |
| `PostBoot_CurtainWait` | `0x080F0584` | 68 |
| `PostBoot_CurtainMove` | `0x080EF650` | 260 |
| `PostBoot_CurtainHold` | `0x080EF754` | 88 |
| `PostBoot_CreateScroll` | `0x080EF7AC` | 268 |
| `PostBoot_ScrollRun` | `0x080EF8B8` | 152 |
| `PostBoot_ScrollOnDestroy` | `0x080F05C8` | 4 |

Todos usam agbcc GCC 2.9-arm-000512 com **`-O2 -mthumb-interwork`**.
Doze fontes não usam asm. Quatro usam **oito templates vazios** no total:
um no criador da cortina, cinco em seu movimento, um em sua repetição e
um no criador de scroll. Conservam endereços temporários, valores de
comparação e argumentos em registradores. **Nenhum template emite instruções.**

## Callback e fases seguintes

`PostBoot_Phase30` testa **`flags & 2`** e aguarda
`elapsed >= timeline[step]`. Incrementa `step` **antes** de testar se o campo
de fade está livre. Essa ordem foi preservada: mesmo com fade ocupado,
o passo já foi incrementado quando o limite é atingido.

No caminho livre, zera uma configuração de 20 bytes por `Runtime_Memset`,
seleciona controle **`0xEF`**, alpha zero e coeficiente **16 → 0**. Calcula
a duração signed de 16 bits com `timeline[step] - elapsed`, incrementa o
passo novamente e chama o serviço de fade já reconstruído. Depois ativa
`0x10`, cria a cortina, salva a tarefa no campo `+0x1D8` e agenda a fase 31.

A fase 31 também testa o bit 2 e aguarda a tabela. Cria outro fade com
controle **`0xC0 | (1 << backgrounds[10].background)`**, duração **40** e
coeficiente 16 → 0, liga o BG dessa entrada e agenda a fase 32. Ela não
condiciona a troca do callback ao retorno do criador de fade.

As fases 32 e 33 carregam as entradas **11 e 12**. A fase 34 aguarda o
próximo tempo, incrementa o passo e usa o limite seguinte para calcular
uma duração unsigned de 16 bits. Cria duas tarefas de scroll, slots **0 e 1**,
liga os dois BGs em **duas escritas** e agenda a fase 35.

A fase 35 apenas aguarda o próximo limite e incrementa o passo. A fase 36
aguarda outro limite e desliga os BGs 11/12, também em duas escritas.
A fase 37 carrega a entrada **13** e registra **`0x080F02ED`**, para o próximo
callback `0x080F02EC`, agora reconstruído na [continuação](post_boot_phase38_matching.md).

No caminho iniciado com passo zero, os novos valores utilizados são:

| Passo | Tempo absoluto | Uso |
|---:|---:|---|
| 18 | 245 | Início da fase 30 |
| 19 | 252 | Limite para calcular a duração do primeiro fade |
| 20 | 285 | Início da fase 31 |
| 21 | 308 | Criação das duas tarefas de scroll |
| 22 | 328 | Limite do scroll e da espera da fase 35 |
| 23 | 348 | Desativação dos dois fundos |

Agora foram verificados os primeiros **24 tempos**. A extensão completa da
tabela não foi inferida desses acessos. As entradas 11/12/13 usam, nesta ROM,
BGs **1/2/1** e recursos **44/65/77**, respectivamente.

## Cortina de sprites

`PostBoot_CreateCurtain` retorna zero quando a tarefa já está ocupada.
No caminho de criação, ativa `0x1000` no controle de vídeo e cria uma tarefa
de **24 bytes**, prioridade **`0x300`**, flags zero e destrutor vazio.
Zera seus dados por `CpuSet`, usa os sprites **0 e 1** preparados pelo pai e
configura coordenadas signed de 16 bits com **seis bits fracionários**:

```text
x = 0x4400 = 272 pixels
y = 0x1400 = 80 pixels
velocidade X = -608 / 64 = -9,5 pixels por atualização
velocidade Y = 0
```

Salva o BG da entrada 9, o pai e a tarefa. Depois ativa `0x2000` no controle
de vídeo e configura o shadow de janelas. `PostBoot_CurtainWait` só troca
para o callback de movimento quando **`parent->elapsed > 259`**.

`PostBoot_CurtainMove` soma as velocidades às coordenadas antes de convertê-las
para pixels. Preserva as guardas e seus efeitos:

- Quando X signed é **menor que -32**, ativa **`0x400`** no pai, agenda o estado
  de repetição, limpa `0x2000` do controle de vídeo e zera seis halfwords de janelas.
- Quando X unsigned cabe em **0..255**, atualiza a posição da janela. Dentro
  dessa guarda, X signed **até 71** ativa **`0x200`** e desliga o BG salvo.
- Desenha o sprite 0 na posição atual. Desenha o sprite 1 em Y=80, de X=240
  para a esquerda em passos de 32 enquanto sua posição signed for maior que X.

Mesmo na atualização que troca de callback, os desenhos restantes da função
são executados. `PostBoot_CurtainHold` passa a desenhar o sprite 1 de **-32
até 256**, de 32 em 32, sempre em Y=80. Os dois estados chamam a função
original de desenho em **`0x08110CA0`**, agora nomeada `Graphics_DrawSprite`;
seu corpo agora tem [matching em C/GNU C](graphics_draw_sprite_matching.md).

## Scroll com velocidade e aceleração

`PostBoot_CreateScroll` cria tarefas de **32 bytes**, prioridade **`0x400`**,
flags zero e destrutor vazio. Zera os dados, salva índice do roteiro, slot,
BG e pai, registra a tarefa no slot e ativa **`0x800`** no pai.

Os antigos campos `child1` e `child2` foram identificados como um array:
**`scrollTasks[2]`**, nos offsets **`+0x1DC` e `+0x1E0`**. O destrutor do pai
foi atualizado para essa representação e continua com **136/136 bytes iguais**.
Os demais offsets e o tamanho de 492 bytes do pai foram preservados.

A tabela em **`0x08A4E3F0`** fornece os primeiros dois pares signed:

| Entrada do roteiro | Início | Parâmetro de destino |
|---:|---:|---:|
| 11 | 180 | 16 |
| 12 | -172 | 16 |

O serviço mantém posição, velocidade e aceleração em ponto fixo com
**16 bits fracionários**, usando as divisões signed originais:

```text
posição inicial = início * 65536
delta = (destino - início) * 131072
velocidade inicial = delta / duração
aceleração = -delta / (duração * duração)
```

O callback faz, nesta ordem, **velocidade += aceleração**,
**posição += velocidade**, escreve `posição >> 16` no scroll horizontal e
incrementa o contador signed de 16 bits. Ao atingir a duração, libera seu
slot. Só limpa `0x800` quando o outro slot também está livre; então destrói
a tarefa atual. Ele **não força a posição final ao parâmetro de destino**.
Foram preservados a ordem das somas, truncamentos e arredondamentos do compilador.

## Validação e continuação

```powershell
.\.venv\Scripts\python.exe tools\match.py --target post_boot_phase30
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Cada `.text` é linkada no endereço original e comparada por inteiro, incluindo
literais e padding. Não há relocations pendentes, edição do assembly,
compilador modificado, opcodes embutidos ou máscaras de diferenças.
Os novos controles negativos alteram guardas, tempos, controles de fade,
movimento, janela, repetição dos sprites, slots, aceleração e conclusão
das tarefas, e exigem rejeição pelo comparador após recompilar.

Os relatórios locais estão em `build/matching/summary.json`, nas subpastas
individuais e em `build/verification.json`. A classificação dos bytes fica em
`build/next/phase30_flow.json`; as leituras das tabelas em `phase30_tables.json`.
A auditoria compara todo o bloco contínuo, com funções de etapas anteriores e da continuação:

| Início | Fim exclusivo | Bytes | Funções |
|---|---|---:|---:|
| `0x080EE654` | `0x080F0910` | 8.892 | 96 |

O [callback `0x080F02EC` e o encerramento](post_boot_phase38_matching.md) também têm matching.
O [desenho de sprites, alocador OAM, serviço de paleta e memset](graphics_draw_sprite_matching.md) também têm matching.
A [animação `0x0810FD70`, seus doze comandos e a paleta OBJ](sprite_animation_matching.md) também têm matching.
O [início do player e cinco serviços de áudio](music_player_start_matching.md) também têm matching.
Permanecem externos o processador de músicas `0x0810A724`, inicialização de áudio e outros wrappers/helpers.
A validação é por
função compilada; faltam o build completo da ROM, execução por frame e o port PC.
