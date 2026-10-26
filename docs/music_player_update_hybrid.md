# MusicPlayer_Update: C nativo e assembly GBA com matching

Validação sobre USA `BDVE`, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

Concluída a divisão escolhida pelo usuário: **C para o port, assembly separado para reproduzir
os bytes do GBA**. Os dois resultados têm critérios de verificação distintos.

| Resultado | Fonte | Validação |
|---|---|---|
| Rotina GBA e ponte compartilhada | `asm/music_player_update.s` | **616/616 bytes idênticos**, em `0x0810A724..0x0810A98C` |
| Lógica para o host | `port/audio/music_player_update.c` | C99 compilado para **Windows x64**, comparado à execução ARM da ROM |
| Interface de memória e chamadas | `port/include/music_player.h` | Endereços do jogo em 32 bits; ponteiros do host em 64 bits |

Há **242 funções C/GNU C com matching (33.856 bytes)** e **23 alvos assembly com matching
(2.720 bytes)**: **265 alvos e 36.576 bytes iguais à ROM**. O C nativo desta etapa é validado
por comportamento e não aumenta a contagem de funções C com igualdade binária ARM.
Há **290 testes validados na última suíte geral (instrumento), sem skips**.

## Por que usar duas versões

A sequência em assembly `MP2KPlayerMain` do
[SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s),
com símbolos resolvidos para esta ROM, reproduziu os mesmos 616 bytes. A conferência inicial
identificou uma diferença na chamada de limpeza: aqui ela usa o wrapper `0x0810B120`, que
consulta o callback em RAM. Usar diretamente `0x0810A4AC` altera os quatro bytes da chamada.
O arquivo assembly do projeto representa as instruções, os labels e os três literais
observados nesta ROM. A coincidência não identifica exclusivamente o SDK histórico da Dimps.

O teste de lock precede qualquer salvamento da pilha. O player encadeado é chamado entre
`PUSH {r0, lr}` e `POP {r0}`; depois são salvos os registradores do corpo principal. O epílogo
restaura oito registradores num único POP e compartilha `BX r3` em `0x0810A97C` com outras chamadas.
Isso é diferente dos prólogos e epílogos produzidos pelos candidatos C testados.

A flag de shrink wrapping depende do suporte do alvo, como esclarece a
[documentação do GCC](https://gcc.gnu.org/onlinedocs/gcc-8.1.0/gcc.pdf).
O [backend Thumb-1 do LLVM](https://www.llvm.org/docs/doxygen/Thumb1FrameLowering_8h_source.html)
também desativa essa transformação explicitamente. Esses fatos delimitam os caminhos testados;
não constituem uma prova de impossibilidade para todo compilador ou toda extensão C.

O antigo candidato `nonmatching/music_player_update.c` continua disponível, acompanhado pelo
manifesto `config/candidates.usa.json`, e ainda reprova na comparação ARM integral. Não foi
renomeado nem reclassificado como C com matching. Seus resultados anteriores estão em
[audio_update_matching.md](audio_update_matching.md).

## Matching GBA

O arquivo dedicado contém **602 bytes de instruções, dois de alinhamento com zero e 12 de
literais**. Inclui `_call_via_r3` como símbolo Thumb na posição original. Não usa `.incbin`,
arrays de opcodes ou patches. As únicas três diretivas `.word` são os literais reais de dados.

`tools/match_assembly.py` monta o fonte com GNU as para ARM7TDMI, resolve os símbolos, linka
no endereço original e compara toda a seção `.text`, incluindo tamanho, literais e padding.
Rejeita relocations restantes, ROM de outro hash e seções alocadas adicionais. O relatório
declara `kind: assembly` e `counts_as_c: false`; o manifesto é `config/assembly.usa.json`.

Também foi conferida a concatenação desta rotina com `MusicTrack_Stop`: **684 bytes contínuos**,
`0x0810A724..0x0810A9D0`. Os 68 bytes da parada de trilha já pertenciam ao conjunto C anterior.

## C nativo e interface para o port

O C novo não converte ponteiros do PC em inteiros de 32 bits nem usa offsets sobre structs
com ponteiros de tamanho diferente. `DbaaMusicHost` oferece leituras e escritas de 1, 2 e 4 bytes,
além da resolução de chamadas do jogo para implementações C do host. As escritas conservam
apenas os bits da largura indicada. Os valores são little-endian.

Essa interface mantém o modelo de endereços dos dados GBA e permite implementações nativas
dos auxiliares. O algoritmo C não executa instruções ARM. Na ferramenta de validação, as
chamadas ainda não portadas são executadas na ROM de referência. A continuação de
[auxiliares de áudio](audio_helpers_matching.md), [frequências PCM/CGB](audio_frequency_matching.md)
e [notas/canais](sound_update_track_hybrid.md) passaram a resolver cinquenta e nove endereços em C,
sem delegá-los ao ARM no lado nativo.

O código cobre lock, encadeamento de players, fade, acumulação de tempo, trilhas, running status,
despacho de comandos/notas, gate time, LFO, volume/pan e pitch. O cálculo de volume originalmente
chamado com entradas em `r4/r5` está expresso diretamente em C. Mantém detalhes como:

- Comparar o tempo antes do truncamento para 16 bits e conservar a subtração de 32 bits.
- Entrar na primeira trilha antes de testar a contagem, inclusive quando ela é zero.
- Usar a soma não truncada da fase do LFO e um deslocamento aritmético definido em C.
- Interpretar o último `BGT` usando os flags da adição do ponteiro, incluindo overflow signed.
- Chamar o wrapper real de limpeza, preservando a possibilidade de callback instalado em RAM.

## Validação diferencial e limites

`tools/verify_music_player.py` compila uma DLL Windows x64 com `-std=c99 -O2 -Wall -Wextra
-Werror` e chama a função C por ctypes. Executa a rotina original em Unicorn, com o modelo
ARM926 e instruções Thumb compatíveis com a ROM. Isso é emulação funcional de CPU, sem
emulação de ciclos ARM7TDMI, PPU ou hardware completo de GBA.

Foram aprovados **1.128 cenários**: 1.000 gerados com seeds determinísticos e 128 dirigidos.
Os casos dirigidos exercitam os **30 índices de comandos, 49 códigos de notas e 49 códigos de
espera**. O conjunto percorreu **290/290 instruções** da rotina original. Essa cobertura de
instruções não prova todos os estados ou todas as combinações de caminhos possíveis.

Cada cenário compara EWRAM inteira, IWRAM fora de 2 KiB de pilha temporária e os efeitos e
argumentos dos callbacks controlados. Notas, comandos, player seguinte e parada CGB usam
callbacks sintéticos para isolar a rotina. Cinquenta e nove endereços agora executam C no lado nativo;
os demais usam callbacks sintéticos controlados neste corpus. O corpus adicional de
[notas/canais](sound_update_track_hybrid.md) exercita também 128 execuções com notas reais.
O teste verifica a restauração da pilha e dos registradores preservados no lado ARM.

Oito testes novos incluem igualdade assembly e classificação separada, ROM errada, mutações
de lock/tempo/máscara, seção extra e comparação nativa. Alterações deliberadas no incremento
do relógio e no cálculo estéreo precisam produzir divergência entre C nativo e ROM. Portanto,
a validação não se limita a compilar ou comparar duas cópias do original.

## Reproduzir

Na raiz do projeto, depois de preparar as ferramentas locais:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-validation.txt
.\.venv\Scripts\python.exe tools\match_assembly.py
.\.venv\Scripts\python.exe tools\verify_music_player.py --cases 1000
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Evidências locais: `build/assembly_matching/music_player_update/report.json`,
`build/native_music_validation/report.json`, `build/verification.json` e
`build/next/music_update_investigation/audit_hybrid.py`/`audit_hybrid.json`.

## Impacto no port

Há agora um processador de músicas em C compilável no host de 64 bits e uma referência GBA
completa e reproduzível. Isso resolve esta rotina pela estratégia aprovada. O despachante
agora resolve 62 endereços em C, incluindo o [mixer PCM](pcm_mixer_native.md)
e a [inicialização de alto nível, Open e wrapper](audio_startup_native.md).
Restam serviços transitivos, dispositivos e integração
com saída de som. A DLL de validação não é um executável do jogo.

O jogo ainda não roda nativamente no Windows. Integração, gameplay, formatos e extração dos
recursos, vídeo/entrada/áudio/saves e comparação por frame continuam necessários. O quadro
atual está em [port_status.md](port_status.md).
