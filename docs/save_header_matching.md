# Leitura do header de save: 0x08001BE4

Verificação em 16/10/2026, ROM USA BDVE rev. 0, SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`.

`src/save_read_status.c` recompila o intervalo **0x08001BE4..0x08001D00**:
**284/284 bytes iguais, zero diferenças**. A seção completa inclui instruções,
constantes, destinos de chamadas e alinhamento. Compilador e flags permanecem
`agbcc` GCC 2.9-arm-000512, `-O2 -mthumb-interwork`.

SHA-256 do candidato e da referência:
`d60e871402036fe996b1e3163d2643b510e9682b50e6cd244aa2735dcfa26d2c`.

## Comportamento preservado

1. Se o bit `0x100` de `gSystemFlags` estiver ativo, retorna 0.
2. Zera checksum e byte `+2` nos dois estados de save e no header; zera o buffer de oito bytes.
3. Chama `Func_080027C8` com três locais de 16 bits. O helper continua externo.
4. Solicita uma leitura de oito bytes no setor EEPROM 1, por `Func_081157C4`.
5. Se o leitor retornar erro, tenta o setor `gSaveEepromConfig->count >> 1` do banco de backup.
6. Copia a primeira halfword do buffer para os três checksums; lê a segunda halfword e
   grava seu byte baixo nos três campos `+2`.
7. Chama `Func_08003028` com os mesmos três locais e retorna 1.

O retorno 1 desse caminho ocorre mesmo se a segunda tentativa falhar. Não foi transformado
em um indicador de sucesso de leitura. Não foi atribuído um significado específico aos três
locais sem reconstruir os dois helpers que os recebem.

## Restrições de GNU C

O fonte usa três templates vazios, sem instruções assembly:

- `+r` mantém o zero do checksum independente do zero usado pelo byte de flags.
- `+r` para o byte, entrada `r` para o endereço do primeiro local e clobbers `r2,r3`
  conservam a preparação do endereço e a ordem da inicialização.
- O destino EEPROM usa uma variável vinculada a `r5` e uma restrição `+r` antes do primeiro
  laço, preservando a distribuição dos registradores nas duas tentativas.

Essas restrições influenciam a geração do compilador; não fazem pós-processamento do assembly
ou do binário. Foram declaradas em `compiler_barriers` no manifesto de produção e no relatório.
Não se afirma que esse era o fonte C histórico.

## Reprodução e estado do restante

```powershell
.\.venv\Scripts\python.exe tools\match.py --target save_read_status
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A base contém **224 funções e 33.032 bytes com matching integral**. O teste negativo do setor
muda a tentativa primária de 1 para 2 em uma cópia do fonte e exige reprovação após recompilar.
Os 19 serviços chamados diretamente pela inicialização têm matching; suas dependências
transitivas ainda incluem serviços externos.

O processador `0x0810DDCC` foi concluído em [background_queue_matching.md](background_queue_matching.md).
`0x0810EFB4` foi concluído depois, conforme [background_sprites_matching.md](background_sprites_matching.md).
O estado das candidatas e as limitações estão em
[background_processors_services.md](background_processors_services.md).
