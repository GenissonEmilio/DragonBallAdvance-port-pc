# Dragon Ball: Advanced Adventure — port nativo para Windows

Port em desenvolvimento a partir da ROM de GBA USA (`BDVE`, revisão 0).
Existe uma prévia Windows x64 que inicia a campanha, executa a primeira fase,
usa vídeo e entrada Win32, grava EEPROM e reproduz o áudio original por WASAPI.
O jogo completo ainda não está validado. Veja o [estado do port](docs/port_status.md).

## Baixar e jogar

A [pré-release Windows x64](https://github.com/GenissonEmilio/DragonBallAdvance-port-pc/releases)
inclui o executável pronto: extraia o ZIP e abra `Jogar.cmd`. Selecione sua ROM
USA `BDVE` revisão 0 quando solicitado, ou coloque `baserom.gba` na pasta.
Não é necessário instalar Python, Git ou um emulador para jogar esse pacote.
ROM e BIOS não acompanham a release. O save `.eep` fica ao lado da ROM;
use uma cópia em uma pasta de testes para separar seus saves existentes.

É uma base para testes durante o desenvolvimento. Campanha completa,
salvamento/recarga de progresso, chefes e modos ainda precisam de validação.
Ao encontrar um problema, [abra uma issue](https://github.com/GenissonEmilio/DragonBallAdvance-port-pc/issues)
com a fase, os passos para reproduzir e os arquivos da sessão em `logs/`.
Veja as [instruções e limitações da prévia](docs/windows_preview.md).

O executável combina serviços reconstruídos manualmente em C com recompilação
estática das demais funções da ROM. Não inclui um interpretador ARM/Thumb.
Chamadas sem implementação interrompem a execução com diagnóstico.
As funções traduzidas são geradas localmente; não contam como matching GBA.

## Compilar e executar

Requisitos: Windows x64, Python 3.10+, Git e PowerShell. Coloque sua ROM em
`baserom.gba`, com SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.

```powershell
.\tools\setup_native.ps1
.\tools\build_native.ps1
.\build\windows_native\bin\dbaa_game.exe .\baserom.gba
```

A instalação é local, sem administrador ou alteração permanente do PATH.
O [guia de compilação](docs/windows_native_build.md) descreve as dependências,
logs e o uso de outro caminho da ROM. A geração e compilação iniciais demoram.

Controles: setas, Z (A), X (B), Enter (Start), Backspace (Select), A (L), S (R).
O arquivo `.eep` de salvamento fica ao lado da ROM.

A continuação usa o [port de Minish Cap para 3DS como referência de base](docs/zelda_base_assessment.md).
A política de sessões de diagnóstico já foi adaptada para o iniciador Windows;
os componentes específicos do jogo e do 3DS são avaliados separadamente.

## Validação

- **265 rotinas GBA, 36.576 bytes exatos:** 242 alvos C/GNU C (33.856 bytes) e
  23 alvos assembly (2.720 bytes), mantidos separadamente.
- **Áudio:** 66 serviços C nativos; a música de ID 1 foi comparada com a ROM
  durante 1.800 quadros, incluindo início, parada e reinício.
- **Saída Windows em builds anteriores:** sessões de 5.000 e 20.000 quadros com janela, sem
  esvaziamentos do endpoint; PCM entregue ao WASAPI igual ao gerado offline.
- **Build a partir dos fontes (verificação anterior):** os 108 objetos foram compilados novamente,
  sem reutilizar objetos experimentais. Em 20.000 quadros, memória, imagem,
  PCM, save e diagnósticos coincidiram com a prévia anteriormente auditada.
- **EEPROM:** formato real de 512 bytes, inicialização igual à ROM e importada
  por ela; gravação atômica e regressões das capacidades de 4/64 Kbit.
- **Vídeo e gameplay:** após corrigir a fase inicial do vídeo, o pedido de IRQ
  e a aplicação dos eventos de entrada, coincidem 356 observações de posição/
  câmera/estado e 600 observações de RNG com a ROM, nos mesmos quadros. No
  quadro 6.000, os 115.200 bytes RGB, a paleta, a VRAM e a OAM são exatos.
  Restam diferenças em RAM e I/O; isso não prova equivalência do jogo inteiro.
- **Prévia atual:** 14 casos de vídeo, entrada e EEPROM aprovados; duas sessões
  de 5.000 quadros tiveram PCM enviado igual ao offline, mas registraram 27 e 3
  esvaziamentos do endpoint. A continuidade do áudio ainda falha. Consulte o
  [manifesto desta versão](docs/validation/v0.1.0-preview.json).

Esses resultados não provam equivalência do jogo inteiro. Ainda faltam paridade
geral de vídeo/temporização/PCM, progresso e recarga de campanha, todas as fases,
chefes e modos, além dos casos de troca de dispositivo e suspensão.
O agregado histórico geral tem 514 testes aprovados; os novos testes foram
executados por grupos. Não se afirma uma nova execução geral dos 541 descobertos.

## Organização

- `src/`, `include/`, `asm/`, `config/`: reconstruções e perfis para matching GBA.
- `port/`: serviços C do host e backends Windows.
- `tools/`: análise, geração, compilação e validação.
- `tests/`: regressões e testes de comportamento.
- `docs/`: método, rotinas reconstruídas, evidências e limites das comparações.

O [subsistema de áudio isolado](docs/windows_audio_output.md) e os
[testes da música original](docs/song_playback_native.md) podem ser executados
separadamente. O [guia de integração](docs/native_game_integration.md) explica
as etapas experimentais anteriores. O projeto de Tenkaichi 3 serviu como
referência de método; sua implementação de PS2 não é reutilizada como runtime.

ROM, BIOS, recursos extraídos, fontes traduzidos da ROM, saves e toolchains
não são distribuídos. A pré-release distribui o executável nativo, que carrega
os dados da ROM local. As dependências e seus avisos estão em
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Os scripts não baixam ROM/BIOS.
