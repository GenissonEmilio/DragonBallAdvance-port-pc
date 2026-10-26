# Inicialização de áudio no port nativo

`Sound_Initialize` (`0x0810B134`) e `Sound_Extend` (`0x0810AFF0`) estão
integradas em **C Windows x64**, por `Dbaa_SoundInitialize` e `Dbaa_SoundExtend`.
O despachante também atende `Sound_Dummy` (`0x0810C224`), callback vazio usado
antes da extensão CGB.

O C/GNU C GBA foi recompilado e comparado integralmente com a ROM USA BDVE rev0,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`:

| Rotina | Instruções | Literais | Padding | Bytes idênticos |
|---|---:|---:|---:|---:|
| Sound_Initialize | 184 | 64 | 0 | 248/248 |
| Sound_Extend | 200 | 80 | 0 | 280/280 |
| Sound_Dummy | 2 | 0 | 2 | 4/4 |

Esses **532 bytes já pertenciam ao matching C**. O total permanece em **242 alvos
C/GNU C, 33.856 bytes, e 23 assembly, 2.720 bytes**: **265 rotinas e 36.576 bytes
exatos**. Os três bindings elevam o conjunto a **54 serviços nativos**; os **36/36
slots da tabela após Sound_Extend** têm binding C. Ainda há dependências transitivas.

## Inicialização

A rotina zera primeiro o lock, interrompe cada DMA cujo bit 25 está ligado e
configura controle, bias e destinos FIFO com as larguras originais. As origens
dos dois DMAs são `sound+0x350` e `sound+0x980`. Publica o ponteiro global em
`0x03007FF0` antes de limpar **1.004 words / 4.016 bytes** de SoundInfo e PCM.

Depois grava oito canais e volume 15, instala `Sound_UpdateTrack` e quatro
ponteiros Thumb para `Sound_Dummy`, copia as 36 entradas da tabela da ROM para
`0x03001C70` e chama `Sound_SetFrequency(0x40000)`. O lock só recebe
`0x68736D53` ao final. A chamada intermediária a VSync-on vê o lock zerado;
a subtração de dez com wrap de 32 bits foi preservada.

O buffer usado pelo jogo começa em `0x03000CC0`. Seus 4.016 bytes terminam
imediatamente antes da tabela de comandos em `0x03001C70`. O nativo usa os
serviços C já ligados, sem executar ARM ou chamar uma BIOS.

## Extensão CGB

As **dez escritas em I/O precedem o teste do lock**, inclusive quando a rotina
rejeita a chamada. Após aceitar `0x68736D53`, ela incrementa o lock e modifica
nove posições da tabela fixa, nesta ordem:

| Slot | Ponteiro Thumb instalado |
|---:|---|
| 8 | `0x0810BFAD` |
| 17 | `0x0810AC69` |
| 19 | `0x0810AC7D` |
| 28 | `0x0810C105` |
| 29 | `0x0810AC01` |
| 30 | `0x0810B22D` |
| 31 | `0x0810A98D` |
| 32 | `0x0810B611` |
| 33 | `0x0810B6D9` |

Instala o buffer CGB, `Cgb_Update`, `Cgb_Stop` e o cálculo de frequência CGB.
Zera `maxLines` e **64 words / 256 bytes** de quatro registros de canal.
Grava os identificadores 1, 2, 3 e 4 e as máscaras `0x11`, `0x22`, `0x44`
e `0x88`. Restaura o lock guardado antes da limpeza, inclusive quando os buffers
se sobrepõem. O buffer CGB habitual é `0x03001D00`.

Na etapa de inicialização, **Cgb_Update (`0x0810B8EC`) e Cgb_Stop
(`0x0810B834`) foram instalados como chaves de endereço sem execução por aquele
corpus**. A continuação de [CGB nativo](cgb_native.md) ligou ambos e Volume,
executando os callbacks em sequências separadas de setup e atualização.

## Validação

O corpus passou em **1.008 cenários e 1.328 execuções**, comparando a ROM,
o C nativo e um modelo independente de estado:

- 36 combinações de DMA, todos os 256 bytes de bias e 16 valores de lock.
- Posições em EWRAM/IWRAM, buffers sobrepostos, sentinelas na tabela e diferentes
  imagens de I/O, incluindo lock rejeitado após as escritas CGB.
- Oito casos de troca do ponteiro global durante a cadeia de frequência.
- **32 sequências** de inicializar → callbacks vazios → estender → modo →
  suspender → retomar → reinicializar → estender, com estado entre chamadas.
- **128 chamadas** pelos quatro ponteiros vazios instalados e **64 verificações**
  da tabela estendida e dos ponteiros dos callbacks.
- 512 casos aleatórios determinísticos.

Coincidiram toda a RAM observável do jogo, os buffers, a tabela, o espelho de I/O
e a ordem/largura das leituras e escritas. A área de pilha morta do executor
`0x03007000..0x030077FF` é excluída da comparação, como nos corpora anteriores.
A cobertura alcançou **399 instruções**: 89 da inicialização, 99 da extensão,
uma de Dummy, 15 da cópia/filtro e 195 de modo/frequência/VSync.
Foram observadas **14.860 escritas em I/O**, **2.545 leituras de VCOUNT**
e **956 preenchimentos**: 662 de inicialização, 230 CGB e 64 de VSync-off.

A referência executa o código da ROM em Unicorn ARM926, com **CpuSet modelado**:
valida SWI `0x0B`, controle exato, alinhamento e origem zero, e materializa as
escritas word. Os três controles permitidos são `0x050003EC`, `0x05000040` e
`0x05000318`. Não foi usada uma imagem da BIOS. O I/O é plano e VCOUNT é
roteirizado; efeitos de DMA/FIFO/timer, ciclos e saída audível continuam pendentes.

Passaram **51 testes direcionados**: 18 desta etapa e 33 de modo/frequência.
As mutações deliberadas cobrem tamanho de limpeza, origem DMA, canais, callbacks,
ponteiro global, posições da tabela, largura/omissão de I/O, máscara, lock e
tentativas de fallback ARM. Os gates revalidaram os **242 alvos C e 22 assembly**,
incluindo literais e padding, sem alterar assembly gerado ou esconder seções
alocadas. Os **22 corpora de áudio** passaram com os fontes finais.

Há **434 testes descobertos**; a suíte geral não foi reexecutada integralmente
nesta etapa. A última suíte completa registrada passou em 290 testes na etapa
de instrumento. ROM, extrações e builds de validação permanecem locais.

Fontes: [C nativo](../port/audio/audio_helpers.c), [API](../port/include/audio_helpers.h),
[inicializador GBA](../src/sound_initialize.c), [extensão GBA](../src/sound_extend.c),
[Dummy GBA](../src/sound_dummy.c), [verificador](../tools/verify_sound_initialization.py)
e [testes](../tests/test_sound_initialization_native.py).

```powershell
.\.venv\Scripts\python.exe tools\match.py --target sound_initialize
.\.venv\Scripts\python.exe tools\match.py --target sound_extend
.\.venv\Scripts\python.exe tools\match.py --target sound_dummy
.\.venv\Scripts\python.exe tools\verify_sound_initialization.py --cases 512
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_sound_*native.py' -v
```

Evidências: `build/native_sound_initialization_validation/report.json`,
`build/next/sound_init/tests_target.log`, `build/next/sound_init/native_jobs.json`,
`build/next/sound_init/audit_initialization.json` e `build/verification.json`.

O jogo Windows ainda não é jogável. [Cgb_Stop e Cgb_Update](cgb_native.md)
foram integrados na continuação, chegando a 57 serviços nativos. O
[mixer PCM](pcm_mixer_native.md) veio depois, chegando a 59 endereços resolvidos.
Saída de áudio e tempo/dispositivos são a próxima fronteira. Também faltam backend de vídeo,
entrada/tempo, recursos, saves, gameplay e validação durante o jogo completo.
Veja o [estado do port](port_status.md).

A [inicialização de alto nível e o wrapper](audio_startup_native.md) foram ligados
na continuação, junto a `MusicPlayer_Open`: 62 endereços em C nativo, com a
configuração dos quatro players e 27 trilhas. Faltam APIs de músicas/dados,
dispositivos, saída de som e integração do jogo.
