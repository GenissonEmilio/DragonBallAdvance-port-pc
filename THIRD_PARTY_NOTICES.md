# Dependências

## gbarecomp

Projeto: [sp00nznet/gbarecomp](https://github.com/sp00nznet/gbarecomp).
Revisão: `ac1176f467cbb708f58785e65f36b4f091a8ab20`. Licença MIT,
cópia em `port/third_party/gbarecomp-MIT.txt`.

Os scripts obtêm os fontes dessa revisão e aplicam as modificações descritas
em `tools/patches/gbarecomp-native.patch`. A tradução do código da ROM é feita
localmente; o código gerado fica fora dos arquivos distribuídos.

## mGBA

Projeto: [mgba-emu/mgba](https://github.com/mgba-emu/mgba).
Revisão: `fd9dc5c2cbf234365068855851107e762fc6211b`. Licença MPL-2.0,
cópia em `port/third_party/mgba-MPL-2.0.txt`.

O executável nativo usa os fontes originais de síntese PSG (`src/gb/audio.c`),
temporização, sincronização e buffers. Não compila os núcleos de CPU de mGBA.
A configuração própria está em `port/third_party/mgba/flags.h`; o adaptador
está em `port/audio/psg_mgba.c`. Os fontes correspondentes estão disponíveis
na revisão indicada e são obtidos por `tools/setup_native.ps1`. O mGBA completo
é usado separadamente como referência de testes, fora do executável do jogo.

`port/include/bios_math.h` adapta o polinômio inteiro de `ArcTan` e as regras
de quadrantes de `ArcTan2` de `src/gba/bios.c`, na mesma revisão, sob MPL-2.0.
Esse arquivo conserva os avisos e usa multiplicações com wrap explícito.

## Política de sessões de diagnóstico de zelda-tmc-3ds

`port/windows/preview/Sessoes.ps1` adapta a alocação de sessões de
`src/port/port_dump_state.c` de
[EstebanPdN/zelda-tmc-3ds](https://github.com/EstebanPdN/zelda-tmc-3ds), revisão
`2f248e06ff1e320da8e2d97ef2fe0202a2071fff`. Copyright (C) 2026 Project Picori
contributors; manutenção 3DS por Esteban PDN. Distribuído sob GPL-3.0-or-later,
com o texto em `port/third_party/zelda-GPL-3.0.txt`. A adaptação para PowerShell
e Windows acompanha o pacote como fonte editável. Esse script executa fora do
binário do jogo. Não foram incorporados a engine, o renderer, os recursos ou
os checkpoints de Zelda. Veja a [análise da base](docs/zelda_base_assessment.md).

## Ferramentas de compilação e análise

O setup obtém w64devkit 2.10.1 do projeto
[skeeto/w64devkit](https://github.com/skeeto/w64devkit), verificando o SHA-256
fixado em `config/matching.json`. A distribuição original inclui os avisos de
seus componentes. O pacote não é incluído neste repositório.
Capstone 5.0.9 é instalado como dependência de análise via `requirements.txt`.
O caminho de matching GBA usa ferramentas adicionais e revisões documentadas
nos perfis de `config/matching.json` e nas páginas de `docs/`.

Os nomes do jogo e seus recursos pertencem aos respectivos titulares. Este
repositório não inclui ROM, BIOS, músicas, gráficos ou outros recursos extraídos.
O pacote Windows contém um executável de recompilação estática que exige a
ROM local, além dos avisos de licença e fontes correspondentes do subconjunto
mGBA usado na síntese. Não distribui o emulador mGBA ou seus núcleos de CPU.
