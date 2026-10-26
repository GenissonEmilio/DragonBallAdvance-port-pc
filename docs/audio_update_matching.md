# Atualização CGB e os primeiros candidatos de MusicPlayer_Update

Continuação: [`MusicPlayer_Update` foi concluída pela divisão C nativo/assembly GBA](music_player_update_hybrid.md).
O assembly tem 616 bytes iguais; o C nativo é validado por comportamento. Os candidatos ARM C
abaixo continuam sem matching e não foram reclassificados.

Validação em 19/10/2026 sobre a ROM USA `BDVE`, revisão 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

**`Cgb_Update` foi reconstruída integralmente em GNU C: 1.100/1.100 bytes iguais à ROM.**
Também foram concluídos dois auxiliares chamados pelo processador de músicas. A função
`MusicPlayer_Update` tinha, nesta etapa, um candidato ARM C **sem matching e fora da produção C**; a continuação está indicada acima.

| Função concluída | Endereço USA | Instruções | Literais | Padding | Total |
|---|---|---:|---:|---:|---:|
| `Cgb_Update` | `0x0810B8EC` | 1.008 | 76 | 16 | 1.100 |
| `Music_FadeOutBody` | `0x0810B610` | 194 | 4 | 2 | 200 |
| `MusicTrack_UpdateVolumePitch` | `0x0810B6D8` | 180 | 0 | 0 | 180 |
| **Total novo** | | **1.382** | **80** | **18** | **1.480** |

O agregado contém **224 funções, 33.032 bytes idênticos e 190 testes aprovados, sem skips**.
Esse total não inclui o candidato de `MusicPlayer_Update`. Os fontes verificados estão em `src/`;
as referências mais diretas do algoritmo estão em `reference/` e não participam da produção.
O candidato pendente está em `nonmatching/music_player_update.c` e `config/candidates.usa.json`.

## Como o match foi obtido

As três funções usam o agbcc GCC 2.9-arm-000512, commit
`da598c1d918402c42c0c0d7128ba14567f3175e9`, sem alterações nos fontes ou no executável.
`Cgb_Update` usa **`-O1 -mthumb-interwork`**; os dois auxiliares usam o perfil padrão
`-O2 -mthumb-interwork`. São configurações compatíveis, sem identificação exclusiva das flags
ou do SDK históricos do jogo.

A reconstrução explicita registradores e fluxo em GNU C. `Cgb_Update` usa **19 restrições de
template vazio**, e cada auxiliar usa duas: **23 no total**, contadas no C pré-processado.
Nenhum template contém instruções. Quinze endereços de labels C conservam fronteiras de blocos
do atualizador CGB: **60 bytes em `.debug_dbaa_flow`, não alocados e não executáveis**.
Eles não entram na imagem da ROM. A comparação abrange a `.text` inteira, e a auditoria verifica
que nenhuma outra seção alocada não vazia tenha ficado fora dela. Os endereços de dados
numéricos evitam duas palavras `.rodata` redundantes que agbcc `-O1` emitia ao usar
os símbolos globais. A ferramenta também passou a rejeitar seções alocadas adicionais.

Um zero em registrador, aparentemente redundante no caminho de ataque, também existe na ROM.
Uma variável de registrador `volatile` com escopo curto conserva essa escrita em C. Seu espaço
temporário de pilha pode ser reutilizado pelo spill do callback, cujo escopo também é curto.
O resultado reproduz o frame de **28 bytes** e o spill em `sp+24`, incluindo os quatro bytes
que ainda diferiam antes desse ajuste de escopos.

Não há funções naked, opcodes inseridos como dados, assembly pós-processado, relocations
mascaradas ou bytes recortados para obter igualdade. As versões em `reference/` são excluídas
e não têm alegação de equivalência binária.

## Processamento dos quatro canais CGB

`Cgb_Update` obtém `SoundInfo` pelo ponteiro global. O byte `SoundInfo+0x0A` percorre os estados
14 até 0, retornando a 14. A função visita quatro registros CGB de **64 bytes** cada e só processa
os que têm algum bit de `status & 0xC7` ativo.

O mapeamento dos ponteiros de acesso ao hardware é:

| Canal | Auxiliar 0 | Comprimento/duty | Volume/envelope | Frequência baixa | Controle/trigger |
|---:|---|---|---|---|---|
| 1 | `0x04000060` | `0x04000062` | `0x04000063` | `0x04000064` | `0x04000065` |
| 2 | `0x04000061` | `0x04000068` | `0x04000069` | `0x0400006C` | `0x0400006D` |
| 3 | `0x04000070` | `0x04000072` | `0x04000073` | `0x04000074` | `0x04000075` |
| 4 | `0x04000071` | `0x04000078` | `0x04000079` | `0x0400007C` | `0x0400007D` |

Os auxiliares `0x61` e `0x71` são placeholders armazenados pelo fluxo; não foram interpretados
como registradores independentes. Os usos do ponteiro auxiliar são condicionados ao canal.

O início de nota (`0x80`) prepara estado e flags de atualização, chama o serviço de volume e
configura comprimento, duty/sweep ou ruído. Para wave, compara os ponteiros em `+0x24/+0x28`:
somente quando mudam, seleciona o banco e copia **quatro palavras de 32 bits** para
`0x04000090..0x0400009C`, atualizando o ponteiro do recurso carregado.

Os dois bits baixos do status selecionam ataque, decay, sustain ou release. Os caminhos de
parada (`0x40`) e eco (`0x04`) preservam as transições e o wrap dos campos de byte. O eco usa
`(echoVolume * envelopeGoal + 255) >> 8`; seus contadores e a comparação do decay preservam
a interpretação signed de oito bits. Quando o contador global chega a zero, o processamento
do envelope se repete uma vez para cada canal naquele ciclo.

A frequência dos canais 1–3 pode ser arredondada quando `type & 8` está ativo. O byte de PWM
em `0x04000089` seleciona `(freq + 2) & 0x7FC`, `(freq + 1) & 0x7FE` ou nenhuma correção.
O canal de ruído conserva o bit `0x08` já presente no registrador antes de combinar a frequência.

O roteamento estéreo em `0x04000081` mantém os canais fora da máscara do registro e aplica seu
pan calculado. Wave usa a tabela em `0x08A676C4`; os primeiros 16 bytes foram conferidos, sem
alegação de limite global exclusivo da tabela. Os demais canais escrevem envelope e trigger,
incluindo a escrita adicional condicionada ao sweep do canal 1. As flags `+0x1D` são limpas ao final.

## Auxiliares de música concluídos

`Music_FadeOutBody` respeita o intervalo e o contador de 16 bits do fade. A cada vencimento,
altera o nível em passos de 16. O modo `0x02` aumenta o nível até 256. No fade de saída, ao
atingir zero, para as trilhas e distingue pausa temporária (`0x01`) de encerramento do status.
Enquanto o fade continua, atualiza `volumePublic = fadeLevel >> 2` nas trilhas ativas e marca
as alterações de volume. O wrap do contador e o teste signed do nível foram preservados.

`MusicTrack_UpdateVolumePitch` processa as flags `0x01` e `0x04`. Calcula o volume a partir de
volume público e volume da trilha, aplica modulação de amplitude ou pan conforme o tipo,
limita pan a `[-128, 127]` e produz volumes direito/esquerdo. O pitch combina bend, alcance,
afinação, transposições, fração pública e modulação, mantendo os deslocamentos e truncamentos
da ROM. Ao terminar, aplica `status &= 0xFA`, preservando as flags de atualização dos canais.

Os campos agora têm tipos e offsets explícitos em `include/audio.h`. Um probe ARM verificou
**39 tamanhos/offsets**, incluindo `MusicTrack = 80 bytes`, `MusicPlayer = 64`, contador e nível
de fade em `+0x26/+0x28`, primeiro canal em `track+0x20` e comandos em `track+0x40`.
Isso não torna esses layouts de ponteiros de 32 bits diretamente utilizáveis num processo PC de 64 bits.

## Limite do candidato ARM C de MusicPlayer_Update

A região solicitada é `0x0810A724..0x0810A98C`: **602 bytes de código, dois de padding e
12 de literais**. Ela contém a entrada do player e um `BX r3` em `0x0810A97C`, também chamado
como ponte por outras rotinas.

O candidato C reconstrói lock, encadeamento de players, fade, acumulação de tempo, interpretação
dos comandos, running status, duração das notas, LFO e atualização de volume/pitch dos canais.
Preserva detalhes como o teste antes de truncar o acumulador para 16 bits, entrada no primeiro
registro antes do teste da contagem e o teste signed do ponteiro no fim do segundo percurso.
O cálculo do auxiliar `0x0810A9D0`, que recebe entradas por `r4/r5`, foi expresso em C inline
para evitar fingir que essa chamada usa a ABI C convencional.

**Esse candidato ainda não passou no gate.** A comparação integral atual retorna:

| Compilador do candidato | Tamanho gerado / referência | Bytes diferentes |
|---|---:|---:|
| agbcc GCC 2.9, `-O2 -mthumb-interwork` | 728 / 616 | 686 |
| GCC 3.4.6, perfil alternativo registrado | 708 / 616 | 686 |
| GCC 8.2.1, ARM7TDMI Thumb com shrink wrapping | 816 / 616 | 798 |

Os três já diferem na primeira instrução. Na ROM, o lock é verificado antes de salvar a pilha.
Depois há um `PUSH {r0, lr}`, chamada do próximo player, `POP {r0}` e só então salvamento dos
registradores do processamento principal. O retorno restaura oito registradores num único POP,
recompõe `r8..r11` e compartilha a ponte `BX r3`. Há ainda oito instruções `TST` na região.
Os candidatos testados conservam outras formas de entrada, saída e corpo.

A organização é compatível com a rotina em assembly `MP2KPlayerMain` da
[biblioteca m4a do SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
O [atualizador CGB nesse projeto](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a.c)
também ajudou na interpretação dos campos. Isso é uma referência de implementação e não prova
do arquivo-fonte ou SDK histórico da Dimps. A prova binária desta etapa vem da ROM local.

A candidata ARM C continua `NONMATCHING`. A continuação adotou, com escolha explícita do
usuário, C nativo para o port e assembly separado para a igualdade binária GBA. Esse assembly
não é contado como C; veja [a solução e as verificações](music_player_update_hybrid.md).

## Reprodução, evidências e estado do port

```powershell
.\.venv\Scripts\python.exe tools\match.py --target cgb_update
.\.venv\Scripts\python.exe tools\match.py --target music_fade_out_body
.\.venv\Scripts\python.exe tools\match.py --target music_track_update_volume_pitch
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Candidato pendente: retorna 1 por diferença de bytes.
.\.venv\Scripts\python.exe tools\match.py --function-map config\candidates.usa.json --target music_player_update --out-dir build\candidate_music_update
```

Os **190 testes passaram sem skips**. Nove testes novos fazem **25 mutações recompiladas** de
contadores, registradores, cópia wave, estados e comparações signed, eco, PWM, estéreo, fade,
clamps, modulação e flags. Um décimo teste confirma que o candidato pendente é excluído da
produção e reprovado pela comparação inteira. O décimo primeiro teste novo acrescenta
dados globais em `.data`, `.rodata` e `.bss`; todos precisam ser rejeitados pelo gate.

A auditoria também confere **1.832 bytes contínuos** em `0x0810B610..0x0810BD38`; juntando
as cinco funções anteriores, são **11 funções e 2.428 bytes contínuos** desde `0x0810B3BC`.
Evidências locais: `build/matching/summary.json`, `build/verification.json`,
`build/next/update_flow.json`, `update_evidence.json`, `audio_layout_probe.json` e
`audit_222.py`/`audit_222.json`.

O atualizador CGB e os dois auxiliares ampliam a base de áudio comprovada. Continuam pendentes
os comandos restantes, cópia da tabela, limpeza e auxiliares, além do mixer
que prossegue em RAM. Ainda faltam integração, gameplay, recursos, backend nativo e validação
com execução por frame. **Ainda não existe executável Windows jogável.** O quadro completo está
em [port_status.md](port_status.md); não foi calculado um percentual de conclusão do port.
