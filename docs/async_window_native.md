# Janela Windows e produção de áudio

O build reproduzível usa `port/windows/game_window_async.c`. A janela, a fila
de mensagens e o GDI pertencem a uma thread de apresentação. A thread do jogo
publica a imagem mais recente com uma tentativa de obter o lock de cópia;
ela não espera pela pintura. O lock nunca permanece retido durante chamadas
ao desktop. O estado das teclas e o pedido de fechamento usam operações
atômicas. A pintura pode apresentar a imagem mais recente após um atraso;
o fluxo de PCM não é descartado, duplicado ou reamostrado.

A separação corrige um atraso observado na implementação síncrona: uma chamada
de apresentação levou 175 ms, enquanto a thread do jogo também produzia áudio.
O build inicial a partir dos fontes teve 11 esvaziamentos de endpoint em 5.000
quadros. Uma execução de diagnóstico registrou 53. Ambos os resultados foram
preservados, mesmo com PCM, imagem e save iguais à execução offline.

Com a apresentação separada passaram sessões de **5.000 e 20.000 quadros**,
zero esvaziamentos e erros, e os mesmos bytes PCM/imagem/save/estado resumido
da execução offline. Na sessão longa foram entregues **16.072.761 pares
estéreo**, FNV-1a64 `199d7f590635ad76`, ao WASAPI. Os relatórios ficam em
`build/native_async_game_device_validation/report.json` e
`build/native_async_game_long_validation/report.json`.

O teste `tools/verify_async_window.py` exercita dez teclas, repetição, perda de
foco, fechamento/reabertura e 120 quadros temporizados. Um hook instalado
somente na própria janela de teste bloqueia sua thread: o produtor publica
100 imagens enquanto ela permanece bloqueada. Essa sonda prova a independência
entre as threads; não simula uma falha real de GPU.

```powershell
.\.venv\Scripts\python.exe tools\verify_async_window.py
.\tools\build_native.ps1
```

Os 108 objetos do primeiro build foram compilados a partir dos fontes; em
20.000 quadros, todos os 396.288 bytes do dump de memória, imagem, PCM e save
coincidiram com a prévia auditada. O backend assíncrono substitui somente o
objeto da janela. O comando público de build também foi executado e seus 108
objetos coincidem com os da variante testada. Os seis objetos PSG coincidem
com os anteriormente validados, usando configuração própria sem núcleos de CPU.

Essas comparações não demonstram paridade do jogo inteiro com o hardware GBA,
nem fidelidade analógica. Permanecem pendentes a campanha completa, saves de
progresso, músicas CGB no mix final e casos como suspensão/troca de dispositivo.
