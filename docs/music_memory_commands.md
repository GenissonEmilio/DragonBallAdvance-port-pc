# MEMACC e XCMD: memória, saltos e comandos estendidos

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

Os dois comandos pedidos foram reconstruídos em **C com matching integral**:
`MusicEvent_MemoryAccess` em `0x0810BFAC`, **344/344 bytes**, e `MusicEvent_Extended`
em `0x0810C104`, **32/32 bytes**. Seus serviços também foram reconstruídos em C/GNU C:
**14 funções e 664 bytes novos**, sem acrescentar assembly ao conjunto.

O total atual é **242 alvos C/GNU C, 33.856 bytes**, mais **23 alvos assembly,
2.720 bytes**: **265 alvos e 36.576 bytes idênticos à ROM**. A suíte atual contém
**290 testes aprovados na última suíte geral (instrumento), sem skips**. Há **59 endereços de áudio atendidos em C nativo**.

## Código reconstruído

| Função | Endereço USA | Bytes |
|---|---|---:|
| Memória e condições | `0x0810BFAC` | 344 |
| Despachante estendido | `0x0810C104` | 32 |
| Fim por callback | `0x0810C124` | 20 |
| Ponteiro da amostra | `0x0810C138` | 72 |
| Tipo do instrumento | `0x0810C180` | 20 |
| Ataque | `0x0810C194` | 20 |
| Decaimento | `0x0810C1A8` | 20 |
| Sustentação | `0x0810C1BC` | 20 |
| Liberação | `0x0810C1D0` | 20 |
| Volume de eco | `0x0810C1E4` | 12 |
| Comprimento de eco | `0x0810C1F0` | 12 |
| Comprimento CGB | `0x0810C1FC` | 20 |
| Sweep/pan | `0x0810C210` | 20 |
| Salto de trilha | `0x0810A554` | 32 |

`0x0810BFAC..0x0810C224` forma **632 bytes contínuos em C**. Concatenado com `Sound_Dummy`
e `Runtime_Initialize`, já reconstruídos, reproduz **2.400 bytes contínuos**, até `0x0810C90C`.
Esses bytes anteriores não são contados novamente. A função de salto adiciona 32 bytes
em outra região. O bloco novo contém 536 bytes de instruções, 104 de literais/tabela de
saltos gerados pelo compilador e 24 zeros de alinhamento.

Os fontes estão em `src/music_event_*.c`. Todos usam o perfil padrão agbcc GCC
2.9-arm-000512, `-O2 -mthumb-interwork`. Há **81 constraints GNU C vazias** declaradas
no manifesto para preservar registradores, ordem de acessos e a convenção interna do SDK.
O despachante, callback de fim e os dois campos de eco não precisam dessas constraints.
Não há instruções embutidas, arrays de opcodes, patches do compilador ou alteração do
assembly gerado. Cada imagem linkada é comparada inteira e seções alocadas extras são rejeitadas.

A inserção dos quatro bytes da amostra preserva o formato de código observado: captura
o temporário em `r4`, mascara e substitui cada byte. Ao final, todos os 32 bits foram
substituídos pelos quatro bytes lidos. O valor anterior de `r4` não afeta o ponteiro final.
O salto preserva a convenção do leitor que devolve o byte filtrado em `r3` e conserva
o acumulador em `r0`; a reconstrução GNU C declara esses efeitos com constraints vazias.

## MEMACC: operações e salto condicional

O evento `0xB9`, slot 8, consome operação, índice e dado. O destino é
`player.memory + índice`, mantendo os incrementos intermediários do cursor observados na ROM.

| Operações | Efeito |
|---|---|
| 0, 1, 2 | Atribuir, somar ou subtrair o dado imediato, armazenando somente oito bits |
| 3, 4, 5 | Atribuir, somar ou subtrair um byte da própria área de memória |
| 6..11 | Comparar com imediato: `==`, `!=`, `>`, `>=`, `<=`, `<` unsigned |
| 12..17 | As mesmas comparações com um byte da área de memória |
| 18..255 | Encerrar após os três parâmetros, sem operação sobre o destino |

Condição verdadeira consulta o **callback atual** no slot 1 da tabela RAM em `0x03001C74`.
Condição falsa avança quatro bytes, sem ler o ponteiro pulado. O callback padrão é o salto
em `0x0810A554`, que monta o endereço lendo os bytes na ordem 3, 2, 1 e 0. O byte baixo
passa pelo filtro já reconstruído em `0x0810A52C`; essa regra não foi substituída por um
load de 32 bits. Os testes também usam uma origem controlada abaixo de `0x02000000`
para conferir o caminho que zera esse byte.

## XCMD: despacho e serviços

O evento `0xCD`, slot 28, consome um índice e consulta a tabela em `0x08A67708`.
Foram verificadas as **12 entradas usadas na análise**, com **11 destinos distintos**:
os índices 0 e 3 compartilham o callback de fim em `0x0810C124`.
O código conserva a consulta pelo índice original; não acrescenta um limite artificial.
Os dados depois dessas entradas não são classificados aqui como uma extensão comprovada da tabela.

O fim consulta o callback atual no slot 0, `0x03001C70`. Os demais serviços atualizam
tipo, ponteiro da amostra, envelope, eco, comprimento ou sweep/pan. A amostra consome
quatro bytes; os setters consomem um. Os campos do instrumento recarregam o cursor após
a escrita, enquanto os dois campos de eco usam o cursor já lido, como no código original.

O C de referência da biblioteca m4a em
[SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a.c)
ajudou a identificar as operações. Os bytes, acessos e endereços foram conferidos nesta ROM.
O perfil compatível não identifica exclusivamente o SDK histórico da Dimps.

## Integração e validação nativa

`port/audio/audio_helpers.c` implementa as operações com endereços GBA `uint32_t` e callbacks
de memória. `Dbaa_AudioCall` resolve os 14 novos endereços em C, aceitando ponteiros Thumb.
Os setters compartilham uma implementação C por deslocamento. No PC, chamadas indiretas
usam esse despachante; a ponte GBA `BX r2`, em `0x08116A24`, não é executada no port.
Ela ainda é uma dependência original dos callers no build GBA e não entra na contagem nova.

`tools/verify_music_memory.py` compila uma DLL Windows x64 C99 com warnings tratados como
erros e compara sua execução com a ROM em Unicorn ARM926. Passou em **2.042 cenários**:

- 288 operações dirigidas e 432 comparações em limites de bytes unsigned.
- 238 operações não reconhecidas, cobrindo todos os valores 18..255.
- 192 eventos estendidos, cobrindo os 12 slots observados.
- 64 saltos e 16 casos adicionais de filtragem do byte baixo.
- 156 casos de sobreposição entre comandos e campos da trilha/memória.
- 16 substituições controladas do callback de salto.
- 512 casos adicionais com seeds determinísticos.
- 128 execuções do player com MEMACC, XCMD, salto real e notas sustentadas.

Foram percorridas **264/264 instruções** das 14 funções. Cada execução integrada verifica
que os dois comandos realmente foram alcançados; saltos tomados também precisam entrar no
callback real. A nota final precisa corresponder ao caminho escolhido e estar marcada para
liberação. Comparam RAM fora da pilha temporária, callbacks e ordem/largura das leituras observadas.

Os novos serviços não são delegados ao ARM no lado nativo. Somente o callback sintético
`0x08010104`, usado nos 16 casos de substituição, passa pelo executor de referência controlado.
Isso é validação funcional isolada, sem boot completo, ciclos ARM7TDMI ou dispositivos GBA.
Os corpora anteriores também passaram com os fontes atuais: 1.128 casos do player,
768 auxiliares, 1.312 notas, 1.472 términos, 2.576 LFO/modulação e 237.568 frequências PCM/CGB.

Os 16 testes novos verificam as 14 imagens C completas e mutações deliberadas em comparação,
aritmética, callback, índice da tabela, campos, endian, tamanho do salto e filtro do byte baixo.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target music_event_memory
.\.venv\Scripts\python.exe tools\match.py --target music_event_extended
.\.venv\Scripts\python.exe tools\verify_music_memory.py --cases 512
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match_assembly.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Evidências: `build/matching/summary.json`, `build/native_music_memory_validation/report.json`,
`build/verification.json` e `build/next/music_memory_commands/audit_memory.py`/`audit_memory.json`.

Os nove slots substituídos por `Sound_Extend` agora têm matching GBA. O port ainda não é
jogável: faltam comandos padrão da música, mixer e saída sonora, recursos, backend, gameplay
e integração. `Sound_SetFrequency` em `0x0810B22C` já tem matching GBA, mas ainda precisa
de um binding nativo ligado ao backend. Veja o [estado completo do port](port_status.md).

A continuação de [padrões e repetição](music_pattern_commands.md) acrescentou quatro bindings, levando o total atual a 35.
