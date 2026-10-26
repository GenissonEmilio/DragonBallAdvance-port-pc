# Sound_UpdateTrack: notas e seleção de canais

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

O processador de notas `0x0810AA00` está integrado ao C nativo e sua referência GBA reproduz
**512/512 bytes em assembly separado**. A versão C ARM ainda diverge e permanece em
`nonmatching/sound_update_track.c`, excluída do matching C. Esta etapa segue a divisão entre
C para o port e assembly GBA usada nas rotinas anteriores da biblioteca m4a.

| Resultado desta etapa | Fonte | Validação |
|---|---|---|
| `Sound_UpdateTrack`, GBA | `asm/sound_update_track.s` | 512 bytes: 502 de instruções, dois de alinhamento e oito de literais |
| `Sound_UpdateTrack`, host | `port/audio/audio_helpers.c` | C99 Windows x64, comparado à execução original da ROM |
| `Music_ClearModulation`, GBA | `src/music_clear_modulation.c` | **28/28 bytes C/GNU C idênticos**, em `0x0810AC40..0x0810AC5C` |
| Reinício da modulação, host | `Dbaa_MusicClearModulation` | C nativo, chamado pelas notas e pelo despachante |

O agregado contém **242 alvos C/GNU C e 33.856 bytes**, mais **23 alvos assembly e
2.720 bytes**: **265 alvos, 36.576 bytes exatos**. A última suíte geral (instrumento) passou em **290 testes**, sem skips.
Os 512 bytes de assembly não aumentam a contagem de matching C.

## Reconstrução e gate de bytes

A sequência corresponde ao processador `MP2K_event_nxx` da referência
[SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
Os endereços, acessos, limites e destinos de chamadas foram conferidos nesta ROM. Essa
coincidência não identifica exclusivamente o SDK histórico do jogo.

A entrada recebe o índice de duração em `r0`, o player em `r1` e a trilha em `r2`. Salva
`r4..r7/lr`, copia `r8..r11` para `r4..r7` em ordem crescente, salva esse grupo e reserva
24 bytes locais. A saída restaura oito registradores em um único POP, move quatro valores
para os registradores altos e retorna com `POP {r0}; BX r0`.

O auxiliar de volume em `0x0810A9D0` também recebe os ponteiros por `r4/r5`. No port, sua
aritmética está expressa diretamente em C, sem executar esse trecho ARM. No build GBA, ele
continua sendo uma dependência original externa ao conjunto matching.

Os experimentos C preservados produziram:

| Perfil ARM C | Resultado integral |
|---|---|
| agbcc, `-O2 -mthumb-interwork` | 612 bytes, 588 diferenças sobre a região completa |
| agbcc, `-O1 -mthumb-interwork` | Rejeitado por seção `.rodata` alocada extra; não recebe resultado de matching |
| GCC 3.4.6, perfil configurado | 572 bytes, 552 diferenças |

O prólogo gerado pelo GCC 3.4.6 move os registradores altos em ordem inversa à referência,
e os corpos/epílogos também divergem. Não foram usados patches no compilador, reordenação
do assembly gerado, arrays de instruções, máscaras ou truncamento para fabricar igualdade.
Os experimentos delimitam os perfis testados; não provam impossibilidade em todos os compiladores.

`tools/match_assembly.py` compara o bloco completo no endereço original, incluindo os dois
literais `gSoundInfoPointer` e `gMusicWaitTable` e o alinhamento com zero. O manifesto declara
explicitamente `kind: assembly` e `counts_as_c: false`.

`Music_ClearModulation` zera a modulação calculada e a fase do LFO, depois marca volume ou
pitch para recálculo conforme o tipo da modulação. Seus 28 bytes incluem dois de alinhamento.
Usa agbcc `-O2 -mthumb-interwork -fprologue-bugfix` e quatro constraints GNU C vazias, declaradas
no manifesto. Essas constraints não contêm instruções.

## Lógica nativa

`Dbaa_SoundUpdateTrack` mantém endereços do GBA em 32 bits e usa os callbacks do host para
memória e chamadas. O despachante atende `0x0810AA00` e `0x0810AC40`, aceitando endereço par
ou ponteiro Thumb. Com as continuações de [término de notas sustentadas](music_end_tie_hybrid.md)
e [LFO/modulação](music_modulation_commands.md),
agora são **cinquenta e nove endereços de áudio atendidos em C nativo**.

A rotina:

1. Lê a duração e até três parâmetros opcionais: nota, velocidade e duração adicional.
   Um byte com bit alto encerra os parâmetros; os valores omitidos são reaproveitados.
2. Resolve o instrumento direto, a tabela dividida por nota ou o instrumento de percussão.
   Instrumentos filhos com novos marcadores de divisão/percussão encerram o evento.
3. Soma e satura a prioridade. CGB usa o canal específico; PCM procura um livre ou escolhe
   um canal existente. Prefere canais em liberação, depois menor prioridade, depois maior
   endereço de trilha proprietária; empates completos permitem que o último canal vença.
4. Remove o canal da lista antiga pelo callback em RAM e o insere na cabeça da trilha.
   Reinicia o atraso/LFO, atualiza volume e pitch e instala os dados do instrumento.
5. Aplica nota, pan de percussão, envelope, eco, comprimento e sweep CGB quando cabíveis.
   Calcula a frequência PCM ou consulta o callback CGB instalado em `SoundInfo+0x30`.
6. Marca o canal para início e limpa os bits inferiores de atualização da trilha.

A busca PCM inspeciona o primeiro canal mesmo quando a contagem é zero, como a referência.
Os desempates usam endereços unsigned de 32 bits. Pitch negativo é limitado a zero; a chamada
de frequência conserva a redução original a oito bits. As rotinas originais são void; o
valor devolvido pelo adaptador de despacho não tem significado para esses serviços.

## Validação nativa

`tools/verify_sound_update_track.py` compila uma DLL Windows x64 e compara com as rotinas
originais em Unicorn ARM926. O corpus passou em **1.312 cenários**:

- 1.152 eventos isolados: 128 dirigidos e 1.024 com seeds determinísticos.
- 128 execuções de `MusicPlayer_Update` com o callback real `0x0810AA01` e o comando de fim real.
- 32 casos adicionais de reinício da modulação.

Foram percorridas **245/245 instruções** do processador de notas. Essa cobertura não equivale
a todas as combinações possíveis de estados. Os casos incluem os quatro comprimentos de
parâmetros, doze tipos de instrumento, canais livres/ativos/em liberação, prioridades e
proprietários empatados, banco CGB ausente, contagem PCM zero, pan signed, notas extremas,
saturação, callback de frequência substituído e callback de remoção substituído.

Comparam EWRAM, IWRAM fora da pilha temporária, leituras observadas de comandos/instrumentos,
efeitos e argumentos dos callbacks. Conferem pilha e registradores preservados no lado ARM.
Os cinquenta e nove alvos nativos não são delegados ao ARM. As substituições de callbacks são sintéticas
e controladas; os testes não fazem boot completo nem modelam ciclos ARM7TDMI ou dispositivos GBA.

O player também voltou a passar nos **1.128 casos** do corpus anterior; os demais auxiliares
nos **768 casos**, e as frequências PCM/CGB nas **237.568 comparações**. O corpus anterior
de player mantém notas sintéticas para isolamento; o novo corpus acrescenta o despacho real.

Os doze testes novos verificam matching e classificação separados, rejeição do candidato C,
mutações dos bytes GBA, flags da modulação e alterações deliberadas em parsing, seleção,
desempates e callbacks nativos. Uma implementação alterada deve divergir da ROM.

```powershell
.\.venv\Scripts\python.exe tools\match_assembly.py --target sound_update_track
.\.venv\Scripts\python.exe tools\match.py --target music_clear_modulation
.\.venv\Scripts\python.exe tools\verify_sound_update_track.py --cases 1024
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match_assembly.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O comando abaixo é um experimento explicitamente **nonmatching**, com saída de reprovação esperada:

```powershell
.\.venv\Scripts\python.exe tools\match.py --target sound_update_track --function-map config\candidates.usa.json --out-dir build\candidate_sound_update_track
```

Evidências locais: `build/assembly_matching/sound_update_track/report.json`,
`build/matching/music_clear_modulation/report.json`, `build/native_sound_update_track_validation/report.json`,
`build/next/sound_update_track/agbcc_o2/report.json`, `build/next/sound_update_track/gcc346/report.json`,
`build/verification.json` e `build/next/sound_update_track/audit_track.py`/`audit_track.json`.

O port ainda não é jogável. O áudio precisa dos serviços transitivos, dispositivos do host, mixer e saída de som;
o jogo completo também exige gameplay, recursos, backend e integração. A continuação de [término de notas sustentadas](music_end_tie_hybrid.md) integrou `0x0810AC00`.
Os comandos `0x0810AC68` e `0x0810AC7C` também foram integrados na etapa de
[LFO e modulação](music_modulation_commands.md). Veja o [estado do port](port_status.md).
