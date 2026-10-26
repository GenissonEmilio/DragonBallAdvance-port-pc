# Mixer PCM: C nativo e reprodução GBA

O mixer `0x0810A084` está reconstruído como **`Dbaa_SoundMain` em C nativo**.
Produz os dois planos de PCM de 8 bits do jogo, preservando wraps, reverb,
envelopes, loops e interpolação. O port executa essa lógica em C Windows x64.

O build GBA usa **assembly separado com 1.064/1.064 bytes idênticos**, de
`0x0810A084` a `0x0810A4AC` exclusivo. O alvo contém 1.024 bytes de instruções,
32 de literais e oito de padding. São **367 instruções**, incluindo trechos
Thumb e **572 bytes de código ARM**.

O candidato C/GCC 3.4.6 gerou **1.532 bytes, com 1.516 diferenças** na comparação
integral. Ele está explicitamente excluído do matching. A mesma implementação
semântica é compartilhada pelo C nativo e por esse probe GBA; não há inline
assembly, arrays de instruções, emulador de CPU ou alteração de assembly gerado
no kernel C. Essa etapa segue a divisão C nativo/assembly GBA adotada no player.

O total passa a **242 alvos C/GNU C, 33.856 bytes, e 23 assembly, 2.720 bytes**:
**265 rotinas e 36.576 bytes idênticos à ROM**. Os 1.064 bytes novos são contados
somente como assembly. O despachante resolve **59 endereços**: os dois novos são
o mixer e a entrada do player `0x0810A724`, cujo C já existia e agora pode ser
chamado diretamente pelo callback do mixer.

## Delimitação e execução

A entrada guarda o ponteiro SoundInfo original, exige o lock `0x68736D53`,
incrementa o lock e calcula um deadline opcional a partir de VCOUNT. Chama o
player, quando há callback, e sempre chama o callback CGB. Depois seleciona a
posição do buffer PCM pelo contador/período DMA.

No GBA, a continuação inicia em `SoundMainRam` (`0x0810A108`), copiada para
`0x030008B0`. Esse bloco alterna Thumb/ARM e restaura a pilha aberta pela entrada;
o salto para RAM não é um retorno. A inicialização copia 1.024 bytes, embora o
trecho próprio restante do mixer ocupe 932: os 92 seguintes são bytes vizinhos
inertes nessa execução e não são somados novamente ao matching.

A referência de validação executa a cópia real na IWRAM, com a entrada na ROM.
O lado nativo chama funções C e mantém endereços de dados de 32 bits. Não executa
o código copiado nem delega os callbacks conhecidos ao ARM.

## Lógica PCM preservada

- Reverb lê quatro amostras signed de dois buffers, multiplica pelo nível,
  aplica shift aritmético de nove bits e o ajuste de arredondamento original.
- Sem reverb, a limpeza mantém a ordem intercalada dos words. Inclusive conserva
  o comportamento particular dos tamanhos artificiais menores que 16 amostras;
  as configurações normais da tabela do jogo são maiores.
- Os canais passam por início, ataque, decay, sustain, release e eco. O ganho
  combina envelope, volume mestre e volumes right/left.
- O caminho fixo consome bytes PCM diretamente. O outro usa interpolação linear,
  fase de 23 bits e incremento com produto unsigned de 32 bits.
- Os acumuladores compactados mantêm adição modular, rotação dos words e flush
  parcial no término de amostra. Não há aproximação por saturação ou ponto flutuante.
- Loop, contagem restante, cursor e fase seguem a ordem original. Ao encerrar uma
  amostra, a rotina limpa seu status sem gravar os campos que a ROM também deixa
  preservados.

A comparação da cadeia completa revelou uma leitura redundante no byte de
espera do player nativo. O player agora reutiliza o valor já lido antes do
decremento; uma mutação dedicada impede a regressão desse acesso.

## Validação

Passaram **1.884 cenários e 2.436 execuções**, com igualdade de RAM observável,
bytes PCM e acessos ordenados de dados:

| Grupo | Cenários |
|---|---:|
| Controles e locks | 25 |
| Tamanhos de frame, incluindo extremos artificiais | 52 |
| Todos os status em dois caminhos de mistura | 512 |
| Limites de envelope e ganho | 165 |
| Finais de amostra e loops | 160 |
| Seleção do buffer DMA | 48 |
| Polifonia de zero a doze canais | 26 |
| Todos os bytes de reverb | 256 |
| Deadlines por scanline | 256 |
| Sequências com estado entre chamadas | 24 |
| Referência PCM escalar independente | 72 |
| Cadeia de players e CGB reais | 32 |
| Aleatórios determinísticos | 256 |

As 24 sequências somam **576 atualizações** do mixer. Os casos integrados
percorrem mixer → dois players encadeados → comandos/auxiliares → CGB → PCM.
Os 72 casos escalares comparam a aritmética por amostra em Python, separada dos
acumuladores compactados, para vozes isoladas em sustain.

Uma matriz complementar encadeou o `Sound_SetFrequency` real com o mixer em
**36 cenários e 72 execuções**, cobrindo os **12 modos de frequência** da ROM.
RAM, acessos ordenados e PCM coincidiram com a referência, e os 36 casos também
passaram no cálculo escalar independente. Doze verificam o overflow do produto
de frequência de 32 bits. Essa matriz é adicional aos 1.884 cenários acima.

Todas as **367 instruções** do mixer foram cobertas. Os endereços executados em
RAM são traduzidos para seus correspondentes na ROM para essa contagem.
A comparação de RAM inclui o buffer de código copiado; suas leituras de literais
são excluídas do trace de dados. Como nos corpora anteriores, a pilha morta
`0x03007000..0x030077FF` é excluída da comparação de estado entre arquiteturas.

Passaram **87 testes direcionados**, incluindo 18 desta etapa, e os **24 corpora
de áudio** com os fontes finais. Os gates recompilaram os **242 alvos C e 23
assembly**, comparando tamanho e todos os bytes, sem máscaras ou recortes.
Há **470 testes descobertos**; a suíte geral não foi reexecutada integralmente.
A última execução completa registrada continua sendo a de 290 testes da etapa
de instrumento.

O código de referência executa em Unicorn ARM926, com I/O plano e VCOUNT
roteirizado. Isso valida dados e controle funcional, sem provar ciclos ARM7TDMI,
efeitos de DMA/FIFO/timer, temporização de dispositivos ou saída audível.

Fontes: [kernel C](../port/include/pcm_mixer_impl.h),
[despachante](../port/audio/audio_helpers.c), [player C](../port/audio/music_player_update.c),
[assembly GBA](../asm/sound_main.s), [probe C excluído](../reference/sound_main.c),
[verificador](../tools/verify_pcm_mixer.py) e [testes](../tests/test_pcm_mixer_native.py).
A referência de interpretação do driver foi o
[m4a0.s de SAT-R/sa2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s);
a ROM local continua sendo a autoridade para bytes e comportamento.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target sound_main
.\.venv\Scripts\python.exe tools\verify_pcm_mixer.py --cases 256
.\.venv\Scripts\python.exe -m unittest discover -s tests -p '*native.py' -v
```

Evidências: `build/assembly_matching/sound_main/report.json`,
`build/native_pcm_mixer_validation/report.json`, `build/next/mixer_native/c_probe/report.json`,
`build/next/mixer_native/tests_target.log`, `build/next/mixer_native/audit_mixer.json`
e `build/verification.json`. A matriz complementar está registrada em
`build/next/mixer_native/real_rates.json`, com o script e os hashes de entrada.

O jogo Windows ainda não é jogável. A [inicialização de alto nível, Open e
wrapper](audio_startup_native.md) foram ligados depois, chegando a 62 endereços
nativos. O mixer já gera buffers PCM equivalentes à referência; faltam APIs de
músicas/dados, saída de áudio, relógio/dispositivos e ligação ao loop do host.
Vídeo, entrada, recursos, saves, gameplay e validação do jogo completo continuam pendentes.
Veja o [estado do port](port_status.md).
