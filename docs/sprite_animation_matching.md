# Animação de sprites e dependências da inicialização

A função **`Sprite_UpdateAnimation` em `0x0810FD70` foi reconstruída em GNU C**, com
**244/244 bytes iguais à ROM USA**. Seus doze processadores de comandos e o serviço de
paleta OBJ também têm matching integral: **14 funções novas, 1.056 bytes**.
O conjunto atual chega a **224 funções e 33.032 bytes idênticos**, com **190 testes aprovados**.

## Funções verificadas

| Função | Endereço USA | Bytes completos |
|---|---|---:|
| `Sprite_UpdateAnimation` | `0x0810FD70` | 244 |
| `SpriteCommand_Tiles` | `0x0810FFB8` | 144 |
| `SpriteCommand_Palette` | `0x08110048` | 148 |
| `SpriteCommand_JumpBack` | `0x08111C78` | 12 |
| `SpriteCommand_End` | `0x08111C84` | 16 |
| `SpriteCommand_Sound` | `0x08111C94` | 20 |
| `SpriteCommand_Hitbox` | `0x081100DC` | 188 |
| `SpriteCommand_Translate` | `0x08111CA8` | 28 |
| `SpriteCommand_Skip` | `0x08111CC4` | 12 |
| `SpriteCommand_Switch` | `0x08111CD0` | 24 |
| `SpriteCommand_Reserved9` | `0x08111CE8` | 8 |
| `SpriteCommand_Priority` | `0x08111CF0` | 28 |
| `SpriteCommand_Order` | `0x08111D0C` | 16 |
| `Graphics_LoadObjPalette` | `0x081145C0` | 168 |

São **964 bytes de instruções, 76 de literais e 16 de padding**. Todos entram na comparação;
não há máscaras, recortes, relocations pendentes ou ajustes do assembly gerado.
O SHA-256 da função principal é `fe5b325a37ccaf8cb9d77b71cea407cd151227aa4d2a5a30db4327af2d40ad28`.

O perfil compatível continua sendo `agbcc` GCC 2.9-arm-000512 com `-O2 -mthumb-interwork`.
A rotina principal usa **9 restrições vazias expandidas**, o comando de hitbox usa **5** e
a paleta usa **18**. As 32 restrições não emitem instruções; conservam registradores e
vida útil de valores do binário original. As outras onze funções desta etapa são C sem
inline assembly. Os vínculos e contagens constam de `config/functions.usa.json`.
A versão histórica exata do SDK continua sem identificação exclusiva.

## Estado e temporização

O layout de 48 bytes em `include/sprites.h` agora identifica os campos:

| Offset | Campo | Uso comprovado |
|---|---|---|
| `+0x04` | `frameIndex`, u32 | Índice usado pelo renderer |
| `+0x08` | `flags`, u32 | Estado, flips, paleta e controles de transferência |
| `+0x0C` | `animation`, u16 | Índice de animação |
| `+0x0E` | `animationCursor`, u16 | Cursor em palavras de 32 bits |
| `+0x16` | `animationDelay`, s16 | Tempo restante com 8 bits fracionários |
| `+0x18` | `previousAnimation`, u16 | Detecção de troca de animação |
| `+0x1A/+0x1B` | `variant/previousVariant`, u8 | Detecção de troca de variante |
| `+0x1C` | `speed`, u8 | Avanço temporal multiplicado por 16 |
| `+0x20` | Dados de hitboxes | Registros de 8 bytes acessados pelo comando -6 |

Se a animação ou a variante mudou, a função atualiza os campos anteriores, zera cursor e
delay e limpa `flags & 0x4000`. Essa flag encerra a animação: se continuar ativa, retorna 0.
Quando o delay assinado é positivo, subtrai `speed << 4` e retorna 1. Mesmo cruzando zero,
o próximo quadro só é lido na chamada seguinte.

O primeiro campo de `gSpriteTables` é uma tabela de scripts, indexada por animação e
variante. O objeto padrão foi instalado por `Game_ResetVideoState`, em `0x0811855C`, e
seu primeiro ponteiro aponta para `0x0816B928`. A extensão global dessas tabelas ainda
não está provada.

Uma palavra não negativa inicia o par `(duração, frameIndex)`. A função calcula
`delay = (duração << 8) + delay - (speed << 4)`, grava o frame, liga `0x04000000` e avança
o cursor em duas palavras. Essa flag conecta a animação ao carregamento de tiles do
[renderer já reconstruído](graphics_draw_sprite_matching.md).

## Comandos negativos

A tabela de 12 ponteiros Thumb começa em **`0x08D27158`** e ocupa os 48 bytes imediatamente
anteriores à tabela de tamanhos OAM, em `0x08D27188`. O índice é o complemento `~comando`.
A chamada indireta usa o helper original **`_call_via_r2` em `0x08116A24`**, conferido na ROM
como `bx r2` seguido do alinhamento original. Esse helper externo não é contado como
uma nova função C.

| Comando | Efeito recuperado |
|---:|---|
| -1 | Avança 3 palavras e enfileira transferência de tiles, salvo flag `0x80000` |
| -2 | Avança 3 palavras e carrega paleta OBJ, salvo flag `0x40000` |
| -3 | Subtrai do cursor o deslocamento de palavras informado |
| -4 | Liga `0x4000`, retorna 0 e mantém o cursor |
| -5 | Avança 2 palavras e chama `Music_StartSong` com ID u16 |
| -6 | Avança 3 palavras, copia e espelha uma hitbox |
| -7 | Avança 2 palavras e soma deslocamentos de 16 bits a x/y |
| -8 | Avança 3 palavras, sem outros efeitos observados |
| -9 | Troca animação/variante, grava variante anterior 255 e retorna -1 |
| -10 | Avança 4 palavras e preserva o ponteiro de comando como retorno |
| -11 | Avança 2 palavras, limpa bits `0x3000` e aplica o argumento deslocado em 12 |
| -12 | Avança 2 palavras e grava `argumento << 6` no grupo OAM |

Retorno 1 faz o despachante continuar a ler comandos. Retorno -1 recarrega o script da
nova animação/variante e zera o cursor. Qualquer outro retorno sai imediatamente.
O comportamento incomum de -10 foi preservado: seu propósito ainda não foi estabelecido.
Não há verificação de limites do índice de comando no código original.

O comando de tiles escolhe blocos de 64 bytes e `tiles8` para índice negativo; para índice
não negativo usa blocos de 32 bytes e `tiles4`. A aritmética do índice negativo é mantida,
sem aplicar valor absoluto. O tamanho é truncado a u16 e o índice da fila volta com
máscara `0x7F`, sem teste de fila cheia.

O comando de paleta lê um índice de banco, contagem u16 e deslocamento u16. Com
`gSystemFlags & 0x20000`, chama `Graphics_LoadObjPalette`: usa as três tabelas de
componentes de cor, chama o callback opcional e liga a flag de paleta OBJ `2`.
No caminho direto, DMA3 copia halfwords para `gObjPaletteBuffer` em `0x03002ED0` e liga
essa mesma flag. A largura e os truncamentos dos argumentos diferem entre esses caminhos
e foram preservados.

A hitbox usa os quatro bits baixos do primeiro argumento para selecionar um registro de
8 bytes a partir de `sprite+0x20`. DMA3 copia duas palavras. Se ambos os pares de limites
forem iguais, grava -1 na primeira palavra do registro. Caso contrário, `0x800` troca e
nega os limites verticais; `0x400` faz o mesmo nos horizontais. O código usa XOR e operações
de byte como o original. O seletor não tem checagem de limites; a quantidade global de
registros válidos não foi inferida apenas dessa máscara.

## Ligação com a abertura

`PostBoot_PrepareSprites` em `0x080EF3B4` chama a rotina reconstruída. O alias antigo
`Func_0810FD70` permanece no mapa e os chamadores anteriores continuam iguais à ROM.
Os nomes dos campos foram atualizados sem alterar o layout. A auditoria leu os nove
registros usados por esse inicializador e percorreu seus scripts até o comando de fim:

| Sprites | Animação / variante | Script | Primeiro par duração / frame |
|---|---|---|---|
| 0 | 4 / 16 | `0x0811BD74` | 3 / 71 |
| 1 | 4 / 17 | `0x0811BDF8` | 3 / 74 |
| 2 a 8 | 177 / 0 a 6 | `0x08166990` a `0x08166A68`, passo 36 bytes | 1 / 0 a 6 |

Esses nove scripts usam -2, -1 e -4: os dois primeiros têm quatro pares de frame; os
outros sete têm um. O percurso é análise estática limitada desses dados, sem execução
em emulador. Não mede tempo observado de tela nem confirma todos os assets do jogo.

A concatenação de seções completas também confere três intervalos contínuos: os comandos
de tiles/paleta/hitbox (`0x0810FFB8..0x08110198`, 480 bytes), as duas paletas
(`0x081145C0..0x08114710`, 336 bytes), e alocador/processador OAM mais nove comandos
(`0x081119F0..0x08111D1C`, 812 bytes). Funções antigas desses intervalos não são
contadas novamente no avanço de 1.056 bytes.

## Reproduzir e limites

```powershell
.\.venv\Scripts\python.exe tools\match.py --target sprite_update_animation
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A suíte tem dez novos testes com 22 alterações negativas recompiladas: reset, delay,
velocidade, despacho, troca de script, duração, flag de tiles, sinal do índice, fila,
modo de paleta, largura DMA, hitbox, retornos especiais, prioridade, grupo OAM e callback.
Cada alteração precisa falhar na comparação com a ROM.

Evidências locais: `build/matching/summary.json`, relatórios individuais,
`build/verification.json`, `build/next/animation_flow.json`, `animation_tables.json` e
`build/next/audit_207.py`/`audit_207.json`. A auditoria verifica igualdade das seções
completas, hashes atuais, fontes dos compiladores sem modificações e templates vazios.

A [etapa seguinte de áudio](music_player_start_matching.md) concluiu **`MusicPlayer_Start`,
`0x0810B4EC`**, e cinco serviços, com 716 bytes novos. Permanecem externos o processador de
músicas, inicialização de baixo nível e mixer. O build completo da ROM, validação por frame
em emulador, extração global de assets e o executável nativo de PC continuam pendentes.
Aritmética de largura fixa, shifts e acessos de DMA precisam ser preservados/adaptados
na futura camada de PC; os fontes atuais reproduzem o alvo ARM com o compilador verificado.
