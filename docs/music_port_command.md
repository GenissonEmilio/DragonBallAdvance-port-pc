# Comando PORT: escrita em registradores

`MusicEvent_Port`, em `0x0810A6C0`, está reconstruído em **C para o port Windows x64**.
O build GBA usa **assembly separado com 24/24 bytes idênticos à ROM USA BDVE rev0**,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

| Implementação | Bytes | Resultado |
|---|---:|---|
| Assembly GBA | 24 | Todos iguais: 20 bytes de instruções e 4 de literal, sem padding |
| C candidato agbcc GCC 2.9-arm-000512 | 28 | 15 diferenças, incluindo quatro bytes extras |
| C candidato GCC 3.4.6 Thumb | 28 | 18 diferenças, incluindo quatro bytes extras |
| C nativo Windows x64 | — | RAM, espelho de I/O e acessos ordenados comparados com a ROM |

O agregado contém **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly e
2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio nativos**.
A região `0x0810A4AC..0x0810A6D8` contém **556 bytes contínuos idênticos**.

## Comportamento reconstruído

O opcode `0xCC`, slot 27 da tabela de música, consome dois bytes:

1. Lê o seletor diretamente do cursor da faixa, sem aplicar o filtro de endereço.
2. Avança e armazena o cursor para depois dos dois parâmetros.
3. Lê e filtra o segundo byte usando a entrada interna `0x0810A54A` do leitor.
4. Faz uma única escrita de **um byte** em `0x04000060 + seletor`.

O literal `0x04000060` está em `0x0810A6D4`. Não há clamp do seletor: os 256 valores
podem alcançar `0x04000060..0x0400015F`, inclusive endereços fora dos registradores
de som. Um valor lido de endereço rejeitado vira zero; o seletor permanece cru.
As flags e os parâmetros da faixa não são alterados, exceto pelo avanço do cursor.
A ordem de atualização importa quando os parâmetros se sobrepõem ao próprio cursor.

O original salva LR em `r12`, preserva o destino em `r0` e recebe o valor em `r3`.
A entrada interna do leitor usa o ponteiro já avançado em `r2`. Esse contrato privado
do SDK explica por que uma chamada C convencional não reproduziu a imagem completa.
O candidato ARM usa uma restrição GNU C vazia e continua fora do matching C.

No nativo, `Dbaa_MusicEventPort` usa endereços GBA de 32 bits e os callbacks do host.
`host->write` recebe endereço, valor e largura 1. O backend deve preservar a ordem
e a quantidade das escritas e implementar os efeitos dos dispositivos correspondentes.

## Fontes e prova de bytes

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), `Dbaa_MusicEventPort`.
- API: [audio_helpers.h](../port/include/audio_helpers.h) e [music_player.h](../port/include/music_player.h).
- Assembly GBA: [music_event_port.s](../asm/music_event_port.s).
- C ARM não correspondente: [music_event_port.c](../nonmatching/music_event_port.c).
- Validação: [verify_music_port.py](../tools/verify_music_port.py) e [test_music_port.py](../tests/test_music_port.py).

O gate compara todo o `.text` linkado no endereço original, incluindo o literal.
Rejeita seções alocadas extras e relocations restantes. Não usa máscaras, recortes
ou alterações no assembly gerado. Os 24 bytes assembly são contabilizados à parte
dos fontes C com matching. A equivalência funcional do C Windows é outra prova.

## Validação desta etapa

Passaram **3.471 cenários**, com **3.983 escritas PORT observadas**:

- 5 controles, 1.024 combinações de seletores e 1.024 combinações de valores.
- Todos os 256 bytes de status, 72 sobreposições de campos e cursor.
- 16 fontes filtradas, 16 em I/O, 16 em IWRAM, 16 na ROM e dois limites de endereço,
  incluindo wrap do cursor de 32 bits.
- 512 casos aleatórios determinísticos.
- 256 sequências antes da criação de nota e 256 com uma nota ativa.

As **512 sequências reais do player** somam **1.024 atualizações**. Cada sequência
executa dois PORT sucessivos no mesmo endereço. O espelho de I/O é carregado na
atualização seguinte; o estado de software da nota existente permanece igual.
As nove instruções originais foram exercitadas. A comparação inclui RAM do jogo,
leituras e escritas na ordem observada, largura, endereço e valor, bytes adjacentes,
SP e registradores preservados. Nenhum serviço novo faz fallback ARM no lado nativo.

Passaram os **12 testes próprios**, incluindo mutações de literal, endereço,
largura, cursor, filtro do valor, filtro indevido do seletor, ordem das leituras
e duplicação de escrita. Os **19 corpora nativos de áudio** foram reexecutados
com os fontes e headers finais, assim como os gates dos **242 alvos C e 22 assembly**.
A suíte geral contém **383 testes** e não foi reexecutada integralmente; a última
execução completa foi a de 290 testes da etapa de instrumento.

O modelo de I/O destes testes é **um espelho plano com rastreamento do barramento**.
Ele confere que o comando emite a operação correta, mas não implementa efeitos
dos dispositivos, como bits de disparo, escrita somente ou limpeza de flags.
Não valida som audível. Unicorn ARM926 fornece comparação funcional; ciclos
ARM7TDMI, boot integral e execução do jogo completo continuam pendentes.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_port
.\.venv\Scripts\python.exe tools\verify_music_port.py --cases 512
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_port.py -v
```

Evidências: `build/native_music_port_validation/report.json`,
`build/assembly_matching/music_event_port/report.json`,
`build/next/music_port/tests_target.log` e `build/verification.json`.

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada,
inicialização integrada, recursos, saves e sistemas de gameplay, seguidos da
validação durante o jogo completo. Veja o [estado atual](port_status.md).
