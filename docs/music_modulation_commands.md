# Comandos de velocidade do LFO e intensidade da modulação

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

`0x0810AC68` e `0x0810AC7C` estão reconstruídos em C para Windows x64 e ligados ao
despachante nativo. Seus **20 bytes por comando têm matching em assembly separado**.
O auxiliar compartilhado `0x0810AC5C` reproduz **12/12 bytes em C/GNU C**.
Os candidatos ARM C dos comandos continuam nonmatching: 32 bytes e 32 diferenças cada.

O agregado contém **242 alvos C/GNU C, 33.856 bytes**, e **23 alvos assembly,
2.720 bytes**: **265 alvos e 36.576 bytes idênticos à ROM**. A última suíte geral (instrumento) passou em **290 testes
aprovados**, sem skips; a execução atual está documentada na etapa de [memória e comandos estendidos](music_memory_commands.md). O despachante nativo
atende **cinquenta e nove endereços de áudio em C**.

## Comportamento e convenção de chamada

| Entrada USA | Nome descritivo | Evento | Efeito |
|---|---|---|---|
| `0x0810AC5C` | `Music_ReadCommandByte` | Auxiliar | Incrementa `track+0x40` e lê o byte apontado pelo cursor anterior |
| `0x0810AC68` | `MusicEvent_LfoSpeed` | `0xC2`, slot 17 | Grava o parâmetro em `track+0x19`, velocidade do LFO |
| `0x0810AC7C` | `MusicEvent_ModDepth` | `0xC4`, slot 19 | Grava o parâmetro em `track+0x17`, intensidade da modulação |

Os dois eventos consomem exatamente um byte, inclusive quando o bit alto está ativado.
Não usam o mecanismo de parâmetro opcional de notas. Quando o valor é zero, chamam
`Music_ClearModulation` em `0x0810AC40`: zeram a modulação calculada em `+0x16` e a fase
em `+0x1A`; marcam o estado da trilha com `0x0C` se o tipo em `+0x18` for zero, ou `3`
caso contrário. Valores diferentes de zero preservam esses campos e os flags existentes.

O auxiliar incrementa o cursor **antes** de ler o byte. A distinção é observável quando
o cursor aponta para dentro do próprio campo `track+0x40`. O C nativo preserva essa ordem.

A convenção interna do SDK recebe a trilha em `r1` e deixa o byte em `r3`. O auxiliar não
tem retorno C convencional em `r0`: sua declaração ARM é void e o fonte GNU C fixa os
registradores com quatro constraints vazias, uma volatile. Não há instruções embutidas.
O matching cobre dez bytes de instruções e dois zeros de alinhamento.
No port, `Dbaa_MusicReadCommandByte` devolve o byte pelo retorno normal de uma função C.

Cada evento GBA guarda `lr` em `r12`, chama o auxiliar, grava `r3`, chama a limpeza se
necessário e retorna por `BX r12`. São sete instruções, 18 bytes, mais dois zeros de
alinhamento. As entradas coincidem com `MP2K_event_lfos` e `MP2K_event_mod` da referência
[SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
Os nomes e a coincidência não identificam exclusivamente o SDK histórico da Dimps.

## Matching e integração

`src/music_read_command_byte.c` usa agbcc GCC 2.9-arm-000512 com o perfil padrão
`-O2 -mthumb-interwork`. O manifesto declara as quatro constraints e o gate compara os
12 bytes completos no endereço original. Os símbolos antigos de `Sound_Extend` permanecem
aliases dos nomes descritivos, com os mesmos ponteiros Thumb nos slots 17 e 19.

Os candidatos C ARM em `nonmatching/` foram testados com agbcc e GCC 3.4.6. Ambos geraram
32 bytes por comando: preservam registradores e retorno na pilha, divergindo da convenção
manual observada. Os candidatos continuam fora de `config/functions.usa.json`; a igualdade
dos 40 bytes pertence a `asm/music_event_lfo_speed.s` e `asm/music_event_mod_depth.s`.
Não houve patch do compilador, alteração do assembly gerado, descarte de bytes ou máscaras.

`port/audio/audio_helpers.c` implementa os três serviços em C99. `Dbaa_AudioCall` aceita tanto
endereços pares quanto ponteiros Thumb. Os eventos chamam o auxiliar e a limpeza pelos
bindings C. A implementação não executa ARM para nenhum desses serviços.

O conjunto formado por notas, término de notas, limpeza da modulação, leitor, dois eventos e
frequência PCM reproduz **756 bytes contínuos**, `0x0810AA00..0x0810ACF4`: 140 de C/GNU C
e 616 de assembly. A etapa acrescenta somente 52 bytes novos ao agregado.

## Validação nativa

`tools/verify_music_modulation.py` compila uma DLL Windows x64 com warnings tratados como
erros e compara a execução C com a ROM em Unicorn ARM926. Passou em **2.576 cenários**:

- 256 leituras com retorno do auxiliar em `r3` no ARM e pelo retorno normal no C nativo.
- 256 parâmetros de velocidade e 256 de intensidade, cobrindo todos os valores do byte.
- 1.024 combinações de estado, tipo de modulação e evento com parâmetro zero.
- 144 casos com parâmetros dentro da trilha, incluindo os quatro bytes do cursor.
- 512 casos adicionais com seeds determinísticos.
- 128 execuções do player com os comandos reais, criação de nota sustentada e término.

Foram percorridas **32/32 instruções** da limpeza, auxiliar e dois eventos. Todos os casos
do player verificam que os três novos serviços foram realmente alcançados e que existe uma
nota sustentada marcada para liberação ao final. Os casos de zero verificam também o
reinício da modulação e da fase. Não houve fallback ARM no lado nativo.

Comparam RAM fora da pilha temporária, callbacks, ordem/largura das leituras observadas e
o retorno definido do auxiliar. Conferem pilha e registradores preservados no lado ARM.
Isso valida comportamento isolado; não é boot completo nem modelagem de ciclos ou hardware GBA.

Os treze testes novos incluem mutações deliberadas nos campos de destino, incremento e
offset de leitura, condição de limpeza, ordem com cursor aliased e extensão signed do byte.
Também comprovam a classificação separada dos candidatos C e do matching assembly.
Na etapa anterior de LFO/modulação, 231 de 232 testes passaram na primeira execução geral. O teste restante encontrou uma declaração
duplicada incompatível no candidato antigo `nonmatching/sound_update_track.c`. A declaração
foi removida para usar o protótipo de `audio.h`, sem alterar a lógica ou fontes de produção.
O teste afetado foi reexecutado e passou. Os três experimentos desse candidato também foram
recompilados: mantiveram as divergências esperadas; o perfil `-O1` continua rejeitado pela
seção `.rodata` alocada extra. Os logs preservam a falha inicial e a reexecução separadamente.
Os corpora anteriores voltaram a passar com os fontes atuais: 1.128 casos do player,
768 auxiliares, 1.312 notas, 1.472 términos de notas e 237.568 cálculos PCM/CGB.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target music_read_command_byte
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_lfo_speed
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_mod_depth
.\.venv\Scripts\python.exe tools\verify_music_modulation.py --cases 512
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match_assembly.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Evidências: `build/matching/music_read_command_byte/report.json`,
`build/assembly_matching/music_event_lfo_speed/report.json`,
`build/assembly_matching/music_event_mod_depth/report.json`,
`build/native_music_modulation_validation/report.json`, `build/verification.json` e
`build/next/music_modulation_commands/audit_modulation.py`/`audit_modulation.json`.

O port ainda não é jogável. A continuação de [memória e comandos estendidos](music_memory_commands.md)
reconstruiu `0x0810BFAC`, `0x0810C104` e seus serviços em C/GNU C com matching. Os nove slots
substituídos por `Sound_Extend` têm matching GBA; comandos padrão, mixer, dispositivos e
integração ainda precisam de trabalho. Veja o [estado completo do port](port_status.md).
