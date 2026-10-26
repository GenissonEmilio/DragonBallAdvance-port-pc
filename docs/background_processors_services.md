# Processadores de fundos e serviços da inicialização

Estado em 16/10/2026, ROM USA BDVE rev. 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

Esta etapa de fundos e serviços acrescentou **23 funções e 6.808 bytes com matching integral**.
A continuação de [tarefas e memória](tasks_memory_matching.md) adicionou outros dez alvos, e a de
[reset serial, buffers e áudio](reset_services_matching.md) acrescentou oito. O total de produção
é **224 funções, 33.032/33.032 bytes iguais**, incluindo o [callback serial](serial_irq_matching.md)
e a [parada de trilha](music_track_stop_matching.md). O agbcc atende 222 alvos: 216 com
`-O2 -mthumb-interwork`, três rotinas com `-O1 -mthumb-interwork` (fila de mapas,
carregador de fundos da abertura e `Cgb_Update`) e o memset
com `-O2` sem interworking, além de `Cgb_Stop`/`Audio_UnlinkChannel` com
`-O2 -mthumb-interwork -fprologue-bugfix`. `MusicEvent_Fine` usa o mesmo perfil GCC 3.4.6 da parada de trilha.
A parada de trilha
usa GCC 3.4.6 alternativo. Os quatro processadores
da tabela gráfica têm matching integral.
A leitura do header de save em `0x08001BE4` e o desenho de sprites em fundos em
`0x0810EFB4` agora têm matching integral.

## Funções concluídas

Os nomes `Func_*` foram conservados onde o papel específico no jogo ainda é provisório.
Cada linha corresponde a um corpo C compilado, linkado no endereço original e comparado
inteiro, incluindo literais e alinhamento. Helpers inline não contam como funções adicionais.

| Alvo | Endereço | Bytes | Operação observada |
|---|---|---:|---|
| `Graphics_ClearBackgrounds` | `0x0810F75C` | 612 | Preenche regiões de quatro fundos e limpa os pedidos |
| `Func_08114BA4` | `0x08114BA4` | 64 | Monta três tabelas de componentes de cor, zera o estado |
| `Func_08115618` | `0x08115618` | 20 | Inicializa o cabeçalho do heap EWRAM |
| `Func_08113C38` | `0x08113C38` | 40 | Limpa 512 bytes do mapa de alocação VRAM |
| `Func_081156FC` | `0x081156FC` | 72 | Seleciona configurações EEPROM 4/64; código 1 para valor inválido |
| `Tasks_AllocateSlot` | `0x0810DBD0` | 40 | Retira um dos 128 slots e incrementa o cursor |
| `Func_0810AD34` | `0x0810AD34` | 120 | Inicializa áudio, código em RAM e quatro players |
| `Func_0810B2D0` | `0x0810B2D0` | 152 | Aplica reverb, canais, volume, resolução e frequência |
| `Func_0810ADAC` | `0x0810ADAC` | 12 | Wrapper da atualização principal de áudio |
| `Func_08113CE0` | `0x08113CE0` | 244 | Configura serial, buffers, código em RAM e IRQ |
| `Func_080043F4` | `0x080043F4` | 16 | Encadeia dois serviços específicos do jogo |
| `Func_080A30F8` | `0x080A30F8` | 64 | Zera estado por DMA e encadeia quatro serviços |
| `Func_08102BF4` | `0x08102BF4` | 32 | Zera dois valores e ativa o byte `+0x34` do estado |
| `Func_0800C364` | `0x0800C364` | 12 | Zera a palavra em `0x02029EB4` |
| `Func_080A38CC` | `0x080A38CC` | 44 | Limpa 64 KiB em `0x0202A0C0` por DMA |
| `Func_080FA048` | `0x080FA048` | 304 | Reinicializa filas, entrada, memória, serial, áudio e handlers |
| `Func_08001538` | `0x08001538` | 152 | Examina assinatura do save e coordena sua inicialização |
| `Func_08001D00` | `0x08001D00` | 152 | Limpa dois estados e o header, preservando campos |
| `Func_080030A0` | `0x080030A0` | 44 | Percorre três índices de save, consultando um serviço externo |
| `Func_08002AA8` | `0x08002AA8` | 120 | Aplica valores padrão e solicita cálculo de checksum |
| `Func_08001BE4` | `0x08001BE4` | 284 | Lê o header EEPROM e tenta o banco de backup em caso de erro |
| `Graphics_DrawBackgroundSprites` | `0x0810EFB4` | 1.340 | Escreve tiles de sprites nos mapas de fundos de texto e afins |
| `Graphics_ProcessBackgroundQueue` | `0x0810DDCC` | 2.868 | Copia mapas e metatiles com rolagem, recortes e espelhamento |

`Runtime_Initialize` e `Game_Initialize` chamam 19 serviços distintos diretamente, além dos
alvos e wrappers de BIOS já conhecidos. **Os 19 serviços agora têm matching**.
A conclusão de `Func_08001BE4` está documentada em [save_header_matching.md](save_header_matching.md). A rotina auxiliar de slots de tarefas foi incluída
separadamente. Isso não significa que todas as dependências transitivas dos serviços estejam
reconstruídas: mixer, leitores EEPROM, verificadores de save e outros callees permanecem externos.

## O processador de limpeza

O slot 1 da tabela em `0x08D26710` aponta para `Graphics_ClearBackgrounds`. Ele percorre quatro
pedidos em `0x030030F0`, lê os controles dos fundos e distingue o caminho de texto do caminho
afim. Os bytes de preenchimento ficam em `0x03006610`. Ao terminar um pedido, limpa seus quatro
bytes por DMA de 32 bits; retorna 1 depois da passagem.

A comparação preserva as sentinelas `0xFF`, os limites inclusivos dos preenchimentos parciais,
os cálculos de contagem e as larguras dos temporários. Expressões incomuns da ROM não foram
substituídas por uma implementação supostamente mais correta. Não foi executado um cenário
gráfico em emulador nesta etapa.

## Restrições de compilação explícitas

`Func_08002AA8` usa dois templates GNU C vazios: um prende temporariamente o valor `0x23`
a `r2`; o outro conserva o deslocamento e a conversão do índice de um bit, evitando dobrar
todo o cálculo em uma constante. Não há instruções nos templates. Essas restrições aparecem
em `compiler_barriers` no manifesto e no relatório. Não afirmamos que esse era o C histórico.

`Func_08001BE4` acrescenta três templates vazios: separa os zeros, mantém o endereço de um
local durante a preparação do byte zero e conserva o destino EEPROM em `r5`. Todos constam do
manifesto. O processador de sprites em fundos acrescenta restrições vazias para DMA,
coordenadas, flips, montagem dos pares de tiles e passos de linha; estão descritas em
[background_sprites_matching.md](background_sprites_matching.md) e no manifesto. Não foram usados `.byte`, `.hword`, `.incbin`, substituição de instruções, recortes,
máscaras de comparação ou pós-processamento do assembly gerado.

`Tasks_AllocateSlot` esclareceu que `0x030030EC` é um cursor inteiro de slots. A declaração
antiga de ponteiro em `Tasks_Initialize` foi corrigida; seu binário continua idêntico.

## Fila de mapas concluída

`Graphics_ProcessBackgroundQueue` saiu das candidatas e entrou em produção após comparar
**2.868/2.868 bytes, zero diferenças**. A reconstrução em GNU C explicita registradores e
blocos de fluxo; usa `-O1`, templates vazios e metadados C de labels fora da imagem de execução.
As particularidades e os hashes estão em [background_queue_matching.md](background_queue_matching.md).
O algoritmo mais legível da investigação está em `reference/graphics_background_queue.c`,
fora do build. O manifesto de candidatas está vazio neste marco.

Há `BL` para destinos internos em `0x0810DDCC`: o compilador os emprega como saltos longos.
Não são novos serviços. A listagem linear pode decodificar os literais depois deles como código;
os limites foram conferidos seguindo os destinos até o retorno e os pools usados.

## Reprodução

```powershell
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match.py --target graphics_clear_backgrounds
.\.venv\Scripts\python.exe tools\match.py --target graphics_process_background_queue
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os comandos de matching precisam retornar 0. Os relatórios estão em
`build/matching/summary.json` e nas subpastas de cada alvo. Alterações no passo do fundo,
na máscara da fila, na capacidade da EEPROM e no setor do header são controles negativos
e precisam reprovar após recompilar.

Continua sem build da ROM inteira, boot do conjunto reconstruído ou executável PC.

## Referências de pesquisa

Fontes primárias consultadas, revisão `393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d`:

- [Rotinas de fundos do motor](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/background.c).
- [Estruturas OAM e bitfields](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/include/gba/types.h).
- [Inicialização e configuração m4a](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a.c).
- [Macros DMA](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/include/gba/dma_macros.h).

As correspondências ajudam a interpretar o motor compartilhado. A evidência de igualdade
dos alvos concluídos é o binário gerado deste projeto comparado com a ROM USA do usuário.
