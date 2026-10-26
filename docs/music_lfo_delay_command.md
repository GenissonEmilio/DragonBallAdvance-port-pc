# Comando de atraso do LFO LFODL

`MusicEvent_LfoDelay`, em `0x0810A688`, está reconstruído em **C para o port nativo
Windows x64**. O build GBA usa **assembly separado com 12/12 bytes idênticos à ROM USA
BDVE rev0**, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 12 | Todos iguais: 10 de instruções e 2 de padding zero |
| C candidato agbcc GCC 2.9-arm-000512 | 12 | 5 diferenças na imagem completa |
| C candidato GCC 3.4.6 Thumb | 12 | 5 diferenças na imagem completa |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O agregado atual contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly
e 2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
Na etapa de atraso do LFO, a região `0x0810A4AC..0x0810A694` contém **488 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xC3`, slot 18 da tabela de música, chama `Music_ReadCommandFiltered`
(`0x0810A548`) e grava o parâmetro sem sinal em `track+0x1B`. O leitor incrementa
o cursor antes de ler e filtrar o parâmetro. O port conserva a ordem, inclusive com
sobreposição do parâmetro, campos e cursor. Endereços rejeitados pelo filtro produzem zero.

O handler conserva todos os valores de 0 a 255. Não altera o status da faixa, o
contador em `track+0x1C`, a fase em `track+0x1A` ou a modulação em `track+0x16`.
Portanto, mudar LFODL durante uma nota modifica a configuração para futuras notas
sem reiniciar a contagem da nota atual.

O [processador de notas](sound_update_track_hybrid.md) copia o atraso configurado
para o contador ao criar uma nota. Se o valor for diferente de zero, também limpa
a fase e a modulação pelo auxiliar existente. Com atraso zero, essa limpeza não
ocorre. Ao final de cada tick musical, o player decrementa o contador se a velocidade
e a intensidade do LFO estiverem habilitadas. O tick que leva o contador a zero
ainda não avança a fase; o avanço ocorre no tick seguinte.

O atraso mede **ticks musicais**, não frames de vídeo. Alterações de tempo podem
fazer uma atualização do player processar vários ticks. Atraso 255 e valores
acima de 127 permanecem positivos. Se a velocidade ou a intensidade forem zero,
o player não decrementa o contador nesse caminho.

Depois da espera, a modulação pode alterar pitch ou volume conforme `track+0x18`.
As notas PCM/CGB mantêm canal, instrumento, envelope e nota original. O mecanismo
de propagação existente atualiza frequência ou volumes e as flags CGB correspondentes.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventLfoDelay`.
- API: [audio_helpers.h](../port/include/audio_helpers.h).
- Assembly GBA: [music_event_lfo_delay.s](../asm/music_event_lfo_delay.s).
- C ARM não correspondente: [music_event_lfo_delay.c](../nonmatching/music_event_lfo_delay.c).
- Validação: [verify_music_lfo_delay.py](../tools/verify_music_lfo_delay.py) e
  [test_music_lfo_delay.py](../tests/test_music_lfo_delay.py).

O original salva LR em `r12`, recebe o parâmetro filtrado em `r3` e mantém a faixa
em `r1`. O candidato C usa uma restrição GNU C vazia para representar esse fluxo,
sem incorporar instruções assembly. Seus seis bytes intermediários coincidem;
prólogo e retorno diferem. Ambos os compiladores geram 12 bytes, com cinco
diferenças na comparação completa. Os candidatos permanecem fora do matching C.

O gate compara todo o `.text` linkado no endereço original, incluindo o padding,
e rejeita seções alocadas extras e relocations restantes. Não há máscaras, recortes
ou alteração do assembly gerado. As quatro instruções ocupam dez bytes; os dois
bytes de alinhamento zero também entram na prova.

## Validação desta etapa

Passaram **2.397 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 parâmetros com quatro estados e
  outros 256 bytes de status.
- 72 sobreposições de memória e 16 parâmetros em endereços filtrados.
- 512 casos aleatórios com seed fixa.
- 256 sequências de criação de nota e 256 mudanças de atraso durante uma nota existente.

As **512 sequências do player real** somam **1.792 atualizações e 33.923 ticks**.
Para todos os 256 atrasos, a criação da nota é seguida até o fim da contagem e o
primeiro avanço de fase. Os atrasos zero e um têm uma atualização adicional para
conferir a continuidade. As mudanças durante uma nota conservam o contador antigo
até sua própria conclusão, independentemente do novo parâmetro.

Um modelo independente confere contador, fase e amplitude. As fixtures de timing
usam velocidade 4 e intensidade 32, dentro do trecho crescente da onda triangular.
Variações de velocidade e onda completas continuam cobertas pelo corpus existente
de [LFO/modulação](music_modulation_commands.md). Aritmética independente confere o
pitch e 512 chamadas independentes às rotinas PCM/CGB da ROM conferem a frequência
final. São exercitados os modos de modulação de pitch e volume.

RAM, leituras observadas e callbacks coincidiram. SP e registradores preservados
também são conferidos. Nenhum serviço novo usa fallback ARM no lado nativo. O
despachante aceita endereço par e ponteiro Thumb, mantendo endereços GBA como inteiros de 32 bits.

Passaram os **12 testes próprios**, incluindo mutações de campo, filtro, padding,
reinício indevido do contador/fase, flags extras e clamp em 127. Os **16 corpora
nativos de áudio** foram reexecutados com os fontes e headers atuais, além dos
gates dos **242 alvos C e 19 assembly**. A suíte geral daquela etapa continha **347 testes**
e não foi reexecutada integralmente; a última execução completa continua sendo
a de 290 testes da etapa de instrumento.

As primeiras execuções dos corpora de padrões e prioridade/tempo foram bloqueadas
pelo Windows Code Integrity (erro 4551) ao carregar suas DLLs, antes dos cenários.
Ambos passaram ao repetir o procedimento normal de compilação e execução, sem
alterar políticas de segurança. Os logs iniciais e os das repetições permanecem
em `build/next/music_lfo_delay/`; a auditoria registra as duas tentativas separadamente.

Unicorn ARM926 fornece comparação funcional; os resultados não validam ciclos
do ARM7TDMI, dispositivos completos ou boot integral. A equivalência comportamental
do executável Windows é registrada separadamente do matching de bytes GBA.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_lfo_delay
.\.venv\Scripts\python.exe tools\verify_music_lfo_delay.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_lfo_delay.py -v
```

Evidências: `build/native_music_lfo_delay_validation/report.json`,
`build/assembly_matching/music_event_lfo_delay/report.json`,
`build/next/music_lfo_delay/tests_target.log` e `build/verification.json`.

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada,
inicialização integrada, recursos, saves e sistemas de gameplay, seguidos de
validação durante o jogo completo. A contagem de slots não representa um percentual
do port. Veja o [estado atual](port_status.md).

O [tipo de modulação](music_mod_type_command.md) foi integrado na etapa seguinte, com
24 bytes assembly exatos, doze testes próprios e reexecução dos dezessete corpora nativos.
