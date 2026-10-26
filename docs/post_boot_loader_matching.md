# Carregador de fundos e fase 0x080EFC88

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Validação local em 19/10/2026. Os nomes de funções e campos foram atribuídos
neste projeto a partir do comportamento observado.

## Resultado

As duas funções foram concluídas e integradas à produção:

| Função | Endereço USA | Instruções | Literais | Padding | Total |
|---|---|---:|---:|---:|---:|
| `PostBoot_LoadBackground` | `0x080EEDB4` | 502 | 56 | 6 | **564** |
| `PostBoot_Phase4` | `0x080EFC88` | 68 | 12 | 0 | **80** |

São **644 bytes completos idênticos à ROM**. O agregado atual tem **224 funções,
33.032 bytes iguais e 190 testes aprovados, sem testes pulados**.

O carregador usa agbcc GCC 2.9-arm-000512 com **`-O1 -mthumb-interwork`**,
fluxo explícito de registradores em GNU C e **treze restrições vazias**.
A fase usa `-O2 -mthumb-interwork` e C estruturado, sem inline assembly.
Esses perfis reproduzem os binários destas reconstruções; não estabelecem
as flags históricas de compilação do jogo.

## Carregamento dos fundos

O índice é truncado para oito bits e seleciona uma entrada de doze bytes
na tabela `0x08A4E33C`. O ID do recurso, em `entry+2`, é comparado como signed
de 16 bits. Valores negativos usam o ID padrão 98, lido de `0x08A4E338`.
O índice 10 chama `PostBoot_LoadSpecialBackground`,
em `0x080EF230`, e retorna pelo mesmo epílogo. Esse caminho está preservado
e incluído na comparação de bytes. O serviço especial e seus três auxiliares
agora têm matching na [etapa do callback `0x080F0040`](post_boot_phase21_matching.md).

No caminho comum, o carregador:

1. Limpa os dois bits de prioridade do controle do BG e combina a prioridade
   da entrada, preservando as duas escritas originais no shadow.
2. Obtém o recurso na tabela `0x0882323C`, descomprime seus tiles para o
   charblock selecionado pelos bits 2..3 e determina o screenblock pelos
   bits 8..12 do controle do BG.
3. Copia ou espelha o mapa, conforme o byte `entry+7`.
4. Ajusta o banco de paleta das entradas do mapa quando as posições de origem
   e destino são diferentes.
5. Transfere a paleta quando a quantidade de bancos é diferente de zero.
6. Zera a primeira cor do buffer BG, ativa o bit 0 de `gSystemFlags` e aplica
   os dois valores de scroll da entrada.

A cópia normal usa uma chamada `CpuSet` por linha, com quantidade de halfwords
equivalente a `width` e stride de destino de **32 halfwords**, ou 64 bytes.
A origem avança conforme a largura real do recurso.

No espelhamento, o ponteiro de origem avança por todos os tiles e o destino
recua dentro de cada linha. Cada entrada de 16 bits recebe **XOR `0x0400`**,
invertendo também o flip horizontal do próprio tile. O contador de coluna
é unsigned de oito bits; o de linha é unsigned de dezesseis bits.

O remapeamento de paleta usa:

```c
tile = (tile & 0x0FFF) | ((destinationPalette & 0xF) << 12);
```

Isso conserva o índice e os dois bits de flip do tile. O remapeamento visita
somente `width × height` entradas, com o mesmo stride de 32 halfwords.

Com `gSystemFlags & 0x10000`, a transferência passa por `0x08114668`:
origem da paleta mais `sourcePalette * 32` bytes, offset de destino
`(destinationPalette & 0xF) * 16` cores e quantidade `paletteCount * 16`
halfwords. No outro caminho, o DMA3 usa o offset de destino
`destinationPalette * 32` bytes e o bit de habilitação `0x80000000`.
Foi preservada a diferença entre o destino mascarado do serviço e o destino
sem essa máscara no caminho DMA. Há uma leitura de retorno do controle DMA.

## Fase seguinte

`PostBoot_Phase4` é a fase registrada por `0x080EFC30`. Ela compara o contador
local com `gPostBootTimeline[data->step]`. Quando o contador atinge ou supera
o limite, incrementa o passo, limpa no shadow de vídeo os bits dos BGs
indicados pelas entradas **0 e 2** do roteiro e agenda `PostBoot_Phase5`.

No fluxo iniciado com passo zero e seguido pelas fases já reconstruídas,
ela usa o quarto tempo da tabela: **72**. Os quatro primeiros valores
confirmados são `51, 59, 64, 72`.
O próximo ponteiro é **`0x080EFCD9`**, para o corpo Thumb em `0x080EFCD8`,
agora reconstruído na [continuação de fases e fade](post_boot_phases_matching.md).
Não foi inferido um limite completo da
tabela de tempos apenas a partir desses quatro acessos.

## Fontes e prova

- `src/post_boot_load_background.c`: reconstrução com matching integral.
- `src/post_boot_phase4.c`: fase em C estruturado com matching integral.
- `reference/post_boot_load_background.c`: referência algorítmica legível;
  **não tem matching e não é alvo do build de produção**.

O carregador conserva três words de stack para BG, ID e offset de scroll,
variáveis associadas a registradores e blocos C com labels. Os endereços
absolutos correspondem à ROM USA e aos símbolos já mapeados. As treze
restrições usam templates vazios: conservam os valores signed, a ordem
dos acessos, movimentos entre registradores e argumentos de chamadas.
**Nenhuma delas emite uma instrução.**

Todas as instruções são emitidas pelo compilador a partir de operações C.
Não há instruções ASM embutidas, arrays de opcodes, edição do assembly,
alterações no compilador, recorte de binário ou máscaras de diferenças.
O ELF do carregador possui somente a seção alocável `.text`, com os 564 bytes
comparados. Não há constantes auxiliares ou novos metadados fora dessa região.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target post_boot_load_background
.\.venv\Scripts\python.exe tools\match.py --target post_boot_phase4
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os novos controles negativos alteram o fallback signed, o índice especial,
o XOR do espelhamento, o stride das linhas, a preservação dos bits do tile,
a seleção do serviço de paleta, o bit de habilitação do DMA, o limite de
tempo, o par de BGs e o próximo callback. Todos exigem que a recompilação
seja rejeitada pelo comparador.

Relatórios em `build/matching/<id>/report.json`, `build/matching/summary.json`
e `build/verification.json`. A análise dos 570 bytes de instruções, 68 de
literais e seis de padding desta etapa está em
`build/next/loader_phase4_flow.json`.
A auditoria também verifica os endereços literais contra o mapa de símbolos
e todo o intervalo contínuo `0x080EE654..0x080F0910`, com 96 funções e
8.892 bytes, incluindo as fases seguintes e o encerramento.

A [continuação de fases, fade e transferência de tiles](post_boot_phases_matching.md)
acrescentou 21 funções e 1.456 bytes, incluindo o callback `0x080EFCD8`.
A etapa do [callback seguinte e fundo especial](post_boot_phase21_matching.md)
concluiu `0x080F0040`, `0x080EF230` e outras quatorze funções.
A etapa do [callback `0x080EEA7C`, sprites e scroll](post_boot_phase30_matching.md)
concluiu outras dezesseis funções e 1.724 bytes.
O [callback `0x080F02EC` e o encerramento](post_boot_phase38_matching.md) também têm matching.
O [desenho de sprites, alocador OAM, serviço de paleta e memset](graphics_draw_sprite_matching.md) também têm matching.
A [animação `0x0810FD70`, seus doze comandos e a paleta OBJ](sprite_animation_matching.md) também têm matching.
O [início do player e cinco serviços de áudio](music_player_start_matching.md) também têm matching.
Permanecem externos o processador de músicas `0x0810A724`, inicialização de áudio e outros wrappers/helpers.
O matching ainda é por função; faltam o build
completo da ROM, a execução por frame em emulador e o port nativo de PC.
