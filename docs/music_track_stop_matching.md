# Parada de trilha com matching integral

ROM USA `BDVE`, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
`MusicTrack_Stop`, em `src/music_track_stop.c`, reproduz integralmente
**`0x0810A98C..0x0810A9D0`: 68/68 bytes iguais à ROM**. O fim é exclusivo:
62 bytes de instruções, dois zeros de alinhamento e um literal de quatro bytes.

## Comportamento reconstruído

Se o bit `0x80` do status da trilha estiver limpo, a função retorna sem alterações.
Caso contrário, percorre a lista iniciada em `track+0x20`. Para cada canal:

1. Se o status do canal for diferente de zero, calcula `type & 7`. Para tipo
   diferente de zero, chama o callback em `gSoundInfoPointer->stopCgb`, offset `0x2C`.
   Depois zera o status do canal.
2. Zera o ponteiro de proprietário em `channel+0x2C`, inclusive quando o status
   já era zero, e avança pelo próximo canal em `channel+0x34`.
3. Ao terminar a lista, zera o primeiro canal da trilha.

O primeiro argumento, o player, não é usado por esse corpo. As views parciais de
trilha, canal e mixer estão em `include/audio.h`; os offsets são os verificados
nas instruções desta ROM.

## Compilador e origem da sequência

Esta função usa **GCC 3.4.6 para Thumb/ARM ELF**, como compilador alternativo capaz
de reproduzir a sequência. Isso não identifica o compilador histórico da Dimps.
O restante da produção conserva agbcc: 216 alvos com `-O2` e três rotinas com `-O1` (fila de mapas, carregador de fundos da abertura e `Cgb_Update`),
esses com `-mthumb-interwork`. O memset usa agbcc `-O2` sem interworking;
`Cgb_Stop` e `Audio_UnlinkChannel` usam `-O2 -mthumb-interwork -fprologue-bugfix`.
`MusicEvent_Fine` compartilha o perfil GCC 3.4.6 desta função.

O backend Thumb do agbcc selecionado não oferece um padrão para gerar o `TST`
presente nessa rotina. A mesma sequência aparece como `TrackStop` no
[arquivo assembly m4a0.s do SAT-R/sa2](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
Isso sustenta a interpretação de uma rotina de biblioteca com organização típica
de assembly; não prova que esse arquivo seja o fonte histórico deste jogo.

O perfil `gcc346` e as flags efetivas estão em `config/matching.json` e no manifesto:

```text
-O2 -mthumb -mcpu=arm7tdmi -mthumb-interwork
-fno-reorder-blocks -fno-crossjumping -fno-thread-jumps
-fno-gcse -fno-loop-optimize
```

O fonte GNU C explicita a duração dos valores e os registradores por meio de
**dez templates assembly vazios**. Eles não contêm instruções nem dados. A chamada
indireta é uma chamada C por ponteiro tipado; o próprio GCC gera `BL _call_via_r3`.
O símbolo é resolvido para `0x0810A97C`, onde a ROM contém `BX r3`, compartilhado
com o epílogo anterior. Esse ponto não foi contado como uma função C adicional.

## Alinhamento e integridade do candidato

O GCC gera uma diretiva `.align 2` antes do literal em `0x0810A9CC`. Na seção
convencional de código, o GNU as moderno preenche esses dois bytes com um NOP
Thumb, enquanto a ROM contém zeros. O atributo C `section(".data")` conserva a
geração das instruções e solicita o alinhamento com zeros da seção de entrada.
`config/music_track_stop.ld` coloca seu conteúdo completo na seção de saída
`.text`, no endereço original, em um segmento de leitura e execução.

A auditoria verifica os flags de execução da seção final e o segmento RX.
Nenhum assembly é editado depois de gerado, nenhum objeto tem seus flags
remendados e nenhum byte é recortado ou ignorado na comparação. Os 68 bytes
incluem as instruções, os dois zeros e o literal `0x03007FF0`.

## Reprodução e validação

Após `tools/setup_matching.ps1`, o setup adicional requer Git Bash e mantém os
arquivos em `tools/local/`. Não altera o PATH permanentemente:

```powershell
.\.venv\Scripts\python.exe tools\setup_gcc346.py
.\.venv\Scripts\python.exe tools\setup_gcc346.py --check
.\.venv\Scripts\python.exe tools\match.py --target music_track_stop
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O pacote é o [gcc-core-3.4.6.tar.bz2 oficial](https://gcc.gnu.org/ftp/gcc/releases/gcc-3.4.6/gcc-core-3.4.6.tar.bz2),
SHA-256 `3aab171d86e5a6c14cb9de35467a0472a7d5ef1d5b79a1df72ca533f8e82a133`.
O setup compara todos os 1.816 arquivos regulares extraídos com o pacote.
A compilação ocorre fora da árvore de fontes, sem mudanças no backend ou em
outros fontes do GCC. Dois headers de configuração gerados do libiberty recebem
o ajuste de capacidade do host para `sys_errlist`/`sys_nerr` do MinGW moderno.
Os programas geradores são compilados com `__USE_MINGW_ANSI_STDIO=1`, necessário
ao uso de `%n` pelo gerador de modos. Esses ajustes afetam a construção da
ferramenta Windows; não são patches na saída ARM.

O script foi validado também com uma construção limpa em `tools/local/gcc346-clean/`.
Esse segundo executável emitiu assembly idêntico ao da ferramenta usada na produção
e novamente reproduziu os 68 bytes completos da ROM. A prova adicional está em
`build/next/gcc346_clean_match/report.json`; a igualdade verificada é da saída ARM,
sem exigir executáveis host idênticos entre pastas de construção.

O relatório `build/matching/music_track_stop/report.json` registra o executável,
perfil, flags e hashes dos inputs e do assembly emitido. Controles negativos
trocam `0x80` por `0x40` e a máscara de canal 7 por 3 em cópias do C, recompilam
e exigem reprovação.

Esta função e o [callback serial](serial_irq_matching.md) acrescentaram 628 bytes,
levando o conjunto então verificado a 62 funções e 14.668 bytes iguais à ROM.
As etapas posteriores de [pacotes seriais](serial_packets_matching.md) e de
[sequências e fade](sequences_initialization_matching.md) levam o total atual
a **224 funções e 33.032 bytes**. A chamada dinâmica
ao callback de desligamento do canal ainda depende de outro corpo externo.
Os 190 testes passaram localmente, sem skips.
Ainda faltam dependências transitivas, build completo da ROM, execução em emulador
e a camada do port nativo para PC.
