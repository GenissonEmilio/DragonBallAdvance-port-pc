# Inicialização de som e serviços CGB com matching integral

Verificado em 19/10/2026 sobre a ROM USA `BDVE`, revisão 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

`Sound_Initialize` e `Sound_Extend` foram reconstruídas em C/GNU C. A continuação também
concluiu o callback vazio e os serviços CGB de parada, frequência e volume. São **seis funções
e 884 bytes novos**, todos iguais à ROM após compilação e link no endereço original.
O agregado atual tem **224 funções, 33.032 bytes idênticos e 190 testes aprovados, sem skips**.

| Função | Endereço USA | Instruções | Literais | Padding | Total | Restrições vazias expandidas |
|---|---|---:|---:|---:|---:|---:|
| `Sound_Initialize` | `0x0810B134` | 184 | 64 | 0 | 248 | 0 |
| `Sound_Extend` | `0x0810AFF0` | 200 | 80 | 0 | 280 | 1 |
| `Sound_Dummy` | `0x0810C224` | 2 | 0 | 2 | 4 | 0 |
| `Cgb_Stop` | `0x0810B834` | 60 | 16 | 4 | 80 | 0 |
| `Cgb_CalculateFrequency` | `0x0810B78C` | 154 | 12 | 2 | 168 | 16 |
| `Cgb_UpdateVolume` | `0x0810B884` | 104 | 0 | 0 | 104 | 20 |
| **Total** | | **704** | **172** | **8** | **884** | **37** |

Os nomes são descritivos, atribuídos pelo projeto. Os fontes estão em `src/`, com APIs em
`include/audio.h` e endereços vinculados ao hash em `config/functions.usa.json` e
`config/symbols.usa.json`. Os callbacks ainda originais continuam explicitamente identificados.

## Compilação e limites da evidência

As seis funções usam o agbcc GCC 2.9-arm-000512, commit
`da598c1d918402c42c0c0d7128ba14567f3175e9`. Cinco usam `-O2 -mthumb-interwork`;
`Cgb_Stop` acrescenta **`-fprologue-bugfix`**, uma opção já existente no compilador selecionado.
O fonte local `gcc/toplev.c` descreve essa opção como prevenção do salvamento desnecessário
de LR; `gcc/thumb.c` contém sua implementação. Ela elimina o prólogo/epílogo excedente dessa
função folha, permitindo o match completo de 80 bytes. Nenhum fonte ou binário do compilador
foi modificado. Esta é uma configuração compatível, sem prova das flags ou SDK históricos.

`Sound_Initialize`, `Sound_Dummy` e `Cgb_Stop` não usam asm. As outras três usam **37 templates
vazios** de GNU C no total, contados após expansão das macros no `.i`. Eles restringem
registradores e duração de valores, sem emitir instruções. `Cgb_UpdateVolume` também usa dois
labels e `goto` em C. Não há novos metadados de labels, opcodes inseridos, funções naked,
edição de assembly, relocations pendentes ou bytes excluídos da comparação.
As versões mais diretas de frequência e volume em `reference/` são referências de leitura,
sem matching e fora da produção.

Um detalhe de `Sound_Extend` exige um símbolo absoluto: a ROM carrega por literal o valor
zero em `0x0810B100` antes de gravar `maxLines`. A atribuição direta de zero em C gerava um
`MOV`, alterando instrução e literal pool. `gSoundDefaultMaxLines` é definido pelo linker
com **valor absoluto zero**, e o C converte seu endereço em inteiro. Isso preserva o `LDR`
original sem ler memória no endereço zero. É um recurso de reconstrução do layout; o nome
não representa uma variável original identificada. O literal também participa da comparação.

## Sound_Initialize: buffers, DMA e callbacks

A função começa zerando o lock. Se o bit de repetição `0x02000000` estiver ativo em DMA1 ou
DMA2, grava `0x84400004` no respectivo controle de 32 bits. Depois configura os controles
de 16 bits para `0x0400`, habilita som com `SOUNDCNT_X = 0x008F`, grava `0xA90E` em
`SOUNDCNT_H` e preserva os seis bits baixos do byte `0x04000089`, ativando seu bit `0x40`.
Larguras e ordem dessas escritas estão preservadas.

Os endereços DMA apontam para dois buffers do objeto recebido, offsets `+0x350` e `+0x980`,
com destinos FIFO A (`0x040000A0`) e FIFO B (`0x040000A4`). A função instala o ponteiro global
e usa `Bios_CpuSet` com controle `0x050003EC` para zerar **4.016 bytes**, por preenchimento
de palavras. Define oito canais PCM e volume mestre 15.

O callback `+0x38` recebe `Sound_UpdateTrack`, em `0x0810AA00`, ainda original. Os callbacks
`cgbMain`, `stopCgb`, `+0x30` e `+0x3C` recebem `Sound_Dummy`. A tabela de 36 comandos é
copiada por `Sound_CopyCommandTable` (`0x0810A514`, ainda original), e seu endereço é instalado
no objeto. Por fim, chama `Sound_SetFrequency(0x40000)` e publica o lock `0x68736D53`.
Essa frequência seleciona 224 amostras por frame na tabela observada. A inicialização externa
aplica posteriormente o modo `0x0095FC00`, que seleciona 264; os dois momentos são distintos.

Para o objeto global usado nesta ROM, o layout observado é:

| Região | Início | Fim exclusivo | Tamanho |
|---|---|---|---:|
| Header e 12 registros PCM | `0x03000CC0` | `0x03001010` | `0x350` |
| Buffer A | `0x03001010` | `0x03001640` | `0x630` |
| Buffer B | `0x03001640` | `0x03001C70` | `0x630` |
| Tabela de 36 comandos | `0x03001C70` | `0x03001D00` | `0x90` |
| Quatro registros CGB | `0x03001D00` | `0x03001E00` | `0x100` |

Os primeiros três intervalos formam exatamente o objeto zerado de `0xFB0` bytes.
O primeiro player começa em `0x03001E00`, conforme a tabela de players já verificada.

## Sound_Extend: instalação dos canais CGB

As escritas iniciais nos registradores sonoros acontecem **antes da verificação do lock**;
mesmo um lock inválido não evita essas escritas. A função habilita som, limpa o controle
estéreo, escreve os valores de parada nos canais, desativa wave e grava `0x77` no byte
`0x04000080`. Só depois exige lock `0x68736D53` e o incrementa durante a instalação.

Ela substitui nove entradas na tabela RAM. Os valores da última coluna incluem o bit Thumb:

| Índice | Função instalada | Ponteiro | Matching em produção |
|---:|---|---|---|
| 8 | `SoundCommand_BFAC` | `0x0810BFAD` | C/GNU C; [memória](music_memory_commands.md) |
| 17 | `SoundCommand_AC68` | `0x0810AC69` | Assembly separado; [LFO/modulação](music_modulation_commands.md) |
| 19 | `SoundCommand_AC7C` | `0x0810AC7D` | Assembly separado; [LFO/modulação](music_modulation_commands.md) |
| 28 | `SoundCommand_C104` | `0x0810C105` | C; [comandos estendidos](music_memory_commands.md) |
| 29 | `SoundCommand_AC00` | `0x0810AC01` | Assembly separado; [término de notas](music_end_tie_hybrid.md) |
| 30 | `Sound_SetFrequency` | `0x0810B22D` | Sim, etapa anterior |
| 31 | `MusicTrack_Stop` | `0x0810A98D` | Sim, etapa anterior |
| 32 | `Music_FadeOutBody` | `0x0810B611` | Sim, continuação de áudio |
| 33 | `MusicTrack_UpdateVolumePitch` | `0x0810B6D9` | Sim, continuação de áudio |

Instala o buffer CGB recebido, `Cgb_Update` (`0x0810B8EC`, agora com [matching](audio_update_matching.md)), `Cgb_Stop` e
`Cgb_CalculateFrequency`. Define `maxLines` como zero e limpa os 256 bytes dos canais com
`Bios_CpuSet(…, 0x05000040)`. Cada registro tem 64 bytes: o campo `+1` recebe os tipos
1, 2, 3 e 4; o campo `+0x1C` recebe as máscaras de roteamento `0x11`, `0x22`, `0x44`, `0x88`.
Ao terminar, restaura o lock capturado.

## Serviços CGB reconstruídos

`Cgb_Stop` recebe um byte. Os casos 1 e 2 escrevem volume 8 e trigger `0x80` nos dois canais
quadrados; o caso 3 desativa wave. **Qualquer outro valor**, inclusive zero, segue o caminho
de parada do ruído. Esse default está preservado.

`Cgb_CalculateFrequency` também recebe canal, nota e fração como bytes. Para canal 4, notas
até 20 usam índice zero; as demais subtraem 21 e limitam o índice a 59 na tabela de ruído
`0x08A67688`. Nos outros canais, notas até 35 zeram nota e fração; as demais subtraem 36,
com limite 130 e fração 255 quando excedido. O mapa em `0x08A675EC` seleciona período e
deslocamento. Os 12 períodos em `0x08A67670` são **signed de 16 bits**, negativos. A fórmula é:

```c
base = periods[map[key] & 15] >> (map[key] >> 4);
next = periods[map[key + 1] & 15] >> (map[key + 1] >> 4);
frequency = base + (((next - base) * fine) >> 8) + 2048;
```

As leituras signed e os deslocamentos aritméticos fazem parte do match. Os intervalos lidos
foram conferidos na ROM; isso não estabelece exclusivamente os limites globais de todas as tabelas.

`Cgb_UpdateVolume` lê direita/esquerda em `+2/+3`. Se um lado tiver pelo menos o dobro do
outro, escolhe pan `0x0F` ou `0xF0` e limita `(direita + esquerda) >> 4` a 15. No caminho
equilibrado escolhe `0xFF` e **não aplica esse limite**. Calcula o envelope em `+0x19` como
`(sustain * volume + 15) >> 4`, armazenado em byte, e aplica a máscara `+0x1C` ao pan `+0x1B`.

Exemplo estático de largura/branch: direita = esquerda = sustain = 255, máscara `0x11`,
produz volume 31 e envelope 239 após truncamento para byte. Com apenas um lado em 255,
o volume é 15 e o envelope 240. Não foi demonstrado que esses valores extremos sejam
alcançáveis pelo jogo; são exemplos aritméticos, sem execução em emulador.

## Verificação e próximos passos

```powershell
.\.venv\Scripts\python.exe tools\match.py --target sound_initialize
.\.venv\Scripts\python.exe tools\match.py --target sound_extend
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A suíte passou com **190 testes, nenhum pulado**. Dez novos testes exercitam **28 alterações
negativas recompiladas**: DMA, limpeza e buffers, canais e volume, callbacks e slots de comandos,
lock, zero absoluto, limites das notas, leitura signed, interpolação, pan, clamp e arredondamento.
Cada candidato alterado precisa reprovar por diferença de bytes.

Além dos 884 bytes novos, a auditoria verificou três regiões por concatenação de binários
completos: `0x0810B78C..0x0810B8EC` (352 bytes), `0x0810B134..0x0810B368` (564) e
`0x0810C224..0x0810C90C` (1.768). Funções de etapas anteriores não foram recontadas.
Evidências locais: relatórios em `build/matching/`, `build/verification.json`,
`build/next/sound_flow.json`, `sound_tables.json` e `audit_219.py`/`audit_219.json` (marco anterior).
A continuação atual foi auditada em `audit_222.py`/`audit_222.json`.
A auditoria confere hashes atuais, seções completas, restrições vazias e fontes inalterados
dos compiladores; o pipeline não pós-processa o assembly.

A continuação concluiu [`Cgb_Update` e dois auxiliares de música](audio_update_matching.md).
[`MusicPlayer_Update` (`0x0810A724`)](music_player_update_hybrid.md) foi concluído em C nativo e assembly GBA separado. Continuam pendentes
a atualização de trilha (`0x0810AA00`), comandos restantes e o mixer que continua em RAM. A entrada `0x0810A084`
continua sem delimitação do mixer inteiro. Ainda faltam integração, gameplay, recursos,
camada nativa e comparação comportamental por frame; veja [estado do port](port_status.md).

A continuação concluiu a [cópia da tabela, limpeza, remoção e fim de trilha](audio_helpers_matching.md),
com 156 bytes novos e nove auxiliares ligados ao C nativo.
