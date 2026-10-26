# Compilador compatível e matching em C

Verificação inicial em 16/10/2026, atualizada em 19/10/2026 sobre a ROM USA `BDVE`, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

## Resultado verificado

O conjunto de produção agora contém **224 funções com 33.032/33.032 bytes iguais**.
O agbcc atende 222 alvos: `-O2 -mthumb-interwork` para 216 e
`-O1 -mthumb-interwork` para três reconstruções de fluxo de registradores: a fila de mapas,
o carregador de fundos da abertura e `Cgb_Update`. `Runtime_Memset` usa `-O2` sem interworking.
`Cgb_Stop` usa `-O2 -mthumb-interwork -fprologue-bugfix`, uma opção existente no agbcc
selecionado, sem modificação do compilador. Veja [inicialização de som](sound_initialization_matching.md)
para os 884 bytes desta etapa, as 37 restrições vazias e o símbolo absoluto de valor zero.
`Audio_UnlinkChannel` compartilha o perfil com `-fprologue-bugfix`.
A parada de trilha e `MusicEvent_Fine` usam GCC 3.4.6 como compilador alternativo compatível; veja
[music_track_stop_matching.md](music_track_stop_matching.md). Inclui o loop principal (340 bytes), a inicialização interna
(1.764 bytes), tarefas e os caminhos gráficos. As tabelas estão em [main_loop.md](main_loop.md)
e [initialization_graphics.md](initialization_graphics.md). O primeiro matching, que
estabeleceu a configuração, segue abaixo.

`src/state_counter.c`, compilado com **GCC 2.9-arm-000512 para Thumb/elf**, reconstruído pelo
projeto `pret/agbcc`, e flags **`-O2 -mthumb-interwork`**, reproduz **28/28 bytes** da ROM:

- Início: `0x0800144C`.
- Fim exclusivo das instruções: `0x08001464` (24 bytes).
- Literal de endereço: `0x08001464..0x08001468` (4 bytes, valor `0x02029F30`).
- Fim exclusivo da região comparada: `0x08001468`.
- Diferenças: **0**, após link completo, sem máscaras de relocations.
- SHA-256 de referência e candidato:
  `f93241a68d6fafa76044ba489b5f3cc9040a8e9036cd8d1932e0d22b50388d76`.

O C é convencional: uma view parcial de struct, uma condição e um incremento unsigned de
32 bits. Não usa inline assembly, registradores fixos, instruções emitidas como dados,
função naked nem edição da saída do compilador. A ROM é lida para identificação e comparação;
não é usada para gerar o assembly ou o candidato.

O inteiro em `+0x10` e a flag em `+0x22` têm comportamento verificado, mas seus nomes originais e
significado no jogo continuam desconhecidos. A escolha unsigned preserva o wrap de 32 bits;
essa instrução isolada não prova se o tipo original era signed ou unsigned.

## O que se pode concluir sobre o compilador original

Foi identificado um **toolchain compatível com a geração original**: a família Nintendo/Cygnus
GCC 2.9-arm-000512 (`agbcc`). A evidência é experimental: o C recompilado gera exatamente a mesma
sequência, prólogo, epílogo interworking, branch e literal. A versão reportada pelo compilador
selecionado consta em `gcc/version.c` do código-fonte pinado abaixo.

Isso não identifica exclusivamente o executável histórico usado pela Dimps, a revisão exata
do SDK nem todas as flags do projeto. Não foram encontrados metadados originais que os
declarem, e versões/opções distintas podem gerar os mesmos bytes de uma função pequena.
O nome e a versão acima identificam o compilador que conseguimos verificar, não uma assinatura
textual encontrada dentro da ROM.

Resultados dos controles com o mesmo C e link no mesmo endereço:

| Compilador/configuração | Tamanho extraído | Match da região inteira |
|---|---:|---|
| agbcc `-O0 -mthumb-interwork` | 40 bytes | Não |
| agbcc `-O1 -mthumb-interwork` | 28 bytes | Sim |
| agbcc `-O2 -mthumb-interwork` | 28 bytes | Sim |
| agbcc `-O3 -mthumb-interwork` | 28 bytes | Sim |
| agbcc `-Os -mthumb-interwork` | 28 bytes | Sim |
| agbcc `-O2`, sem interworking | 28 bytes | Não, 3 bytes diferentes |
| GCC ARM 8.2.1 `-O2 -mthumb-interwork -mcpu=arm7tdmi -ffreestanding -fno-builtin` | 24 bytes | Não |

Assim, **`-O2` é uma configuração reproduzível escolhida, não uma flag histórica deduzida
exclusivamente deste resultado**. Os 216 alvos de produção com agbcc `-O2 -mthumb-interwork` dão match com essa configuração; a fila de mapas, o carregador de fundos da abertura e `Cgb_Update` usam `-O1`.
A matriz acima mede apenas a primeira função pequena. Os resultados locais desse experimento
estão em `build/compiler_matrix/results.json`.

O bootstrap em C reproduz `0x08001424..0x08001440` (28 bytes): duas
chamadas, escrita do byte 2 em `0x02029F38`, outra chamada e retorno. Foi necessário tipar os
símbolos externos como Thumb (`.thumb_set`); um endereço absoluto NOTYPE no linker moderno
gera veneers de interworking e altera chamadas. O bootstrap foi integrado como alvo de produção
`game_bootstrap`. O arquivo auxiliar `extern_symbols.s` declara esses tipos e endereços;
não contém instruções ou cópias de código da ROM.

O GNU as moderno acrescenta NOP Thumb `0x46C0` em certos finais de seção, enquanto os trechos
originais correspondentes têm zeros. O build fornece `config/gas_padding.s` como segundo
input do assembler: contém apenas `.text` e `.balign 4, 0`. O linker também alinha com zeros.
Esse ajuste de layout não edita o `.s` gerado pelo compilador e não substitui instruções em C.
O padding é incluído no candidato e na comparação; não é recortado ou ignorado.

As novas rotinas DMA exigem conservar a forma dos escopos dos macros C: para esse compilador,
blocos simples e `do/while (0)` podem produzir alocações e loops diferentes. A implementação
verificada está em `include/hardware.h`. `Graphics_ProcessOam` usa uma barreira GNU C de
template vazio e entrada `r` para preservar um contador crescente. Ela não emite instruções
e é registrada em `compiler_barriers`. `Func_08002AA8` acrescenta duas restrições vazias:
um vínculo do valor a `r2` e uma dependência que conserva o cálculo do índice do bit.
`Func_08001BE4` usa três restrições vazias para os zeros independentes, o endereço
de um local e o destino EEPROM em `r5`; detalhes em [save_header_matching.md](save_header_matching.md).
São ajustes explícitos de GNU C, sem instruções dentro dos templates. Não há bytes de código
copiados da ROM no candidato; o assembly gerado nunca é pós-processado.

## Reprodução no Windows

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_matching.ps1
.\.venv\Scripts\python.exe tools\setup_gcc346.py
.\.venv\Scripts\python.exe tools\match.py
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O setup mantém downloads e programas em `tools/local/`; não instala componentes no sistema
nem altera permanentemente o PATH. Os arquivos grandes estão ignorados pelo Git. O script
interrompe a instalação se o SHA-256 dos arquivos não corresponder ao registrado.

O matching executa estes passos, sem manipular o assembly produzido:

1. Verificar o SHA-1 exato da ROM USA.
2. Pré-processar o C com `arm-none-eabi-gcc` 8 (`-E -P -nostdinc`). Este GCC não gera o código
   ARM do candidato; apenas resolve o include local.
3. Compilar o `.i` para `.s` com agbcc e as flags do alvo: `-O2 -mthumb-interwork`
   por padrão, `-O1 -mthumb-interwork` para a fila de mapas, o carregador de fundos da abertura
   e `Cgb_Update`; a parada de trilha
   seleciona o perfil `gcc346`, com suas nove flags registradas. `Runtime_Memset`
   usa agbcc `-O2` sem interworking para conservar seu retorno `POP ... pc`.
4. Montar com GNU as para ARM7TDMI e alinhamento explícito com zeros; linkar no endereço
   original, com globais e funções externas resolvidas pelo mapa da ROM USA.
5. Conferir endereço da seção, ausência de relocations e integridade do assembly gerado.
6. Extrair `.text` inteira, incluindo literais e padding; comparar tamanho e todos os bytes com a ROM.
7. Registrar hashes dos fontes, headers, compilador, assembly e configuração de link, comandos e
   resultado em `build/matching/<id>/report.json` e `build.log`. `--all` gera ainda `summary.json`.

Retorno 0 = match; 1 = diferença; 2 = erro. Os testes negativos mudam o incremento para +2,
o destino de uma chamada e um controle DMA em cópias do C e exigem diferenças após recompilar/linkar.
O setor de leitura do header EEPROM e o deslocamento do tamanho do tile dos sprites
de fundo e a máscara circular da fila de mapas também são alterados em controles negativos.
Há também controles negativos do handshake, da tabela serial e das máscaras de áudio,
rejeição de perfil de compilador desconhecido, ROM/mapa de hash errado e relatórios antigos no agregado.
Os 190 testes passaram localmente, sem skips. Nenhum fonte de produção é alterado pelos testes.

`--function-map` aceita um manifesto de candidatos separado, como `config/candidates.usa.json`; ele é repassado aos subprocessos de `--all` e seu hash vai para o relatório.
O manifesto de produção permanece `config/functions.usa.json`.

## Proveniência das ferramentas

- [agbcc](https://github.com/pret/agbcc), commit
  `da598c1d918402c42c0c0d7128ba14567f3175e9`, compilado nativamente no Windows sem alterações
  nos fontes. [Versão declarada](https://github.com/pret/agbcc/blob/da598c1d918402c42c0c0d7128ba14567f3175e9/gcc/version.c).
- [GCC 3.4.6 oficial](https://gcc.gnu.org/ftp/gcc/releases/gcc-3.4.6/), sem alterações nos
  1.816 arquivos regulares do pacote-fonte. Construído fora da árvore de fontes com Git Bash
  e w64devkit; somente headers gerados de configuração do host recebem ajustes MinGW.
  Não identifica o compilador histórico da rotina de biblioteca.
- Host: [w64devkit 2.10.1](https://github.com/skeeto/w64devkit/releases/tag/v2.10.1), GCC 16.2.0 e
  GNU Make 4.4.1. Esse GCC constrói a ferramenta Windows; não compila o C do jogo para GBA.
- Assembler/linker/extractor: GNU Arm Embedded 8-2018-q4-major, GCC 8.2.1 e GNU binutils 2.31.51.20181213,
  [distribuição Windows preservada pelo STM32duino](https://github.com/stm32duino/arm-none-eabi-gcc/releases/tag/8-2018-q4-major).
- Endereços, URLs e SHA-256 dos arquivos de ferramentas estão em `config/matching.json`.

Não é necessário Docker nem WSL para este fluxo. A instalação do Docker presente na máquina
não foi usada para produzir o matching.

A etapa de serviços e fundos está em [background_processors_services.md](background_processors_services.md).
A fila de mapas foi concluída em [background_queue_matching.md](background_queue_matching.md).
A etapa de [tarefas e memória](tasks_memory_matching.md) acrescentou dez alvos com `-O2`,
uma restrição vazia na criação, um clobber vazio na destruição por faixa e uma releitura
`volatile` no alocador EWRAM. Não houve alterações no compilador.
O C da fila de mapas explicita registradores e usa nove labels conservados por uma tabela C de 36 bytes em
`.debug_dbaa_flow`. O linker classifica esses endereços de labels como metadados INFO,
não alocáveis e não executáveis. O corpo `.text` inteiro continua sujeito à comparação exata.
O manifesto e os relatórios declaram tanto as flags específicas quanto os metadados auxiliares.

A etapa de [pacotes seriais](serial_packets_matching.md) acrescentou três alvos e 404 bytes
com agbcc `-O2`. O processador é C estruturado; o validador tem uma restrição vazia e
o construtor tem cinco, incluindo a captura de `r1` para preservar o caminho fora de 1..5.

A etapa de [sequências e fade](sequences_initialization_matching.md) acrescentou doze alvos
e 1.556 bytes com agbcc `-O2`. `0x080C863C` usa três restrições vazias; o callback
do fade e o inicializador filho usam uma cada. Os demais fontes novos não contêm
inline assembly. Macros GNU C com expressão de bloco conservam a resolução dos dados da tarefa.

A etapa de [apresentação inicial](boot_presentation_matching.md) acrescentou treze
alvos e 1.428 bytes com agbcc `-O2`. Onze fontes novos não contêm inline assembly.
O carregador usa duas restrições vazias e a limpeza do screenblock usa uma;
nenhum template contém instruções. O callback solicitado `0x080F2FD0` reproduz
252 bytes em C estruturado, incluindo literais e padding.

A etapa de [inicialização após a apresentação](post_boot_initialization_matching.md)
acrescentou dezenove alvos e 2.252 bytes com agbcc `-O2`. O inicializador
`0x080EFAA4` usa duas restrições vazias. Quatro outros fontes usam uma cada,
e o wrapper de música vincula uma variável a `r2` sem template de instruções.
A continuação concluiu o carregador `0x080EEDB4` e a fase `0x080EFC88`;
veja [carregador e fase seguinte](post_boot_loader_matching.md). São mais 644 bytes.
O carregador usa agbcc `-O1`, fluxo explícito de registradores em GNU C e treze
restrições vazias. A fase usa `-O2`, sem inline assembly. Nenhum template novo emite instruções.

A continuação de [fases, fade e transferência de tiles](post_boot_phases_matching.md)
acrescentou 21 alvos e 1.456 bytes com agbcc `-O2`. Três fontes usam uma restrição
vazia cada, para conservar endereços temporários e dois testes de flags separados;
os outros dezoito não usam asm. Nenhum template emite instruções.

A etapa do [callback `0x080F0040` e fundo especial](post_boot_phase21_matching.md)
acrescentou dezesseis alvos e 1.564 bytes com agbcc `-O2`. Quatro fontes usam nove
templates vazios no total, conservando ponteiros, offsets, testes separados,
o limite em `r8`, words em `r3` e o endereço temporário de preenchimento.
Nenhum template emite instruções; doze fontes novos não usam asm.

A etapa do [callback `0x080EEA7C`, sprites e scroll](post_boot_phase30_matching.md)
acrescentou dezesseis alvos e 1.724 bytes com agbcc `-O2`. O callback solicitado
é C estruturado, sem asm. Quatro outros fontes usam oito templates vazios para
conservar endereços, valores de posição, comparações e argumentos de desenho.
Nenhum emite instruções. O destrutor do pai foi atualizado para a view identificada
`scrollTasks[2]`, preservando seus 136 bytes completos.

A etapa do [callback `0x080F02EC` e encerramento](post_boot_phase38_matching.md)
acrescentou 25 alvos e 1.528 bytes com agbcc `-O2`. O callback solicitado é
C estruturado sem asm. O criador da tarefa circular usa uma restrição vazia;
o cálculo de posições usa duas, para preservar a extração do ângulo e a
soma do deslocamento de cada sprite. Os demais 23 fontes não usam asm.
Nenhum template emite instruções. Todo o bloco local de 96 funções e 8.892
bytes agora é comparado integralmente com a ROM.

A etapa de [reset serial, buffers e áudio](reset_services_matching.md) acrescentou oito
funções C estruturadas e 556 bytes com `-O2`, sem novas restrições GNU C. A continuação
concluiu o [callback serial](serial_irq_matching.md), com 560 bytes e sete restrições vazias,
e a [parada de trilha](music_track_stop_matching.md), com 68 bytes, dez restrições vazias
e um atributo de seção para preservar os zeros de alinhamento. As seções finais são
linkadas para execução na ROM; o assembly emitido permanece intacto.

A etapa de [desenho de sprites e serviços](graphics_draw_sprite_matching.md)
acrescentou quatro alvos e 1.592 bytes. `Graphics_DrawSprite` usa GNU C com
registradores explícitos, onze words temporárias e 193 restrições vazias
após expansão; a paleta usa 18 e o memset uma. O alocador é C sem asm.
Nenhum template emite instruções. O manifesto e a auditoria registram a
contagem no `.i`, incluindo cada expansão da macro de restrição de valores.
Os três alvos gráficos usam `-O2 -mthumb-interwork`; o memset usa `-O2`.

A etapa de [atualização CGB e auxiliares de música](audio_update_matching.md) acrescentou
três alvos e 1.480 bytes: `Cgb_Update` com `-O1`, fade e volume/pitch com `-O2`. São
23 templates vazios expandidos e 60 bytes de labels C não alocados. Os endereços de
dados numéricos do CGB evitam palavras `.rodata` redundantes emitidas por agbcc `-O1`;
todos os literais de execução continuam dentro da região comparada. O gate agora rejeita
qualquer seção alocada não vazia fora da `.text`. Um teste com dados globais adicionais
confirma a rejeição de `.data`, `.rodata` e `.bss`.

O candidato ARM C de `MusicPlayer_Update` continua `NONMATCHING`: agbcc, GCC 3.4.6 e GCC 8
diferem da entrada com salvamento de registradores em etapas e do corpo original.
Esses experimentos não alteram os perfis de produção nem identificam o SDK histórico.

A continuação de [MusicPlayer_Update](music_player_update_hybrid.md) adotou a divisão aprovada:
C nativo para a lógica do port e assembly separado para os 616 bytes GBA. O arquivo assembly
passa no gate próprio e declara `counts_as_c: false`. A rotina C compila para Windows x64 e
passou em 1.128 cenários contra a execução ARM da ROM. Esses resultados não alteram os perfis
dos 224 alvos C anteriores nem dão matching ao candidato ARM C antigo.

A etapa de [auxiliares de áudio](audio_helpers_matching.md) acrescentou 80 bytes C com matching:
`Audio_UnlinkChannel` com agbcc/prologue-bugfix e quatro restrições vazias, `MusicEvent_Fine`
com GCC 3.4.6 e cinco templates vazios. Cópia/validação e limpeza somam 76 bytes assembly
separados. O port nativo resolve nove endereços auxiliares em C e passa em 768 cenários próprios,
além dos 1.128 cenários do player integrado. Nenhum byte assembly é contado como C compilado.
