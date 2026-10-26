# Comando de instrumento VOICE

`MusicEvent_Voice`, em `0x0810A608`, está integrado em **C ao port nativo Windows x64**.
A reprodução GBA usa **assembly separado com 48/48 bytes idênticos à ROM USA BDVE rev0**,
SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`. O candidato agbcc continua diferente
em cinco bytes e permanece explicitamente em `nonmatching/`.

| Implementação | Bytes | Estado |
|---|---:|---|
| Referência GBA assembly | 48 | Todos os bytes iguais à ROM, incluindo 2 de alinhamento |
| C candidato agbcc GCC 2.9-arm-000512 | 48 | 5 bytes diferentes |
| C candidato GCC 3.4.6 Thumb | 48 | 41 bytes diferentes |
| C nativo Windows x64 | — | Comportamento comparado com a execução original |

O total atual é **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly e
2.720 bytes**: **265 alvos e 36.576 bytes exatos**. Há **59 endereços de áudio ligados
ao C nativo**. A última suíte geral (instrumento) passou em **290 testes, sem skips**.

## Comportamento reconstruído

O opcode `0xBD`, slot 12 da tabela de música, lê um índice sem sinal de oito bits no
cursor `track+0x40` e só então incrementa esse cursor. Essa leitura é bruta, sem chamar
o leitor filtrado dos comandos anteriores. A tabela de instrumentos está em `player+0x30`;
o registro selecionado fica em `base + 12 * índice`.

O comando lê três palavras e grava em `track+0x24`, `+0x28` e `+0x2C`, respectivamente:
tipo/atributos, ponteiro da amostra ou subgrupo, e ADSR ou mapa de teclas. Cada palavra
passa por `Sound_FilterAddress` usando o **mesmo endereço inicial do registro**, inclusive
quando os dois últimos acessos estão em outro lado do limite de endereço do filtro.
As leituras ocorrem antes da filtragem. A cópia intercala leitura e escrita; não faz uma
cópia temporária de todos os dados. Essa ordem conserva o resultado quando origem e
destino se sobrepõem. O comando não altera o status nem as notas já criadas.

O processador de notas usa o timbre selecionado para escolher o canal PCM/CGB, a amostra,
o envelope e os atributos CGB. Instrumentos agrupados e rítmicos continuam sendo resolvidos
pelo processador de notas, com seus mapas de teclas e timbres filhos.

## Fontes e matching

- C nativo: [audio_helpers.c](../port/audio/audio_helpers.c), função `Dbaa_MusicEventVoice`.
- API e despacho: [audio_helpers.h](../port/include/audio_helpers.h) e `Dbaa_AudioCall`;
  aceita endereço par ou ponteiro Thumb e conserva os endereços GBA como inteiros de 32 bits.
- Assembly exato: [music_event_voice.s](../asm/music_event_voice.s).
- C ARM não correspondente: [music_event_voice.c](../nonmatching/music_event_voice.c).
- Verificação funcional: [verify_music_voice.py](../tools/verify_music_voice.py).
- Controles negativos: [test_music_voice.py](../tests/test_music_voice.py).

O original salva LR em `r12` e chama três vezes o filtro com argumentos/resultado em
`r2/r3`, preservando outros registradores. Os compiladores testados emitem outro
prólogo/epílogo; o candidato C usa apenas restrições GNU C vazias, sem instruções embutidas.
No candidato agbcc, os 42 bytes entre a entrada e o epílogo já coincidem. As cinco
diferenças restantes estão na preservação de LR e no retorno/alinhamento; o gate completo
continua reprovando esse candidato. A convenção também aparece na referência local do
[m4a0.s do SA2 em revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A ROM local determina os bytes e os endereços desta reconstrução.

O gate compara o `.text` completo linkado no endereço original. Rejeita seções alocadas
extras e relocations restantes. Não há recortes, máscaras, substituição de bytes ou edição
do assembly gerado. As **20 instruções e os dois bytes finais** compõem os 48 bytes.
A região de áudio `0x0810A4AC..0x0810A638` na etapa de instrumento tem **396 bytes contínuos idênticos**.

## Validação

Passaram **2.283 cenários** contra a ROM executada em Unicorn:

- 5 controles dirigidos, 1.024 combinações dos 256 instrumentos com quatro estados e
  outros 256 bytes de status.
- 66 sobreposições, 30 limites do filtro, 6 parâmetros em endereço baixo e 64 registros
  de dados da ROM.
- 512 casos aleatórios com seed fixa.
- 256 sequências de seleção e criação de notas e 64 sequências de troca de instrumento.

As **320 sequências do player real** somam **384 atualizações**. Verificam os três
campos copiados, PCM/CGB, subgrupos e ritmos, ponteiros de amostras, ADSR, atributos CGB,
cursores e a preservação das notas existentes após a troca. As 384 frequências de notas
novas são conferidas com chamadas independentes às rotinas PCM/CGB da ROM.

RAM, ordem das leituras observadas e callbacks foram iguais. SP e registradores preservados
também são verificados. Todas as 20 instruções do comando foram percorridas; padding entra
no gate binário. Nenhum serviço novo recorre a ARM no lado nativo. Os dez corpora anteriores
foram reexecutados com os fontes e headers atuais.

Os nove testes próprios incluem mutações do passo de 12 bytes, destino, leitura bruta,
endereço usado no filtro e ordem da cópia. As mutações devem falhar. Unicorn ARM926 é usado
para comparação funcional; a prova não cobre ciclos de ARM7TDMI, dispositivos GBA completos,
boot integral ou equivalência de bytes do executável Windows.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_voice
.\.venv\Scripts\python.exe tools\verify_music_voice.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Evidências locais: `build/native_music_voice_validation/report.json`,
`build/assembly_matching/music_event_voice/report.json`, `build/next/music_voice/tests_all.log`
e `build/verification.json`.

## Estado do port

Após `Sound_Extend`, **36 dos 36 slots** têm binding C nativo. A
[configuração de frequência](sound_frequency_native.md), `0x0810B22C`, e
VSync-on estão integradas. Ainda faltam serviços transitivos, mixer e dispositivos
do backend. Esses números medem a tabela, sem representar a conclusão do áudio ou do jogo.

O port ainda não é jogável. Faltam mixer, backend de áudio/vídeo/entrada, integração da
inicialização, recursos, saves e sistemas de gameplay, seguidos de comparação durante o
jogo completo. Veja o [estado atual do port](port_status.md).

O [comando de volume](music_volume_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, nove testes próprios e reexecução dos doze corpora nativos.

O [comando de pan](music_pan_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos treze corpora nativos.

O [pitch bend](music_pitch_bend_command.md) foi integrado na etapa seguinte, com
20 bytes assembly exatos, doze testes próprios e reexecução dos quatorze corpora nativos.
