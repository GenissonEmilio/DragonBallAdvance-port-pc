# Graphics_DrawSprite e serviços de inicialização

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes são descritivos, atribuídos neste projeto.

## Resultado

**`Graphics_DrawSprite`, em `0x08110CA0`, foi reconstruída em C/GNU C com
1.188/1.188 bytes idênticos à ROM.** A etapa também concluiu seu alocador de
OAM, o serviço de paleta chamado pela abertura e `Runtime_Memset`.

| Função | Endereço USA | Bytes de instruções | Literais | Padding | Total |
|---|---|---:|---:|---:|---:|
| `Graphics_DrawSprite` | `0x08110CA0` | 1.104 | 80 | 4 | 1.188 |
| `Graphics_AllocateOam` | `0x081119F0` | 116 | 32 | 4 | 152 |
| `Graphics_LoadBgPalette` | `0x08114668` | 152 | 16 | 0 | 168 |
| `Runtime_Memset` | `0x08118508` | 82 | 0 | 2 | 84 |

São **quatro funções e 1.592 bytes completos** novos, com zero diferenças.
Ao concluir esta etapa, o conjunto tinha **193 funções, 28.816 bytes iguais à ROM e 130 testes
aprovados, sem skips**. O bloco local da abertura continua integralmente
validado: 96 funções e 8.892 bytes contínuos em `0x080EE654..0x080F0910`.

Os três alvos gráficos usam agbcc GCC 2.9-arm-000512 com
**`-O2 -mthumb-interwork`**. `Runtime_Memset` usa **`-O2`**, sem interworking,
para reproduzir o retorno original `POP {r4,r5,pc}`. São perfis compatíveis
verificados, sem identificação exclusiva do SDK histórico.

O renderer explicita registradores e um scratch de onze words em GNU C.
Há **193 templates vazios após o pré-processamento** nessa função, **18**
no serviço de paleta e **um** no memset; o alocador é C estruturado sem asm.
O total novo é **212 restrições vazias**. A macro `IN_REGISTER` representa
uma restrição por expansão; a contagem é feita no `.i` consumido pelo
compilador. **Nenhum template contém ou emite instruções.**

Não foram usados opcodes como dados, funções naked, edição de assembly,
compilador modificado, relocations mascaradas ou cortes da comparação.
A versão algorítmica em `reference/graphics_draw_sprite.c` é somente um
auxílio de leitura, excluído do manifesto e dos totais de matching.
O fonte de produção é `src/graphics_draw_sprite.c`.

## Caminho do renderizador

A rotina recebe o sprite de **48 bytes** já utilizado pelas tarefas da
abertura. O layout foi compartilhado em `include/sprites.h`, preservando
os offsets e o tamanho de seus usuários anteriores. Foram identificados:

| Offset | Campo |
|---|---|
| `+0x00` | Destino dos tiles em VRAM |
| `+0x04` | Índice de frame e seu formato nos quatro bits superiores |
| `+0x08` | Flags de desenho |
| `+0x0C` | Animação |
| `+0x10`, `+0x12` | Coordenadas signed de 16 bits |
| `+0x14` | Grupo de ordenação OAM |
| `+0x1D` | Primeiro índice OAM da chamada |
| `+0x1E` | Quantidade de subframes, truncada para um byte |
| `+0x1F` | Seleção de paleta |

Se o frame vale `0xFFFFFFFF`, retorna imediatamente. Formato zero usa
registros de dimensões com stride **12**; os demais usam stride **16**.
O formato **1** habilita o caminho adicional de tiles descrito abaixo.
O stride unsigned também preserva o descarte dos bits superiores na
multiplicação por 16, como no código original.

A rotina copia a quantidade de subframes para o sprite e lê suas coordenadas.
Com `flags & 0x20000`, subtrai o deslocamento global em `0x03002B54`.
Depois prepara atributos, origem e espelhamento:

| Flags do sprite | Efeito observado |
|---|---|
| `0x200` | Acrescenta `0x1000` ao atributo 0 |
| `0x20` | Modo affine; acrescenta `0x100` ao atributo 0 e usa os cinco bits inferiores como índice da matriz |
| `0x40`, dentro do modo affine | Subtrai metade das dimensões da origem, duplica largura/altura e acrescenta `0x200` ao atributo 0 |
| `0x400` e `0x800`, fora do modo affine | Ajustam origem e espelhamento horizontal/vertical, combinados com os bits 14/15 do registro de dimensões |
| `0x180` | Transferidos, deslocados três bits, para o atributo 0 |
| `0x3000` | Transferidos para os bits 10/11 do atributo 2 |

O corte só é feito quando a largura é diferente de zero. Retorna se
**x + largura < 0**, **x > 240**, **y + altura < 0** ou **y > 160**.
As igualdades de borda são aceitas. A largura zero pula toda essa guarda.
Os casts de 16 bits usados nas meias dimensões também foram preservados.

Depois registra o índice OAM inicial e percorre os subframes. Para cada um:

1. Aloca uma entrada com grupo **`(order & 0x7C0) >> 6`**. Se receber a
   sentinela de falha, retorna imediatamente. As entradas anteriores permanecem
   consumidas; esse caminho não executa a parte final de transferência de tiles.
2. Copia **seis bytes**, por DMA com controle `0x80000003`, do template
   `(oamIndexAndFlip & 0x3FFF) + i`. O stride do template é 6; o da lista OAM é 8.
3. Extrai X de nove bits e Y de oito bits e aplica **`0xFE00`** aos dois
   atributos antes de acrescentar as posições e flags.
4. Quando necessário, inverte os bits `0x1000`/`0x2000` do atributo 1 e
   calcula o deslocamento com largura/altura do subframe. A tabela em
   **`0x08D27188`** contém doze pares de tamanhos, verificados na ROM.
5. Soma as coordenadas com wrap de **nove bits em X** e **oito em Y**,
   aplica atributos e paleta e, quando o atributo 0 contém `0x2000`,
   acrescenta outra vez os dez bits inferiores do índice de tile.
6. Acrescenta **`(destinoVRAM - 0x06010000) >> 5`** ao atributo 2.

A rotina monta a lista de OAM e pode enfileirar cópias; ela não substitui o
commit de hardware já reconstruído. Os sprites da cortina e do círculo
agora chamam um corpo C com matching, em vez de depender apenas do símbolo externo.

## Transferências agrupadas de tiles

Este trecho só roda depois dos subframes, com **formato 1** e
**`flags & 0x04000000`**. Limpa esse bit, lê a word adicional do registro de
16 bytes e separa **24 bits de índice** e **oito bits de quantidade**.
Acessa a lista de índices por um ponteiro no offset `+0x18` das tabelas.

O sinal do primeiro índice seleciona os blocos de **32 ou 64 bytes** e os
ponteiros nos offsets `+0x10` ou `+0x14`. O código preserva os índices
assinados e o resultado de 32 bits da multiplicação; não os converte em
valor absoluto. Esse detalhe precisará de wrap explícito no futuro port.

Agrupa as fontes quando **`início + tamanho == próxima fonte`**. O tamanho
acumulado é truncado para **16 bits** a cada extensão. Uma descontinuidade
gera um registro de 12 bytes na fila em `0x03003130`, avança o destino pelo
tamanho anterior e começa outro grupo. Sempre enfileira o grupo final.
O índice de escrita em `0x03003F10` avança com máscara **`0x7F`**.
A rotina não acrescenta teste de fila cheia ou validação dos metadados.

O reset já reconstruído seleciona a base de tabelas em **`0x0811855C`**.
Foram lidas as words acessadas/adjacentes para análise, mas não foi provada
a extensão completa desse objeto nem o conjunto total de animações.
Os campos ainda desconhecidos continuam sem interpretação definitiva.

## Alocação OAM

`Graphics_AllocateOam` limita o grupo a **31**. Interpreta o contador de
entradas como signed de oito bits: quando o bit alto está ativo, retorna
exatamente a sentinela lida de **`0x03006FE8`**, sem presumir NULL.

Nos demais casos, inicializa `next` com `0xFF`, cria ou prolonga a lista do
grupo usando heads em `0x03002BB0` e tails em `0x030065F0`, incrementa o
contador e retorna a entrada recém-alocada em `0x03003730`.
O campo de encadeamento está no offset `+6` do registro de oito bytes.

O alocador termina exatamente onde começa `Graphics_ProcessOam`, já
reconstruída. A auditoria concatena os dois binários e verifica **648 bytes
contínuos**, em **`0x081119F0..0x08111C78`**.

## Paleta e memset

`Graphics_LoadBgPalette` mantém o alias anterior **`Func_08114668`**, para
os chamadores já reconstruídos. Usa o offset de oito bits e trunca a
quantidade de entrada para 16 bits. Converte cada cor pelas três tabelas
RAM de 32 componentes em **`0x03003C40`**, escrevendo em `gBgPaletteBuffer`.
O inicializador já existente preenche essas tabelas com os valores
identidade `i`, `i << 5` e `i << 10`.

O endereço **`0x03003BE8`**, antes chamado `gColorState`, funciona aqui como
callback opcional, agora também nomeado `gPaletteCallback`. Quando presente,
recebe a **base completa do buffer**, offset e quantidade, inclusive quando
a quantidade é zero. A rotina sempre ativa **`gSystemFlags & 1`** ao terminar.

A chamada passa pela ponte original **`0x08116A28`**, que contém `BX r3`.
A declaração C de quatro argumentos coloca o callback no quarto registrador,
e a ponte encaminha os outros três argumentos a ele. Não se confundiu esse
endereço com a ponte equivalente da biblioteca de áudio em `0x0810A97C`.
Esses dois helpers originais não são contados como corpos C reconstruídos.

`Runtime_Memset` retorna o destino original. Para destinos alinhados em quatro
bytes e tamanhos maiores que três, replica o byte baixo em uma word e escreve
blocos de **16 bytes**, depois words de **quatro bytes**. Trata o restante
por bytes; destinos desalinhados usam o caminho de bytes inteiro.
A restrição vazia conserva o contador anterior ao decremento no teste da
cauda, reproduzindo inclusive o decremento final. Os **84 bytes** incluem
os dois zeros de alinhamento, terminando exatamente na base de dados
`0x0811855C`; nenhum byte dessas tabelas foi contado como código.

## Verificação e continuação

```powershell
.\.venv\Scripts\python.exe tools\match.py --target graphics_draw_sprite
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Cada `.text` é compilada, linkada no endereço original e comparada por inteiro,
incluindo literais e padding, sem relocations pendentes. A auditoria confere
os hashes atuais de fontes, headers, ferramentas, assembly e binários,
as fontes não modificadas dos compiladores e as restrições expandidas.
A rotina de áudio mantém seu perfil GCC 3.4.6 alternativo anterior.

Os 22 novos controles negativos recompilam alterações de frame/stride,
câmera e modo affine, bordas da tela, grupo OAM, sinal de transferência,
agrupamento e truncamento de tamanhos, capacidade e encadeamento OAM,
componentes e contagem da paleta, callback, sinalização e caminhos do memset.
Todos exigem reprovação na comparação com a ROM.

Evidências locais: `build/matching/summary.json`, relatórios individuais,
`build/verification.json`, `build/next/draw_flow.json`, `draw_tables.json`
e `build/next/audit_193.py`/`audit_193.json`.

A [etapa seguinte de animação](sprite_animation_matching.md) concluiu **`0x0810FD70`**,
seus doze comandos e a paleta OBJ. O [início do player `0x0810B4EC` e cinco serviços de áudio](music_player_start_matching.md) também têm matching. O matching ARM por função ainda precisa ser integrado a um
build completo da ROM. Execução por frame em emulador, extração completa de
assets e o port nativo para PC continuam pendentes.
