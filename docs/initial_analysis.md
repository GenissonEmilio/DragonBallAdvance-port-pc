# Primeiro reconhecimento da ROM USA

Análise estática em 16/10/2026 da ROM com SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`. Os nomes abaixo são descritivos,
atribuídos nesta análise. Esta nota registra o reconhecimento inicial. Não houve execução em
debugger; o matching em C foi concluído posteriormente nesta mesma data e está documentado
em [compiler_findings.md](compiler_findings.md). O avanço posterior para 224 funções, incluindo
o loop e a inicialização interna, está em [main_loop.md](main_loop.md) e
[initialization_graphics.md](initialization_graphics.md).

## Fluxo de entrada verificado nas instruções

1. A instrução ARM em `0x08000000` é `B 0x080000C0`.
2. `0x080000C0` seleciona o modo IRQ e carrega sua stack de `0x03007F00`; depois
   seleciona System e carrega a stack de `0x03007FA0`.
3. Escreve o endereço `0x080000FC` em `0x03007FFC`, endereço de callback IRQ usado pela BIOS.
4. Lê `0x0810D65D` do literal em `0x080001C4` e faz `BX`: entra em Thumb em `0x0810D65C`.
5. O wrapper Thumb chama, nesta ordem, `0x0810C228`, `0x0800152C`, `0x0810C90C`.
   O wrapper tem 18 bytes de instruções e termina em `BX r0` em `0x0810D66C`.
6. `0x0800152C` é outro wrapper: chama `0x08001424` e retorna. Essa chamada **não é evidência
   de um loop principal**. `0x08001424` chama `0x080014D0`, `0x08001350`, escreve 2 no byte
   `0x02029F38`, chama `0x08001468` e retorna.

O handler em `0x080000FC` lê IE/IF juntos a partir de `0x04000200`, seleciona uma interrupção,
escreve seu bit em IF e transfere a execução para um endereço da tabela em `0x03001F10`.
O caso do bit `0x2000` contém um loop. As consequências para temporização e callbacks ainda
precisam ser observadas no debugger.

## Primeira função pequena candidata a reconstrução

`0x0800144C..0x08001464` (fim exclusivo), Thumb, 24 bytes de instruções. O literal
`0x02029F30` está em `0x08001464`. Comportamento observado:

```text
se o byte em 0x02029F30 + 0x22 for diferente de zero:
    incrementar o inteiro de 32 bits em 0x02029F30 + 0x10, módulo 2^32
retornar
```

É uma boa primeira candidata por não chamar outras funções e ter efeitos de memória pequenos.
Pode ser um contador condicionado por uma flag, mas seu significado no jogo ainda não está
estabelecido. O endereço dela aparece com bit Thumb em um literal de `0x08001468`, que a passa
ao chamar `0x0810D758`; a reconstrução posterior do criador local e do despachante confirmou
que ela é registrada como callback de uma tarefa.

Os 24 bytes de instruções e os 4 de literal agora são reproduzidos por `src/state_counter.c`
com `agbcc` GCC 2.9-arm-000512, `-O2 -mthumb-interwork`. Continua útil observar as leituras/escritas
desses campos no debugger e registrar os chamadores para estabelecer seu significado no jogo.

## Estado e limites

- Perfis de ROM, checksums e comparação exata: implementados.
- Desmontagem explícita ARM/Thumb e extração dos oito trechos do mapa: implementadas.
- Mapa de entrada: evidência estática dos endereços e instruções descritos acima.
- Compilador compatível verificado: GCC 2.9-arm-000512 (`agbcc`); executável histórico e conjunto
  completo de flags não identificados exclusivamente. Ausência de strings GCC/ARM no scan simples
  não prova a ausência dessas ferramentas na produção do jogo.
- Funções de produção reconstruídas em C/GNU C e verificadas por matching: **224**, 33.032 bytes,
  incluindo literais e padding.
- Loop principal por frame: identificado em `0x0810C90C` e reconstruído em C com 340/340 bytes iguais.
- Inicialização interna, inicialização de tarefas e seis rotinas gráficas: matching completo;
  os serviços transitivos externos continuam pendentes; os quatro processadores da tabela gráfica têm matching.
- Criação/destruição de tarefas e heaps IWRAM/EWRAM: dez alvos adicionais com matching;
  veja [tasks_memory_matching.md](tasks_memory_matching.md).
- Callback serial e parada de trilha: matching integral; veja [serial_irq_matching.md](serial_irq_matching.md)
  e [music_track_stop_matching.md](music_track_stop_matching.md). A trilha usa GCC 3.4.6 alternativo.
- Processador, construtor e validador de pacotes seriais: três alvos com matching;
  veja [serial_packets_matching.md](serial_packets_matching.md).
- Criador de sequência `0x080C863C`, primeiro inicializador filho, continuação e fade:
  doze alvos adicionais com matching; veja [sequences_initialization_matching.md](sequences_initialization_matching.md).
- Formatos de recursos, build completo e port nativo: pendentes.

As listagens exploratórias em `build/` abrangem também literal pools; não devem ser tratadas
como uma sequência inteira de código. Use `config/regions.usa.json` para reproduzir a separação
dos trechos já revisados, vinculada ao hash exato da ROM.
