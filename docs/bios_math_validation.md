# ArcTan e ArcTan2 no runtime nativo

A implementação anterior de `ArcTan2` somava meia volta ao ângulo calculado:
para `(x=1, y=0)`, retornava `0x8000` em vez de zero. `ArcTan` também usava
uma aproximação cúbica com possibilidade de overflow com sinal. O wrapper
original da ROM USA em `0x08115A80` executa SWI `0x0A`; há chamadas desse
wrapper em rotinas do jogo, incluindo `0x0807ABE8` e `0x0807F7C6`.

`port/include/bios_math.h` substitui essas aproximações por aritmética inteira,
com o polinômio de ponto fixo e as regras de quadrantes da referência mGBA
fixada no projeto. As multiplicações preservam explicitamente a palavra
inferior de 32 bits. O arquivo é uma adaptação sob MPL-2.0, com seus avisos.

Passaram **196.833 casos**, comparando R0, R1, R2 e R3:

- Todos os 65.536 valores com sinal de 16 bits em `ArcTan`.
- 131.297 pares em `ArcTan2`, incluindo eixos, fronteiras de quadrantes,
  extremos de 16 bits e pares pseudoaleatórios reproduzíveis.

O mesmo corpus passou pela entrada real `gba_swi` do runtime nativo, além do
teste isolado dos auxiliares. O controle negativo, com os corpos antigos das
rotinas, reproduziu a meia volta incorreta. Os resultados de R0–R3 ocupam
3.149.328 bytes em cada implementação e coincidiram integralmente.

Os testes são `tools/verify_bios_math.py` e
`tools/verify_bios_math_runtime.py`. Os relatórios locais ficam em
`build/native_bios_math_validation_v4` e
`build/native_bios_math_runtime_validation`. O primeiro teste aceita
`--negative-runtime` para comparar um fonte anterior preservado; esse arquivo
é opcional e não é necessário para testar as novas rotinas.

A referência executa a implementação de software de BIOS do mGBA em processo
separado. O executável nativo do teste não contém um núcleo de CPU. Não houve
comparação com uma imagem física de BIOS, nem validação de ciclos ou flags
CPSR nesta etapa. Os testes também não acrescentam alvos ao matching GBA e
não provam equivalência do jogo inteiro.
