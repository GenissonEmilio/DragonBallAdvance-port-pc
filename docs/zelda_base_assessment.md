# Base de referência: zelda-tmc-3ds

Revisão analisada em 26/10/2026:
[`2f248e06ff1e320da8e2d97ef2fe0202a2071fff`](https://github.com/EstebanPdN/zelda-tmc-3ds/tree/2f248e06ff1e320da8e2d97ef2fe0202a2071fff).
O repositório foi consultado como código-fonte; nenhum binário de Zelda,
ROM, BIOS ou recurso do jogo foi incorporado.

O projeto parte de Project Picori/tmc-android e da decompilação de Minish Cap.
Isso fornece a lógica nativa daquele jogo. Fases, entidades, colisões, tabelas
e saves de Zelda não têm o layout ou a semântica de Dragon Ball. Trocar a ROM
nesse executável não produz um port de outro jogo.

## Adaptação aplicada

A política de diretórios de diagnóstico de
[`src/port/port_dump_state.c`](https://github.com/EstebanPdN/zelda-tmc-3ds/blob/2f248e06ff1e320da8e2d97ef2fe0202a2071fff/src/port/port_dump_state.c)
foi portada para `port/windows/preview/Sessoes.ps1` e ligada ao iniciador Windows.
Ela ordena sessões por sequência, recupera o contador examinando os diretórios,
resiste ao relógio voltar e preserva capturas anteriores. A adaptação adiciona
um bloqueio de arquivo entre processos e usa substituição do contador no Windows.
É um script independente, distribuído com fonte e GPL-3.0-or-later; os créditos
e o texto da licença acompanham o pacote. Não carrega checkpoints de Zelda nem
altera o estado de Dragon Ball.

A organização descrita em
[`docs/ARCHITECTURE.md`](https://github.com/EstebanPdN/zelda-tmc-3ds/blob/2f248e06ff1e320da8e2d97ef2fe0202a2071fff/docs/ARCHITECTURE.md)
também orienta a continuação: separar o núcleo do jogo, a memória/serviços de
GBA e os backends de plataforma; amostrar entrada e avançar áudio em cada tick;
permitir que a apresentação acompanhe o ritmo disponível. Nosso vídeo já usa
thread de apresentação separada e o áudio tem worker próprio. Essas partes
existentes e verificadas são mantidas como base.

## Reaproveitamento avaliado

| Componente de Zelda | Aplicação em Dragon Ball |
|---|---|
| Diagnósticos numerados e verificações host | Política de sessões portada para o iniciador; testes sem ROM |
| Separação de engine, ponte GBA e plataforma | Orienta a estrutura existente; mantém layout e ordem de callbacks do jogo |
| Renderer `src/port/ppu` | Referência para recursos pendentes; não foi incorporado ou declarado validado para Dragon Ball |
| `agbplay_core` e agendamento de áudio | Alternativa existente para estudo; o áudio nativo já comparado com a ROM permanece ativo |
| `port_bios.c` | Referência de contratos; não substitui verificações contra a ROM/BIOS de referência |
| Engine, saves, widescreen e interface de duas telas | Dependem dos dados de Zelda ou de APIs 3DS; exigem adaptações específicas |

O renderer desse fork atende principalmente os modos GBA 0/1 e inclui regras
específicas de widescreen/HUD de Zelda. Não é substituto completo dos dispositivos
GBA. Sua própria nota de proveniência também registra uma questão de licença
no upstream VirtuaPPU; a declaração GPL do fork não demonstra por si só autorização
sobre a parte anterior. Nenhum arquivo desse renderer foi redistribuído aqui.
O módulo de diagnóstico reaproveitado é identificado separadamente.

O caminho para completar o port é conservar a recompilação estática já funcional,
substituir serviços por implementações compartilhadas verificadas quando houver
benefício e usar capturas reproduzíveis das falhas encontradas jogando. O uso dessa
base não prova que todas as fases, modos ou saves de Dragon Ball estejam corretos.
