# Padrões, retorno e repetição de música

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Atualizado em 20/10/2026.

`0x0810A574` é o comando de chamada de padrão, identificado aqui como
`MusicEvent_Pattern`. A chamada, o retorno, a repetição e o leitor auxiliar têm
**versões C integradas ao port nativo**. No build GBA, **20 bytes têm matching C/GNU C**
e **88 bytes têm matching assembly separado**, seguindo a divisão já adotada no áudio.
Os candidatos ARM C dos três alvos restantes diferem e continuam fora da produção C.

| Alvo | Endereço USA | Instruções | Padding | Total | Matching GBA |
|---|---|---:|---:|---:|---|
| `MusicEvent_Pattern` | `0x0810A574` | 26 | 2 | 28 | Assembly |
| `MusicEvent_PatternEnd` | `0x0810A590` | 20 | 0 | 20 | C/GNU C |
| `MusicEvent_Repeat` | `0x0810A5A4` | 46 | 2 | 48 | Assembly |
| `Music_ReadCommandFiltered` | `0x0810A548` | 10 | 2 | 12 | Assembly |
| **Total novo** | | **102** | **6** | **108** | |

Os binários completos foram montados ou compilados e linkados nos endereços originais.
Todos os bytes, incluindo os seis zeros de alinhamento, coincidem. Não há máscaras,
recortes, seções alocadas ocultas, relocations restantes ou edição do assembly gerado.
Somados aos auxiliares anteriores e a `MusicEvent_Goto`, reproduzem **296/296 bytes contínuos**
em `0x0810A4AC..0x0810A5D4`, sem contar regiões sobrepostas duas vezes.

O agregado atual é **242 funções C/GNU C e 33.856 bytes**, mais **23 alvos assembly e
2.720 bytes**: **265 alvos e 36.576 bytes idênticos à ROM**. Foram validados
**290 testes na última suíte geral (instrumento), sem skips**. O despachante nativo atende **59 endereços em C**.

## Fluxo dos comandos

A tabela original em `0x08A67460` contém GOTO, PATT, PEND e REPT nos índices 1 a 4.
No fluxo de música, os opcodes correspondentes são `B2`, `B3`, `B4` e `B5`.

PATT lê a profundidade em `track+2`. Abaixo de três, salva `command+4` em
`track+0x44+4*profundidade`, incrementa a profundidade e salta para GOTO. A pilha
possui três endereços de retorno de 32 bits. Se a profundidade já é três ou maior,
salta diretamente para `MusicEvent_Fine`, que encerra a trilha e remove seus canais.
Esses saltos são diretos para código, sem consulta ao callback GOTO em RAM.

PEND não faz nada com profundidade zero. Nos outros casos, decrementa a profundidade
e restaura o cursor pelo slot correspondente. A ROM não limita uma profundidade
corrompida a três; o C mantém esse acesso e os testes cobrem os 256 valores do byte.

REPT recebe um byte de contagem e um endereço de quatro bytes. Com contagem zero,
avança sobre o byte e salta incondicionalmente pelo corpo compartilhado de GOTO.
Com contagem não zero, incrementa `track+3`, grava o byte e conserva o incremento
completo para a comparação: **255 + 1 é comparado como 256**, mesmo que o byte gravado
seja zero. O leitor avança o cursor antes de ler e filtrar a contagem. Se o incremento
for menor, repete pelo endereço; caso contrário, zera o contador e salta os cinco
bytes de parâmetros. A versão nativa preserva também a ordem dos acessos quando
os parâmetros e os campos da trilha compartilham memória.

O leitor de `0x0810A548` retorna o resultado em `r3`, mantém em `r2` a origem lida e
salta ao filtro de endereço de `0x0810A52E`. A leitura acontece depois da escrita
do cursor e antes da rejeição do endereço. O filtro desta ROM zera o valor lido
abaixo de `0x02000000`; a leitura continua observável. GOTO reaproveita a leitura
filtrada do byte baixo do endereço, conforme a etapa anterior.

## Matching C e referência assembly

O C de PEND está em [music_event_pattern_end.c](../src/music_event_pattern_end.c).
Usa agbcc GCC 2.9-arm-000512 com `-O2 -mthumb-interwork -fprologue-bugfix` e três
restrições GNU C vazias para preservar os registradores e a forma do fluxo. Não
contém instruções assembly embutidas. O compilador permanece inalterado.

As outras três entradas usam saltos para trechos externos compartilhados; REPT entra
em GOTO depois de seu `push {lr}`, e o leitor usa a convenção de retorno em `r3`.
Os compiladores testados não reproduziram esse fluxo nos candidatos C:

| Candidato | Bytes ROM | agbcc: bytes / diferenças | GCC 3.4.6: bytes / diferenças |
|---|---:|---:|---:|
| PATT | 28 | 52 / 51 | 40 / 40 |
| REPT | 48 | 72 / 70 | 76 / 75 |
| Leitor filtrado | 12 | 28 / 28 | 28 / 28 |

As referências estão em [music_event_pattern.s](../asm/music_event_pattern.s),
[music_event_repeat.s](../asm/music_event_repeat.s) e
[music_read_command_filtered.s](../asm/music_read_command_filtered.s).
São fontes assembly explícitos, registrados em `config/assembly.usa.json` e excluídos
da contagem C. Os candidatos ficam em `nonmatching/`, com manifest próprio.

A referência pública da biblioteca ajuda a reconhecer os eventos e a convenção de
registradores: [m4a0.s do SA2, revisão fixa](https://github.com/SAT-R/sa2/blob/393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d/src/lib/m4a/m4a0.s).
A identidade dos bytes é verificada contra a ROM local, não inferida desse projeto.

## Integração e validação nativa

As quatro funções estão em [audio_helpers.c](../port/audio/audio_helpers.c), com API
em [audio_helpers.h](../port/include/audio_helpers.h). `Dbaa_AudioCall` resolve seus
endereços com ou sem bit Thumb. Os endereços do jogo continuam inteiros de 32 bits;
os ponteiros do host Windows x64 não são truncados. A chamada do padrão usa GOTO e FINE
em C; o nativo não executa ARM para os 35 serviços ligados.

[verify_music_patterns.py](../tools/verify_music_patterns.py) compara o C Windows x64
com as rotinas originais executadas em Unicorn. Passaram **4.056 cenários**:

- 10 controles dirigidos, incluindo wrap do contador e leitura com alias do cursor.
- 512 casos de profundidade: todos os bytes de PATT e de PEND.
- 2.048 combinações de contador com limites de contagem e outros 256 casos de contagem.
- 256 bytes do leitor, 48 origens filtradas e 30 casos de memória compartilhada.
- 512 casos aleatórios com seed fixa.
- 384 execuções do player real: 64 para cada profundidade de 1 a 3, 64 encerramentos
  por excesso de profundidade, 64 repetições finitas e 64 saltos com contagem zero.

Cada comparação verifica RAM do jogo, sequência e largura das leituras observadas,
callbacks, resultado definido do leitor, SP e registradores preservados. Os casos do
player exigem que os handlers reais sejam alcançados, conferem os cursores de retorno,
os contadores e a nota sustentada criada/liberada. Os casos de excesso de profundidade
exigem encerramento e remoção dos canais. Foram percorridas as **50 instruções** dos
quatro alvos, excluindo padding da medida de cobertura. Não houve fallback para ARM.

Na etapa original de padrões, 260 dos 261 testes passaram na execução geral. O teste agregado de assembly ainda
esperava o total antigo de 1.308 bytes; foi atualizado para 1.396 e passou na reexecução.
A alteração do teste se limita a esse literal, e os fontes de produção permaneceram
inalterados. Os logs da execução geral e da correção são registrados separadamente.

Os testes incluem controles negativos para limite da pilha, índice/stride de retorno,
wrap do contador, ordem da leitura, destino de saída e filtro. Mudanças intencionais
precisam falhar. Os corpora anteriores de player, memória/XCMD, auxiliares, notas,
término, modulação e frequências foram reexecutados com os fontes e headers atuais.
Essa validação funcional isolada não constitui boot do jogo, temporização do GBA ou
matching de bytes do binário Windows.

```powershell
.\.venv\Scripts\python.exe tools\match.py --target music_event_pattern_end
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_pattern
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_event_repeat
.\.venv\Scripts\python.exe tools\match_assembly.py --target music_read_command_filtered
.\.venv\Scripts\python.exe tools\verify_music_patterns.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Próximo trecho do port

Os comandos seguintes, incluindo [PORT](music_port_command.md), foram integrados.
Após `Sound_Extend`, os 36 slots têm binding C nativo, incluindo
[configuração de frequência](sound_frequency_native.md). Restam serviços transitivos,
mixer e dispositivos do backend. Essa contagem não mede a conclusão do jogo. O port ainda não é jogável: não há executável
integrado nem abertura validada no Windows. Gameplay, recursos, renderização, entrada,
saves e comparação de execução completa continuam descritos no [estado do port](port_status.md).

A última suíte geral passou em 290 testes na etapa de instrumento. A etapa de volume
acrescentou nove testes próprios aprovados e reexecutou os doze corpora de áudio.
