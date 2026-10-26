# Correções de instruções no tradutor nativo

A validação das instruções ARM/Thumb encontrou dois defeitos no tradutor
`gbarecomp`, revisão `ac1176f467cbb708f58785e65f36b4f091a8ab20`:

- Os deslocamentos Thumb atualizavam N/Z, mas deixavam o carry anterior.
  A instrução real `0x0805B896`, `LSL r1, r1, #18`, divergiu em 56 de 112
  combinações de valor e flags. Operações lógicas ARM com S também precisam
  receber o carry produzido pelo deslocamento ou pela rotação da constante.
- O decodificador de transferências de meia palavra não exigia bit 25 igual
  a zero. Assim, certas instruções ARM com constante, incluindo TST e TEQ,
  eram emitidas como leituras de memória.

O patch local corrige os dois casos. Os auxiliares de deslocamento distinguem
zero, 32, valores maiores que 32, rotação e RRX. Operações aritméticas mantêm
o carry de entrada necessário a ADC/SBC; o shifter não o substitui nesse caso.

`tools/verify_static_shifts.py` usa o próprio emissor C e bytes da ROM USA local
para comparar os 15 registradores visíveis e todas as flags NZCV com Unicorn.
O teste passou em **405.376 casos**, cobrindo 602 instruções selecionadas:
192 formas Thumb imediatas, oito formas Thumb por registrador e 402 formas
ARM de processamento de dados. A regressão com o tradutor anterior apresentou
**18.304 divergências em 40.960 casos Thumb**. Os relatórios locais ficam em
`build/native_static_shift_validation_v5/` e
`build/native_static_shift_old_validation/`.

Os testes incluem todas as combinações NZCV, execução condicional, valores
de fronteira e quantidades de deslocamento de até 255, usando apenas o byte
inferior do registrador. Algumas codificações foram encontradas fora da região
indicada como código: isso verifica a semântica da instrução, sem afirmar que
aquele endereço é executado pelo jogo. Operandos PC, retornos de exceção,
temporização e a ISA completa ficam fora desta comparação.

A especificação de referência é o
[ARM7DI Data Sheet, DDI 0027D](https://documentation-service.arm.com/static/5ed11a2dca06a95ce53f8f99).
O interpretador usado como oráculo é um processo de teste separado; o port
nativo continua sem interpretador ARM/Thumb compilado. Esses resultados não
alteram os 265 alvos de matching GBA nem provam equivalência do jogo inteiro.
