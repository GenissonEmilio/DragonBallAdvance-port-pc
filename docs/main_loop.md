# Loop principal e funções com matching

ROM USA `BDVE`, revisão 0, SHA-1 `1338584d8cfa57402603197e65d2e2ff0184d24f`.
Análise inicial em 16/10/2026; conjunto atualizado em 20/10/2026. Os nomes são descritivos, atribuídos neste projeto.

## Resultado

Foram reconstruídas **242 funções em C/GNU C**. A etapa seguinte ao reconhecimento do loop
adicionou nove funções de inicialização e vídeo, descritas em
[initialization_graphics.md](initialization_graphics.md). A etapa de fundos e serviços está em [background_processors_services.md](background_processors_services.md).
A leitura do header de save foi concluída em [save_header_matching.md](save_header_matching.md),
e o desenho de sprites em fundos em [background_sprites_matching.md](background_sprites_matching.md).
As seções linkadas reproduzem **33.856/33.856 bytes**, incluindo instruções, literal pools e
padding de alinhamento, sem diferenças e sem máscaras. São 240 alvos com
`agbcc` GCC 2.9-arm-000512: 232 com `-O2 -mthumb-interwork` e três rotinas
com `-O1 -mthumb-interwork`: a [fila de mapas](background_queue_matching.md),
o [carregador de fundos da abertura](post_boot_loader_matching.md) e
[`Cgb_Update`](audio_update_matching.md).
`Runtime_Memset` usa agbcc `-O2` sem interworking; `Cgb_Stop`, `Audio_UnlinkChannel`, `Music_ClearModulation` e `MusicEvent_PatternEnd` acrescentam `-fprologue-bugfix`
ao perfil `-O2 -mthumb-interwork`, totalizando os 240 alvos desse compilador.
`MusicTrack_Stop` e `MusicEvent_Fine` usam o perfil alternativo GCC 3.4.6, documentado em
[music_track_stop_matching.md](music_track_stop_matching.md). O callback serial está em
[serial_irq_matching.md](serial_irq_matching.md).

A tabela abaixo conta apenas matching de C. Separadamente,
[`MusicPlayer_Update`](music_player_update_hybrid.md) acrescenta **616 bytes assembly iguais**
e uma versão C nativa validada por comportamento. A continuação de
[cópia da tabela e auxiliares](audio_helpers_matching.md) acrescentou outros 76 bytes assembly
e 80 C. A etapa de [frequências PCM/CGB](audio_frequency_matching.md) acrescentou 100 bytes C
e dois bindings. A etapa de [notas e canais](sound_update_track_hybrid.md) acrescentou 28 bytes C,
512 assembly e dois bindings. O [término de notas sustentadas](music_end_tie_hybrid.md) acrescentou 64 bytes assembly.
Os [comandos de LFO e modulação](music_modulation_commands.md) acrescentaram 12 bytes C,
40 assembly e três bindings. A etapa de [memória e comandos estendidos](music_memory_commands.md)
acrescentou 14 funções C/GNU C, 664 bytes e 14 bindings. A continuação de
[padrões e repetição](music_pattern_commands.md) acrescentou 20 bytes C, 88 assembly e quatro bindings.
A etapa de [prioridade e tempo](music_priority_tempo_commands.md) acrescentou 32 bytes assembly e dois bindings C.
A [transposição](music_key_shift_command.md) acrescentou outros 20 bytes assembly e um binding C.
A [seleção de instrumento](music_voice_command.md) acrescenta 48 bytes assembly e seu C nativo.
O [comando de volume](music_volume_command.md) acrescenta 20 bytes assembly e seu C nativo.
O [comando de pan](music_pan_command.md) acrescenta 20 bytes assembly e seu C nativo.
O [pitch bend](music_pitch_bend_command.md) acrescenta 20 bytes assembly e seu C nativo.
O [alcance do bend](music_bend_range_command.md) acrescenta 20 bytes assembly e seu C nativo.
O [atraso do LFO](music_lfo_delay_command.md) acrescenta 12 bytes assembly e seu C nativo.
O [tipo de modulação](music_mod_type_command.md) acrescenta 24 bytes assembly e seu C nativo.
A [afinação](music_tune_command.md) acrescenta 20 bytes assembly e seu C nativo.
O [PORT](music_port_command.md) acrescenta 24 bytes assembly e seu C nativo.
A [configuração de frequência e VSync-on](sound_frequency_native.md) acrescenta dois bindings;
seus 224 bytes C GBA já pertenciam ao matching.
O [modo e VSync-off](sound_mode_native.md) acrescenta dois bindings;
seus 276 bytes C GBA já pertenciam ao matching.
São 66 endereços nativos após as [APIs de músicas](song_playback_native.md)
e **265 alvos e 36.576 bytes** no conjunto,
sem atribuir os bytes assembly ao compilador C.

| Função em C | Endereço USA | Bytes comparados | Resultado |
|---|---|---:|---|
| `Game_Bootstrap` | `0x08001424` | 28 | Match |
| `Game_ResetVideoStateCallback` | `0x08001440` | 12 | Match |
| `State_IncrementWord10IfFlag22` | `0x0800144C` | 28 | Match |
| `Game_CreateCounterTask` | `0x08001468` | 104 | Match |
| `Game_ResetVideoState` | `0x080014D0` | 92 | Match |
| `Game_Entry` | `0x0800152C` | 12 | Match |
| `Runtime_MainLoop` | `0x0810C90C` | 340 | Match |
| `Input_Update` | `0x0810D2F8` | 240 | Match |
| `Runtime_Startup` | `0x0810D65C` | 20 | Match |
| `Tasks_RunFrame` | `0x0810D94C` | 212 | Match |
| `Game_Initialize` | `0x08001350` | 212 | Match |
| `Runtime_Initialize` | `0x0810C228` | 1.764 | Match |
| `Graphics_CommitDma` | `0x0810CA60` | 724 | Match |
| `Graphics_ClearOamDma` | `0x0810CD34` | 224 | Match |
| `Graphics_CommitCpu` | `0x0810CE14` | 528 | Match |
| `Graphics_ProcessVramQueue` | `0x0810D240` | 184 | Match |
| `Graphics_ClearOamCpu` | `0x0810D5C0` | 156 | Match |
| `Tasks_Initialize` | `0x0810D670` | 232 | Match |
| `Graphics_ProcessOam` | `0x08111A88` | 496 | Match |
| `Func_08114BA4` | `0x08114BA4` | 64 | Match |
| `Func_08115618` | `0x08115618` | 20 | Match |
| `Func_08113C38` | `0x08113C38` | 40 | Match |
| `Func_081156FC` | `0x081156FC` | 72 | Match |
| `Tasks_AllocateSlot` | `0x0810DBD0` | 40 | Match |
| `Func_08102BF4` | `0x08102BF4` | 32 | Match |
| `Func_0800C364` | `0x0800C364` | 12 | Match |
| `Func_080043F4` | `0x080043F4` | 16 | Match |
| `Func_080A38CC` | `0x080A38CC` | 44 | Match |
| `Func_080A30F8` | `0x080A30F8` | 64 | Match |
| `Func_0810ADAC` | `0x0810ADAC` | 12 | Match |
| `Graphics_ClearBackgrounds` | `0x0810F75C` | 612 | Match |
| `Func_0810AD34` | `0x0810AD34` | 120 | Match |
| `Func_0810B2D0` | `0x0810B2D0` | 152 | Match |
| `Func_08113CE0` | `0x08113CE0` | 244 | Match |
| `Func_08001538` | `0x08001538` | 152 | Match |
| `Func_08001D00` | `0x08001D00` | 152 | Match |
| `Func_080030A0` | `0x080030A0` | 44 | Match |
| `Func_08002AA8` | `0x08002AA8` | 120 | Match |
| `Func_080FA048` | `0x080FA048` | 304 | Match |
| `Func_08001BE4` | `0x08001BE4` | 284 | Match |
| `Graphics_DrawBackgroundSprites` | `0x0810EFB4` | 1.340 | Match |
| `Graphics_ProcessBackgroundQueue` | `0x0810DDCC` | 2.868 | Match |
| `Task_Create` | `0x0810D758` | 316 | Match |
| `Task_Destroy` | `0x0810D894` | 184 | Match |
| `Tasks_IwramAlloc` | `0x0810DA20` | 104 | Match |
| `Tasks_IwramFree` | `0x0810DA88` | 124 | Match |
| `Tasks_DestroyPriorityRange` | `0x0810DBF8` | 120 | Match |
| `Task_HeadSentinel` | `0x0810DC9C` | 4 | Match |
| `Task_TailSentinel` | `0x0810DCA0` | 4 | Match |
| `Task_UnusedSentinel` | `0x0810DCA4` | 4 | Match |
| `Heap_EwramAlloc` | `0x0811562C` | 100 | Match |
| `Heap_EwramFree` | `0x08115690` | 108 | Match |
| `Func_08114D70` | `0x08114D70` | 64 | Match |
| `Func_080010C4` | `0x080010C4` | 12 | Match |
| `Func_08000FDC` | `0x08000FDC` | 64 | Match |
| `Func_0810AEEC` | `0x0810AEEC` | 44 | Match |
| `Serial_Stop` | `0x08114138` | 80 | Match |
| `Serial_InstallHandlerAndStart` | `0x08115434` | 40 | Match |
| `Serial_Start` | `0x08114DB0` | 188 | Match |
| `MusicPlayer_Stop` | `0x0810B5D0` | 64 | Match |
| `MusicTrack_Stop` | `0x0810A98C` | 68 | Match |
| `Serial_IrqHandler` | `0x08114E6C` | 560 | Match |
| `Serial_ProcessPacket` | `0x0811509C` | 108 | Match |
| `Serial_ValidatePacket` | `0x08115108` | 60 | Match |
| `Serial_MakePacket` | `0x08115144` | 236 | Match |
| `Func_080C863C` | `0x080C863C` | 328 | Match |
| `Sequence_Prepare` | `0x080C8964` | 104 | Match |
| `Sequence_Run` | `0x080C8784` | 196 | Match |
| `Sequence_Finish` | `0x080C88F0` | 116 | Match |
| `Sequence_OnDestroy` | `0x080C88EC` | 4 | Match |
| `Sequence_StartAfterBoot` | `0x080C8898` | 72 | Match |
| `BootSequence_Initialize` | `0x080F3368` | 136 | Match |
| `BootSequence_OnDestroy` | `0x080F33F0` | 4 | Match |
| `BootSequence_Run` | `0x080F2FD0` | 252 | Match |
| `BootSequence_Finish` | `0x080F30CC` | 140 | Match |
| `BootSequence_BeginFadeOut` | `0x080F3158` | 80 | Match |
| `BootSequence_Advance` | `0x080F31A8` | 120 | Match |
| `BootSequence_LoadScreen` | `0x080F3220` | 328 | Match |
| `BootSequence_Update` | `0x080F33F4` | 112 | Match |
| `BootSequence_StartScreen` | `0x080F3464` | 68 | Match |
| `BootSequence_FadeIn` | `0x080F34A8` | 80 | Match |
| `BootSequence_BeginHold` | `0x080F34F8` | 32 | Match |
| `BootSequence_Hold` | `0x080F3518` | 48 | Match |
| `BootSequence_FadeOut` | `0x080F3548` | 52 | Match |
| `BootSequence_BeginPause` | `0x080F357C` | 48 | Match |
| `BootSequence_ClearScreen` | `0x080F35AC` | 68 | Match |
| `PostBoot_Initialize` | `0x080EFAA4` | 144 | Match |
| `PostBoot_OnDestroy` | `0x080EE654` | 136 | Match |
| `PostBoot_Run` | `0x080EE6DC` | 308 | Match |
| `PostBoot_Update` | `0x080EE810` | 220 | Match |
| `PostBoot_Finish` | `0x080EE8EC` | 164 | Match |
| `PostBoot_PrepareSprites` | `0x080EF3B4` | 148 | Match |
| `PostBoot_FreeSprites` | `0x080F054C` | 48 | Match |
| `PostBoot_Begin` | `0x080EFB34` | 92 | Match |
| `PostBoot_EnableBackgrounds` | `0x080EFB90` | 80 | Match |
| `PostBoot_DisableBackgrounds` | `0x080EFBE0` | 80 | Match |
| `PostBoot_LoadTiles` | `0x080F0434` | 116 | Match |
| `Music_StartSong` | `0x0810ADB8` | 44 | Match |
| `Vram_AllocateTiles` | `0x08113B80` | 184 | Match |
| `Vram_FreeTiles` | `0x08113C60` | 48 | Match |
| `PostBoot_CreateSkipTask` | `0x080F0898` | 116 | Match |
| `PostBoot_SkipRun` | `0x080EF9BC` | 116 | Match |
| `PostBoot_SkipFade` | `0x080EFA30` | 116 | Match |
| `PostBoot_SkipOnDestroy` | `0x080F090C` | 4 | Match |
| `PostBoot_Phase3` | `0x080EFC30` | 88 | Match |
| `PostBoot_LoadBackground` | `0x080EEDB4` | 564 | Match |
| `PostBoot_Phase4` | `0x080EFC88` | 80 | Match |
| `PostBoot_Phase5` | `0x080EFCD8` | 24 | Match |
| `PostBoot_Phase6` | `0x080EFCF0` | 96 | Match |
| `PostBoot_Phase7` | `0x080EFD50` | 96 | Match |
| `PostBoot_Phase8` | `0x080EFDB0` | 32 | Match |
| `PostBoot_Phase9` | `0x080EFDD0` | 24 | Match |
| `PostBoot_Phase10` | `0x080EFDE8` | 72 | Match |
| `PostBoot_Phase11` | `0x080EFE30` | 72 | Match |
| `PostBoot_ClearBackgroundMap` | `0x080F04A8` | 56 | Match |
| `PostBoot_Phase12` | `0x080EFE78` | 24 | Match |
| `PostBoot_Phase16` | `0x080EFF60` | 24 | Match |
| `PostBoot_Phase13` | `0x080EFE90` | 72 | Match |
| `PostBoot_Phase14` | `0x080EFED8` | 72 | Match |
| `PostBoot_Phase15` | `0x080EFF20` | 64 | Match |
| `PostBoot_Phase17` | `0x080EFF78` | 96 | Match |
| `PostBoot_Phase18` | `0x080EFFD8` | 36 | Match |
| `PostBoot_StartFade` | `0x080EE9FC` | 128 | Match |
| `PostBoot_CreateFade` | `0x080EF448` | 168 | Match |
| `PostBoot_FadeRun` | `0x080EF4F0` | 120 | Match |
| `PostBoot_FadeOnDestroy` | `0x080F057C` | 4 | Match |
| `PostBoot_Phase21` | `0x080F0040` | 56 | Match |
| `PostBoot_Phase25` | `0x080F014C` | 56 | Match |
| `PostBoot_Phase22` | `0x080F0078` | 112 | Match |
| `PostBoot_Phase23` | `0x080F00E8` | 36 | Match |
| `PostBoot_Phase24` | `0x080F010C` | 64 | Match |
| `PostBoot_LoadMap` | `0x080EEFE8` | 316 | Match |
| `PostBoot_LoadPalette` | `0x080EF124` | 188 | Match |
| `PostBoot_ApplyBackground` | `0x080EF1E0` | 80 | Match |
| `PostBoot_Phase26` | `0x080F0184` | 44 | Match |
| `PostBoot_Phase27` | `0x080F01B0` | 36 | Match |
| `PostBoot_Phase28` | `0x080F01D4` | 56 | Match |
| `PostBoot_Phase29` | `0x080F020C` | 24 | Match |
| `PostBoot_LoadSpecialBackground` | `0x080EF230` | 108 | Match |
| `PostBoot_LoadSpecialTiles` | `0x080EF29C` | 168 | Match |
| `PostBoot_LoadSpecialMap` | `0x080EF344` | 112 | Match |
| `PostBoot_LoadSpecialPalette` | `0x080F04E0` | 108 | Match |
| `PostBoot_Phase30` | `0x080EEA7C` | 148 | Match |
| `PostBoot_Phase31` | `0x080EEB10` | 156 | Match |
| `PostBoot_Phase32` | `0x080F0224` | 24 | Match |
| `PostBoot_Phase33` | `0x080F023C` | 24 | Match |
| `PostBoot_CreateCurtain` | `0x080EF568` | 232 | Match |
| `PostBoot_CurtainOnDestroy` | `0x080F0580` | 4 | Match |
| `PostBoot_CurtainWait` | `0x080F0584` | 68 | Match |
| `PostBoot_CurtainMove` | `0x080EF650` | 260 | Match |
| `PostBoot_CurtainHold` | `0x080EF754` | 88 | Match |
| `PostBoot_Phase34` | `0x080EEBAC` | 144 | Match |
| `PostBoot_CreateScroll` | `0x080EF7AC` | 268 | Match |
| `PostBoot_ScrollRun` | `0x080EF8B8` | 152 | Match |
| `PostBoot_ScrollOnDestroy` | `0x080F05C8` | 4 | Match |
| `PostBoot_Phase35` | `0x080F0254` | 40 | Match |
| `PostBoot_Phase36` | `0x080F027C` | 88 | Match |
| `PostBoot_Phase37` | `0x080F02D4` | 24 | Match |
| `PostBoot_Phase38` | `0x080F02EC` | 24 | Match |
| `PostBoot_Phase39` | `0x080EEC3C` | 144 | Match |
| `PostBoot_Phase40` | `0x080F0304` | 40 | Match |
| `PostBoot_Phase41` | `0x080EECCC` | 116 | Match |
| `PostBoot_Phase47` | `0x080EED40` | 116 | Match |
| `PostBoot_Phase42` | `0x080F032C` | 60 | Match |
| `PostBoot_Phase43` | `0x080F0368` | 40 | Match |
| `PostBoot_Phase44` | `0x080F0390` | 40 | Match |
| `PostBoot_Phase45` | `0x080F03B8` | 68 | Match |
| `PostBoot_Phase46` | `0x080F03FC` | 28 | Match |
| `PostBoot_Phase48` | `0x080F0418` | 28 | Match |
| `PostBoot_CreateRing` | `0x080F05CC` | 148 | Match |
| `PostBoot_RingOnDestroy` | `0x080F0660` | 4 | Match |
| `PostBoot_RingRun` | `0x080F0664` | 76 | Match |
| `PostBoot_RingBegin` | `0x080F06B0` | 12 | Match |
| `PostBoot_RingInitContract` | `0x080F06BC` | 68 | Match |
| `PostBoot_RingContract` | `0x080F0700` | 56 | Match |
| `PostBoot_RingSpin` | `0x080F07AC` | 56 | Match |
| `PostBoot_RingHold` | `0x080F0738` | 48 | Match |
| `PostBoot_RingInitSpin` | `0x080F0768` | 68 | Match |
| `PostBoot_RingRelease` | `0x080F07E4` | 76 | Match |
| `PostBoot_RingTail` | `0x080F0830` | 24 | Match |
| `PostBoot_RingStep` | `0x080F0848` | 44 | Match |
| `PostBoot_RingDraw` | `0x080F0874` | 36 | Match |
| `PostBoot_PositionRing` | `0x080EF950` | 108 | Match |
| `PostBoot_Phase19` | `0x080EFFFC` | 68 | Match |
| `PostBoot_CopyTileChunk` | `0x080EE990` | 108 | Match |
| `Func_0800C0C8` | `0x0800C0C8` | 264 | Match |
| `ScreenFade_Commit` | `0x0800C230` | 108 | Match |
| `ScreenFade_Run` | `0x0800C29C` | 200 | Match |
| `ScreenFade_OnDestroy` | `0x0800C38C` | 24 | Match |
| `Graphics_DrawSprite` | `0x08110CA0` | 1188 | Match |
| `Graphics_AllocateOam` | `0x081119F0` | 152 | Match |
| `Graphics_LoadBgPalette` | `0x08114668` | 168 | Match |
| `Runtime_Memset` | `0x08118508` | 84 | Match |
| `Sprite_UpdateAnimation` | `0x0810FD70` | 244 | Match |
| `SpriteCommand_Tiles` | `0x0810FFB8` | 144 | Match |
| `SpriteCommand_Palette` | `0x08110048` | 148 | Match |
| `SpriteCommand_JumpBack` | `0x08111C78` | 12 | Match |
| `SpriteCommand_End` | `0x08111C84` | 16 | Match |
| `SpriteCommand_Sound` | `0x08111C94` | 20 | Match |
| `SpriteCommand_Hitbox` | `0x081100DC` | 188 | Match |
| `SpriteCommand_Translate` | `0x08111CA8` | 28 | Match |
| `SpriteCommand_Skip` | `0x08111CC4` | 12 | Match |
| `SpriteCommand_Switch` | `0x08111CD0` | 24 | Match |
| `SpriteCommand_Reserved9` | `0x08111CE8` | 8 | Match |
| `SpriteCommand_Priority` | `0x08111CF0` | 28 | Match |
| `SpriteCommand_Order` | `0x08111D0C` | 16 | Match |
| `Graphics_LoadObjPalette` | `0x081145C0` | 168 | Match |
| `MusicPlayer_Start` | `0x0810B4EC` | 228 | Match |
| `MusicPlayer_Open` | `0x0810B474` | 120 | Match |
| `MusicPlayer_Clear` | `0x0810B120` | 20 | Match |
| `Sound_VSyncOff` | `0x0810B3BC` | 124 | Match |
| `Sound_VSyncOn` | `0x0810B438` | 60 | Match |
| `Sound_SetFrequency` | `0x0810B22C` | 164 | Match |
| `Sound_Initialize` | `0x0810B134` | 248 | Match |
| `Sound_Extend` | `0x0810AFF0` | 280 | Match |
| `Sound_Dummy` | `0x0810C224` | 4 | Match |
| `Cgb_Stop` | `0x0810B834` | 80 | Match |
| `Cgb_CalculateFrequency` | `0x0810B78C` | 168 | Match |
| `Cgb_UpdateVolume` | `0x0810B884` | 104 | Match |
| `Cgb_Update` | `0x0810B8EC` | 1.100 | Match |
| `Music_FadeOutBody` | `0x0810B610` | 200 | Match |
| `MusicTrack_UpdateVolumePitch` | `0x0810B6D8` | 180 | Match |
| `Audio_UnlinkChannel` | `0x0810A4C4` | 32 | Match |
| `MusicEvent_Fine` | `0x0810A4E4` | 48 | Match |
| `Music_CalculateFrequency` | `0x0810AC90` | 100 | Match |
| `Music_ClearModulation` | `0x0810AC40` | 28 | Match |
| `Music_ReadCommandByte` | `0x0810AC5C` | 12 | Match |
| `MusicEvent_MemoryAccess` | `0x0810BFAC` | 344 | Match |
| `MusicEvent_Extended` | `0x0810C104` | 32 | Match |
| `MusicEvent_ExtendedEnd` | `0x0810C124` | 20 | Match |
| `MusicEvent_Wave` | `0x0810C138` | 72 | Match |
| `MusicEvent_Type` | `0x0810C180` | 20 | Match |
| `MusicEvent_Attack` | `0x0810C194` | 20 | Match |
| `MusicEvent_Decay` | `0x0810C1A8` | 20 | Match |
| `MusicEvent_Sustain` | `0x0810C1BC` | 20 | Match |
| `MusicEvent_Release` | `0x0810C1D0` | 20 | Match |
| `MusicEvent_EchoVolume` | `0x0810C1E4` | 12 | Match |
| `MusicEvent_EchoLength` | `0x0810C1F0` | 12 | Match |
| `MusicEvent_Length` | `0x0810C1FC` | 20 | Match |
| `MusicEvent_Sweep` | `0x0810C210` | 20 | Match |
| `MusicEvent_Goto` | `0x0810A554` | 32 | Match |
| `MusicEvent_PatternEnd` | `0x0810A590` | 20 | Match |

O mapa adicional está em `config/functions.usa.json`; o primeiro alvo permanece em
`config/matching.json`. `config/symbols.usa.json` registra os endereços externos usados no
link, vinculados ao mesmo hash. Um símbolo externo nesse mapa não significa função reconstruída.

## Caminho desde o reset

```text
0x08000000  branch ARM
  -> 0x080000C0  stacks e entrada Thumb
     -> Runtime_Startup (0x0810D65C)
        1. Runtime_Initialize (0x0810C228; matching completo)
        2. Game_Entry (0x0800152C)
           -> Game_Bootstrap (0x08001424)
              1. Game_ResetVideoState (0x080014D0)
              2. Game_Initialize (0x08001350; matching completo)
              3. gDbaaGameState.byte08 = 2
              4. Game_CreateCounterTask (0x08001468)
        3. Runtime_MainLoop (0x0810C90C; permanente)
```

`Game_Entry` retorna depois de inicializar o jogo. A repetição permanente está em
`Runtime_MainLoop`, cujo C completo está em `src/runtime_main.c`.
O cabeçalho da repetição fica em `0x0810C910`; os branches em `0x0810CA46` e
`0x0810CA54` voltam para esse endereço. Não há caminho de retorno normal nessa função.

O intervalo comparado é `0x0810C90C..0x0810CA60`, com fim exclusivo: 272 bytes de
instruções, 60 de literais e 8 de alinhamento interno. A igualdade abrange também os destinos
das chamadas, os acessos às globais, as condições e os branches de retorno ao início.

## O que ocorre em cada passagem

1. Zera `gFrameBeginByte`. O bit `0x40000` de `gSystemFlags` habilita uma chamada auxiliar.
2. Se `gFrameMode == 0xFF`, chama `Input_Update` e processa caminhos adicionais selecionados
   por `gInputMode` e flags. Executa `Tasks_RunFrame` se o bit 2 de `gVideoWords[4]` estiver
   limpo; caso contrário, escreve zero em `gFrameMode`.
3. Salva `gSystemFlags` em `gPreviousSystemFlags` e chama a BIOS para esperar VBlank.
4. Zera `gAfterVBlankByte`. O bit `0x4000` escolhe entre os caminhos externos
   `Graphics_CommitCpu`/`Graphics_ClearOamCpu` e `Graphics_CommitDma`/`Graphics_ClearOamDma`.
   O bit `0x400` suprime a segunda chamada de cada par.
5. Copia o estado lógico do bit `0x400` para o bit `0x800`. Se `0x4000` estiver limpo,
   chama também `0x0810ADAC`.
6. Espera o bit 0 de `REG_DISPSTAT` ficar limpo e volta ao início.

A chamada em `0x0810C9B2` leva a `0x08115ACC`, cujo wrapper contém `svc #5` em Thumb.
Esse serviço é `VBlankIntrWait`, conforme o
[header da BIOS no libgba](https://github.com/devkitPro/libgba/blob/master/include/gba_systemcalls.h).
O polling final lê `0x04000004`; o bit 0 corresponde ao estado de VBlank, conforme as
[definições de vídeo do libgba](https://github.com/devkitPro/libgba/blob/master/include/gba_video.h).
Portanto, o código sincroniza a passagem pelo loop com VBlank; ele não é apenas um loop
genérico inferido de um branch para trás.

Os quatro corpos posteriores ao VBlank agora têm matching em C, incluindo transferências de
paletas, registradores de vídeo, OAM e callbacks. `gFrameMode` conserva o nome provisório,
mas sua utilização como índice de continuação da tabela gráfica foi estabelecida. Detalhes
das flags e das funções auxiliares estão em [initialization_graphics.md](initialization_graphics.md).

## Como a lógica é despachada

`Tasks_RunFrame`, em `src/tasks_run.c`, percorre tarefas por offsets de 16 bits relativos
à base da IWRAM `0x03000000`; a própria base é a sentinela final. O callback está em `+8`
da estrutura e as flags em `+0x12`. O próximo elemento é salvo antes da chamada indireta.

- Com `(gSystemFlags & 0x800) == 0`, executa tarefas cujo bit 0 das flags esteja limpo.
- Com esse bit global ativo, executa apenas tarefas para as quais `(flags & 5) == 4`.
- Entre tarefas, um byte auxiliar pode solicitar a chamada de `0x0810ADAC`.
- Ao terminar, zera os ponteiros `gCurrentTask` e `gNextTask`.

O compilador gera uma chamada ao helper Thumb `_call_via_r0`, em `0x08116A1C`, para invocar
o ponteiro. O helper original permanece externo; o C não contém inline assembly.

`Game_CreateCounterTask` registra `State_IncrementWord10IfFlag22` como callback e
`Game_ResetVideoStateCallback` como callback adicional na criação. Assim, a primeira função
reconstruída está conectada ao despacho do loop. Seu efeito conhecido continua sendo apenas
incrementar `word10` quando `flag22` está ativa; não foi provado que esse campo seja tempo de jogo.
`Task_Create` foi reconstruída em C com 316 bytes iguais: o tamanho é em bytes, a prioridade
ordena a lista de forma estável e o destrutor recebe o ponteiro da tarefa. Detalhes dos heaps
e da destruição durante callbacks estão em [tasks_memory_matching.md](tasks_memory_matching.md).

## Controles

`Input_Update`, em `src/input_update.c`, lê as dez teclas pelo registrador ativo em zero
`KEYINPUT`, mantém máscaras de teclas seguradas, recém pressionadas e soltas, e atualiza
contadores de repetição por tecla. Há dois modos auxiliares selecionados por
`gInputConfig[8]`, com chamadas a `0x0811456C` e `0x0811453C`; suas finalidades ainda não
estão confirmadas. Os 240 bytes incluem os acessos a esses modos e a lógica de repetição.

## Reproduzir e conferir

Na raiz de `DBAdvancedAdventure`, após preparar as ferramentas conforme o README:

```powershell
.\.venv\Scripts\python.exe tools\match.py --all
.\.venv\Scripts\python.exe tools\match.py --target runtime_main
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O primeiro comando recompila os 242 fontes separadamente e gera `build/matching/summary.json`.
Cada subpasta contém o C pré-processado, assembly original do compilador, ELF linkado,
binário candidato, referência extraída, desmontagem, comandos e hashes. A comparação usa a
seção `.text` inteira; não corta bytes excedentes nem elimina diferenças de relocations.

Os testes recompilam todos os alvos, verificam os bytes contra as regiões da ROM e incluem
controles negativos: incremento alterado, destino de chamada alterado, ROM errada e rejeição
de relatórios antigos quando uma nova execução falha. Detalhes do toolchain e do padding em
[compiler_findings.md](compiler_findings.md).

Última suíte geral (instrumento): **290 testes aprovados**, incluindo a recompilação e comparação integral dos
242 alvos. Os testes que dependem da ROM e do toolchain só são executados quando esses
arquivos estão disponíveis; nesta execução nenhum teste foi pulado.

Esta validação é de código compilado e análise estática de fluxo. Ainda não houve boot completo
do conjunto reconstruído, teste em debugger por frame nem implementação do port de PC.
As funções são linkadas individualmente com referências para os endereços originais; não
constituem uma ROM inteira reconstruída.

`Task_Create`, seus dois alocadores e a destruição por faixa usada na inicialização têm matching.
Os serviços de reset serial, buffers e parada de players agora têm matching; veja
[reset_services_matching.md](reset_services_matching.md). A parada de trilha `0x0810A98C` e o callback serial
`0x08114E6C` também têm matching, assim como os três serviços de
[pacotes seriais](serial_packets_matching.md). `0x080C863C` e onze dependências
agora têm matching em [sequences_initialization_matching.md](sequences_initialization_matching.md).
O callback `0x080F2FD0` e suas doze dependências também têm matching em
[apresentação inicial](boot_presentation_matching.md). A tabela da sequência seguinte,
ID `0x4D`, aponta para `0x080EFAA4`, agora reconstruído com dezoito dependências
em [inicialização após a apresentação](post_boot_initialization_matching.md).
O [carregador `0x080EEDB4` e a fase `0x080EFC88`](post_boot_loader_matching.md)
agora têm matching. A [continuação de fases, fade e transferência de tiles](post_boot_phases_matching.md)
acrescentou 21 funções e 1.456 bytes a partir de `0x080EFCD8`.
A etapa do [callback `0x080F0040` e fundo especial](post_boot_phase21_matching.md)
concluiu outras dezesseis funções e 1.564 bytes, incluindo o caminho `0x080EF230`.
A etapa do [callback `0x080EEA7C`, sprites e scroll](post_boot_phase30_matching.md)
concluiu outras dezesseis funções e 1.724 bytes.
A etapa do [callback `0x080F02EC` e encerramento](post_boot_phase38_matching.md)
concluiu outras 25 funções e 1.528 bytes. Agora todo o bloco local
`0x080EE654..0x080F0910` tem matching: 96 funções, 8.892 bytes contínuos.
A etapa de [desenho de sprites e serviços](graphics_draw_sprite_matching.md) concluiu
`0x08110CA0`, seu alocador OAM, `0x08114668` e `Runtime_Memset`: mais quatro funções
e 1.592 bytes. A etapa de [animação de sprites](sprite_animation_matching.md) concluiu `0x0810FD70`,
seus doze comandos e a paleta OBJ: mais 14 funções e 1.056 bytes. A etapa de [início de músicas e serviços de áudio](music_player_start_matching.md) concluiu
`MusicPlayer_Start` e cinco dependências: mais seis funções e 716 bytes.
A etapa de [inicialização de som e serviços CGB](sound_initialization_matching.md) concluiu
`Sound_Initialize`, `Sound_Extend` e quatro serviços: mais seis funções e 884 bytes.
A continuação de [atualização CGB e auxiliares de música](audio_update_matching.md) concluiu
`Cgb_Update`, `Music_FadeOutBody` e `MusicTrack_UpdateVolumePitch`: mais três funções e
1.480 bytes. A continuação concluiu [`MusicPlayer_Update`](music_player_update_hybrid.md)
com assembly GBA separado e C nativo: 616 bytes iguais e 1.128 cenários de comparação funcional.
O candidato ARM C antigo não ganhou matching. A continuação concluiu a
[cópia da tabela e os auxiliares](audio_helpers_matching.md); as etapas seguintes ligaram
os handlers de eventos da tabela. Mixer e dispositivos continuam pendentes. A etapa de [frequências PCM/CGB](audio_frequency_matching.md)
acrescentou `Music_CalculateFrequency` (100 bytes C) e integrou ambos os cálculos ao port.
A etapa de [notas e seleção de canais](sound_update_track_hybrid.md) acrescentou 28 bytes C,
512 assembly e o processador de notas em C nativo. Os quatro processadores gráficos têm matching. O mapa de tarefas permite seguir os callbacks de jogador, inimigos e cenas.
Assets, áudio e saves também continuam pendentes para o port.

A etapa de [padrões, retorno e repetição](music_pattern_commands.md) acrescentou 20 bytes C com matching,
88 bytes assembly e quatro serviços C nativos. O corpus próprio passou em 4.056 cenários.

A [inicialização e extensão](sound_initialization_native.md) e o [CGB nativo](cgb_native.md)
ligaram seus serviços. O [mixer PCM](pcm_mixer_native.md) acrescentou 1.064 bytes
assembly exatos e C nativo: são 242 alvos C e 23 assembly, 36.576 bytes ao todo.
Passaram 87 testes direcionados e os 24 corpora de áudio. Há 470 testes
descobertos; o registro de 290 acima é a última suíte geral.
São 59 endereços resolvidos, incluindo a entrada do player como callback do mixer.
Saída de som, dispositivos, backend e integração do jogo continuam pendentes.

A [inicialização de alto nível, Open e wrapper](audio_startup_native.md) ligaram
mais três entradas ao C nativo: são 62 endereços resolvidos. Seus 252 bytes C GBA
foram revalidados e já pertenciam ao total. Passaram 1.288 cenários, 1.392 execuções,
96 atualizações pelo wrapper, 108 testes direcionados e os 25 corpora de áudio.
Há 491 testes descobertos; a última suíte geral permanece a de 290 testes.
Restam APIs de músicas e dados, dispositivos e integração do jogo.
