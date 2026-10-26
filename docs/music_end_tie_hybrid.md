# Término de notas sustentadas: MusicEvent_EndTie

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

`0x0810AC00` está integrado ao C nativo como `Dbaa_MusicEventEndTie`. A referência GBA
reproduz **64/64 bytes em assembly separado**. O candidato C ARM permanece nonmatching:
GCC 3.4.6 gera 68 bytes, com 13 diferenças na comparação integral. Esses 64 bytes não são
atribuídos ao matching C.

O conjunto contém **242 alvos C/GNU C, 33.856 bytes**, mais **23 alvos assembly,
2.720 bytes**: **265 alvos e 36.576 bytes idênticos à ROM**. A última suíte geral (instrumento) passou em **290 testes**.
O despachante nativo atende **cinquenta e nove endereços de áudio em C**.

## Comportamento reconstruído

O comando é `0xCE`, índice 29 da tabela de eventos. `Sound_Extend` instala o endereço
`0x0810AC01` nesse slot. A entrada recebe player em `r0` e trilha em `r1`; o player não é
consultado. O nome descreve o evento `MP2K_event_endtie` da referência m4a
[SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).

1. Lê um byte no cursor `track+0x40`. Se for menor que `0x80`, atualiza `track+5` e
   avança o cursor em um byte. Caso contrário, preserva o cursor e reaproveita a nota anterior.
2. Percorre os canais a partir de `track+0x20`, seguindo `channel+0x34`.
3. Considera somente canais cujo estado tem algum bit de `0x83` e não tem `0x40`.
4. Compara a nota com **`channel+0x11`**, a nota original copiada da trilha. O campo
   `channel+8` pode representar outra nota para instrumentos de percussão.
5. Marca o **primeiro** canal compatível com `status | 0x40` e encerra a busca.

A função preserva os elos e o restante do estado do canal. Não chama a remoção da lista,
não percorre os canais posteriores depois de encontrar a nota e não limpa a trilha.
Mesmo com lista vazia, um parâmetro explícito ainda atualiza a nota e o cursor.

## Matching GBA e candidato C

`asm/music_event_end_tie.s` contém 32 instruções Thumb, sem literais e sem padding.
Preserva o prólogo `PUSH {r4,r5}` e o retorno `POP {r4,r5}; BX lr`. O gate compara todos
os 64 bytes no endereço original, rejeita seções alocadas adicionais e declara
`kind: assembly`, `counts_as_c: false`.

O C ARM experimental está em `nonmatching/music_event_end_tie.c`, com dez constraints
GNU C vazias e nenhuma instrução embutida. Os perfis GCC testados acrescentam o salvamento
de `lr` e alteram comparações/ordenação; o melhor candidato configurado continua com
68 bytes e 13 diferenças. Ele fica em `config/candidates.usa.json`, fora da produção C.

Também foi testado o Clang 19.1.7 distribuído no Zig 0.14.1, obtido da
[distribuição oficial](https://ziglang.org/download/). O arquivo foi conferido pelo SHA-256
publicado `554f5378228923ffd558eac35e21af020c73789d87afeabf4bfd16f2e6feed2c`.
Esse ensaio gerou 68 bytes de `.text` e oito bytes alocados de `.ARM.exidx`; não satisfaz o
gate integral. A rotina de salvamento do LLVM também acrescenta `lr` quando preserva
registradores baixos, como mostra o
[backend ARM da versão testada](https://github.com/llvm/llvm-project/blob/llvmorg-19.1.7/llvm/lib/Target/ARM/ARMFrameLowering.cpp#L2671).

Os resultados delimitam os perfis testados. Não houve patch de compilador, alteração do
assembly gerado, arrays de instruções, descarte de bytes ou promoção indevida do candidato C.
Zig/Clang é apenas um experimento local; não é dependência do matching de produção.

Os binários de `Sound_UpdateTrack`, `MusicEvent_EndTie` e `Music_ClearModulation` agora
reproduzem **604 bytes contínuos**, `0x0810AA00..0x0810AC5C`: 576 de assembly e 28 de C/GNU C.
Os bytes já comprovados nas etapas anteriores são contados uma única vez no total.

## C nativo e validação

`port/audio/audio_helpers.c` implementa a rotina com endereços GBA `uint32_t` e callbacks de
memória do host. `Dbaa_AudioCall` atende tanto `0x0810AC00` quanto `0x0810AC01`.
O retorno do adaptador é ignorado, pois o evento original é void.

`tools/verify_music_end_tie.py` compara o C Windows x64 com a execução da ROM em Unicorn
ARM926. Passou em **1.472 cenários**, percorrendo **32/32 instruções originais**:

- 512 combinações dirigidas de estado e correspondência de nota, incluindo todos os 256 bytes de estado.
- 256 limites de parâmetro, cobrindo todos os valores do byte de entrada.
- 128 casos de listas vazias, posições diferentes e ausência de correspondência.
- 512 casos adicionais com seeds determinísticos.
- 64 execuções do player criando uma nota sustentada com `0xCF` e liberando-a com o comando real `0xCE`.

Comparam RAM, ordem e largura das leituras observadas e efeitos dos callbacks. Os testes
também verificam pilha e registradores preservados no lado ARM. O corpus de término de notas
não recorre a fallback ARM no lado nativo, inclusive no caminho integrado de criação/liberação.
Isso é validação funcional isolada, sem boot completo ou emulação de ciclos/dispositivos GBA.

A auditoria dos 64 casos integrados confirma, em cada execução, a entrada real em
`0x0810AA00` e `0x0810AC00`. Também verifica que existe um canal de duração zero com a nota
original 60 e os flags de início/liberação ao final. Assim, a igualdade não depende de
execuções em que o player deixa de criar a nota.

Os nove testes novos incluem gates positivos, classificação separada, reprovação do C ARM
e mutações deliberadas. Usar `0x87` no teste de estado, comparar a nota em `+8`, consumir o
byte `0x80` ou continuar após a primeira correspondência deve produzir divergência.

Também voltaram a passar os 1.312 cenários de notas, 1.128 do player, 768 dos demais
auxiliares e 237.568 comparações de frequência PCM/CGB, com os fontes nativos atuais.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_end_tie
.\.venv\Scripts\python.exe tools\verify_music_end_tie.py --cases 512
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match_assembly.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O experimento abaixo tem reprovação esperada:

```powershell
.\.venv\Scripts\python.exe tools\match.py --target music_event_end_tie --function-map config\candidates.usa.json --out-dir build\candidate_music_end_tie
```

Evidências: `build/assembly_matching/music_event_end_tie/report.json`,
`build/native_music_end_tie_validation/report.json`, `build/next/music_end_tie/candidate_final/report.json`,
`build/next/music_end_tie/held_note_lifecycle.json`,
`build/verification.json` e `build/next/music_end_tie/audit_end_tie.py`/`audit_end_tie.json`.

O port ainda não é jogável. Restam comandos da tabela, mixer, saída de som, gameplay,
recursos e backend. A continuação de [LFO e modulação](music_modulation_commands.md) integrou
`0x0810AC68`, `0x0810AC7C` e o leitor compartilhado. Entre os slots alterados por
`Sound_Extend`, os dois comandos seguintes também foram concluídos em C na etapa de
[memória e comandos estendidos](music_memory_commands.md): `0x0810BFAC` e `0x0810C104`.
Veja o [estado do port](port_status.md).
