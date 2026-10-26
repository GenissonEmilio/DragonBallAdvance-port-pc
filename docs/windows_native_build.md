# Compilar a prévia nativa no Windows

O port completo ainda está em desenvolvimento. Este caminho gera os fontes
locais a partir da ROM e compila as funções traduzidas, os serviços C
reconstruídos, vídeo Win32, entrada, EEPROM e áudio WASAPI. Nenhum objeto das
etapas experimentais `build/next` é usado. O executável não inclui os núcleos de
CPU ARM/Thumb ou SM83. A recompilação estática não conta como matching GBA.

Requisitos: Windows x64, Git, PowerShell e Python 3.10 ou superior. Coloque uma
ROM USA BDVE revisão 0 em `baserom.gba`, com SHA-1
`1338584d8cfa57402603197e65d2e2ff0184d24f`. Os scripts não baixam ROM ou BIOS.

```powershell
.\tools\setup_native.ps1
.\tools\build_native.ps1
.\build\windows_native\bin\dbaa_game.exe .\baserom.gba
```

Para outro caminho da ROM: `tools/build_native.ps1 -Rom 'C:\jogos\jogo.gba'`.
A primeira geração e compilação podem demorar; os logs e manifestos ficam em
`build/windows_native_generation` e `build/windows_native`. A instalação usa
ferramentas dentro do projeto, sem administrador ou alteração permanente do
PATH. Uma instalação existente com outra revisão é preservada e gera erro.

Os controles são setas, Z (A), X (B), Enter (Start), Backspace (Select), A (L)
e S (R). O save `.eep` fica ao lado da ROM. Para uma execução curta sem janela:

```powershell
.\build\windows_native\bin\dbaa_game.exe .\baserom.gba --headless --frames 300
```

Dependências fixadas: gbarecomp MIT em
`ac1176f467cbb708f58785e65f36b4f091a8ab20`, com o patch versionado em
`tools/patches/gbarecomp-native.patch`; mGBA MPL-2.0 em
`fd9dc5c2cbf234365068855851107e762fc6211b`, somente síntese PSG, relógio e
buffers; w64devkit 2.10.1 e Capstone 5.0.9. Os avisos de licença estão em
`port/third_party`. O subconjunto PSG usa configuração própria sem macros de
núcleo de CPU; não depende de um build CMake anterior.

A ROM, recursos extraídos, traduções derivadas da ROM, bibliotecas das
ferramentas e saves ficam locais. O repositório distribui os fontes do projeto,
patches e instruções para gerar o restante a partir da ROM do usuário.
 
A instalação e os dois comandos públicos foram exercitados em uma cópia
isolada de 527 fontes, com Git e Python preparados novamente e 108 objetos
compilados do zero. O arquivo de download do compilador, com SHA-256 conferido,
foi reaproveitado como cache. Nenhuma ferramenta extraída ou objeto anterior
foi copiado. O executável resultante reproduziu os mesmos bytes de memória,
imagem, PCM e save do build principal em 20.000 quadros.
