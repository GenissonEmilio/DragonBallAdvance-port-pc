# Comando de tipo de modulação MODT

`MusicEvent_ModType`, em `0x0810A694`, está reconstruído em **C para o port nativo
Windows x64**. O build GBA usa **assembly separado com 24/24 bytes idênticos à ROM USA
BDVE rev0**, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 24 | Todos iguais: 11 instruções, sem literais ou padding |
| C candidato agbcc GCC 2.9-arm-000512 | 28 | 8 diferenças, incluindo quatro bytes extras |
| C candidato GCC 3.4.6 Thumb | 28 | 8 diferenças, incluindo quatro bytes extras |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
Na etapa de tipo de modulação, a região `0x0810A4AC..0x0810A6AC` contém **512 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xC5`, slot 20 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`) e compara o parâmetro com `track+0x18`. Se forem iguais, retorna
sem gravar o tipo ou o status. Se forem diferentes, grava o novo byte e acrescenta
`0x0F` às flags existentes, solicitando recálculo e propagação de pitch e estéreo.
O cursor avança nos dois caminhos.

O leitor incrementa o cursor antes da leitura e do filtro. O nativo preserva a
ordem, inclusive com sobreposição de campos e cursor. Um endereço rejeitado pelo
filtro produz zero; a comparação de igualdade usa esse valor filtrado.

O comando não reinicia fase, amplitude ou contador de atraso do LFO. A seleção é
um byte sem sinal: valores de 3 a 255 são conservados, sem clamp para os modos conhecidos.
O cálculo existente interpreta os tipos assim:

| Tipo | Efeito da modulação |
|---|---|
| 0 | Soma `16 * modulação_com_sinal` ao pitch em unidades de 1/256 de semitom |
| 1 | Multiplica o volume por `(128 + modulação_com_sinal) / 128`, com truncamento |
| 2 | Soma a modulação com sinal ao pan antes do limite de -128 a 127 |
| 3 a 255 | Calcula volume e pan básicos e exclui a contribuição de modulação no pitch |

A máscara `0x0F` remove a contribuição do modo anterior e aplica a do novo à nota
existente. Por exemplo, vibrato para volume restaura o pitch básico e recalcula o
estéreo. Trocar apenas entre flags de volume ou apenas de pitch deixaria valores
anteriores em cache. Notas PCM/CGB mantêm canal, instrumento, envelope e nota original.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventModType`.
- API: [audio_helpers.h](../port/include/audio_helpers.h).
- Assembly GBA: [music_event_mod_type.s](../asm/music_event_mod_type.s).
- C ARM não correspondente: [music_event_mod_type.c](../nonmatching/music_event_mod_type.c).
- Validação: [verify_music_mod_type.py](../tools/verify_music_mod_type.py) e
  [test_music_mod_type.py](../tests/test_music_mod_type.py).

O original salva LR em `r12`, recebe o byte filtrado em `r3` e mantém a faixa em
`r1`. Os candidatos usam três restrições GNU C vazias, sem incorporar instruções
assembly. Seus 20 bytes intermediários coincidem, incluindo o desvio de igualdade;
prólogo e retorno diferem. As imagens completas têm 28 bytes e oito diferenças
contra os 24 da ROM. Permanecem explicitamente fora do matching C.

O gate compara todo o `.text` linkado no endereço original e rejeita seções alocadas
extras e relocations restantes. Não há máscaras, recortes ou alterações no assembly
gerado. Os bytes do assembly separado são contabilizados à parte dos fontes C com matching.

## Validação desta etapa

Passaram **3.185 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos e 1.024 combinações dos 256 parâmetros com valor anterior
  igual/diferente e dois estados de flags.
- 512 combinações dos 256 bytes de status com os dois caminhos da comparação.
- 72 sobreposições de memória, 16 parâmetros em endereços filtrados e 512 casos
  aleatórios com seed fixa.
- 522 sequências com criação de nota e 522 mudanças de modo em uma nota existente.

As **1.044 sequências do player** somam **2.088 atualizações**: 512 mantêm o mesmo
tipo e 532 mudam de tipo. Há 32 sequências que cruzam todos os pares dos tipos
`0,1,2,255`, antes e depois da criação da nota. Os demais valores de 0 a 255 também
entram em sequências reais com igualdade e mudança de tipo.

São usados valores positivos e negativos de modulação. Um cálculo independente
confere pitch, volumes da faixa, pan, volumes dos canais e saturação. As fixtures
do LFO usam o trecho positivo ou negativo da onda triangular com velocidade 4 e
intensidade 32. Cada uma das 1.044 frequências finais é conferida com uma chamada
independente à rotina PCM/CGB da ROM. A evolução da fase e da amplitude também é
conferida para detectar limpezas indevidas durante a troca.

RAM, leituras observadas e callbacks coincidiram. SP e registradores preservados
também são conferidos. Nenhum serviço novo usa fallback ARM no lado nativo. O
despachante aceita endereço par e ponteiro Thumb e mantém endereços GBA como inteiros de 32 bits.

Passaram os **12 testes próprios**, incluindo mutações do campo gravado, desvio de
igualdade, flags incompletas, perda de flags anteriores, reinício de fase, filtro e
clamp. Os **17 corpora nativos de áudio** foram reexecutados com os fontes e headers
atuais, além dos gates dos **242 alvos C e 20 assembly**. A suíte geral daquela etapa continha
**359 testes** e não foi reexecutada integralmente; a última execução completa
continua sendo a de 290 testes da etapa de instrumento.

Um seletor do teste de mutação foi corrigido para selecionar apenas a instrução
de escrita, distinguindo-a da leitura do mesmo campo. A suíte específica completa
foi repetida após a correção, preservando os dois logs. Qualquer bloqueio inicial
de DLL pelo Windows Code Integrity é registrado separadamente de uma repetição do
procedimento normal; nenhuma política de segurança é alterada.

Unicorn ARM926 fornece comparação funcional. Os resultados não validam ciclos do
ARM7TDMI, dispositivos completos ou boot integral. A equivalência comportamental
Windows é registrada separadamente do matching de bytes GBA.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_mod_type
.\.venv\Scripts\python.exe tools\verify_music_mod_type.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_mod_type.py -v
```

Evidências: `build/native_music_mod_type_validation/report.json`,
`build/assembly_matching/music_event_mod_type/report.json`,
`build/next/music_mod_type/tests_target.log` e `build/verification.json`.

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada,
inicialização integrada, recursos, saves e sistemas de gameplay, seguidos de
validação durante o jogo completo. A contagem de slots não representa um percentual
do port. Veja o [estado atual](port_status.md).

A [afinação](music_tune_command.md) foi integrada na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos dezoito corpora nativos.
