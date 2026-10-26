"""Mixed-ISA GBA bytes and semantic native PCM mixing with scalar checks."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class PcmMixerNativeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)

    @unittest.skipUnless(READY,'requires ROM and GBA tools')
    def test_pcm_mixer_complete_mixed_isa_assembly_image_matches(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match_assembly.py','--target','sound_main','--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr);report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal']);self.assertEqual(report['different_bytes'],0)
            self.assertEqual(report['candidate_size'],1064);self.assertFalse(report['counts_as_c'])
            self.assertFalse(report['assembly_postprocessing']);self.assertFalse(report['remaining_relocations'])
            self.assertEqual((Path(temp)/'sound_main.bin').read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10A084:0x10A4AC])

    @unittest.skipUnless(READY,'requires ROM and GBA tools')
    def test_pcm_mixer_assembly_dma_stride_mutation_fails_byte_gate(self):
        source=(ROOT/'asm/sound_main.s').read_text();old='.equ PCM_DMA_BUF_SIZE,0x630';self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.s';changed.write_text(source.replace(old,'.equ PCM_DMA_BUF_SIZE,0x62C'));out=Path(temp)/'out'
            r=self.run_tool('match_assembly.py','--target','sound_main','--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY and(ROOT/'tools/local/gcc346-build/gcc/cc1.exe').is_file(),'requires GCC346 and ROM')
    def test_pcm_mixer_plain_c_probe_is_explicitly_nonmatching(self):
        config=json.loads((ROOT/'config/functions.usa.json').read_text())
        self.assertNotIn('sound_main',[t['id']for t in config['functions']])
        config['functions']=[dict(id='sound_main_c',name='Func_0810A084',address='0x0810A084',size=1064,
            source='reference/sound_main.c',compiler_profile='gcc346',
            compiler_flags=['-O2','-mthumb','-mcpu=arm7tdmi','-mthumb-interwork','-std=gnu99'])]
        with tempfile.TemporaryDirectory()as temp:
            manifest=Path(temp)/'candidate.json';manifest.write_text(json.dumps(config));out=Path(temp)/'out'
            r=self.run_tool('match.py','--target','sound_main_c','--function-map',manifest,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr);report=json.loads((out/'report.json').read_text())
            self.assertFalse(report['equal']);self.assertGreater(report['different_bytes'],0)
            self.assertFalse(report['assembly_postprocessing']);self.assertFalse(report['remaining_relocations'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_ram_pcm_bus_callbacks_and_scalar_reference_match(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_pcm_mixer.py','--cases',0,'--sample-step',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr);report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],170);self.assertEqual(report['executions'],722)
            self.assertEqual(report['lifecycle_sequences'],24);self.assertEqual(report['lifecycle_updates'],576)
            self.assertGreater(report['scalar_pcm_cases'],0);self.assertEqual(report['mixer_instruction_count'],367)
            self.assertGreaterEqual(report['mixer_instructions_covered'],350)
            self.assertEqual(report['copied_ram_bytes'],1024);self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','raw_pcm_bytes_equal','ordered_reads_and_writes_equal','relocated_code_executed']:self.assertTrue(report[key],key)
            for key in ['native_mixer_fallback_to_arm','byte_matching','full_game_boot','hardware_register_side_effects_validated',
                'real_time_validated','audible_output_validated']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new,source='port/include/pcm_mixer_impl.h',option='--mixer-source'):
        original=(ROOT/source).read_text();self.assertEqual(original.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/Path(source).name;changed.write_text(original.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_pcm_mixer.py','--cases',0,'--sample-step',16,option,changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr);self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_lock_guard_mutation_is_detected(self):
        self.native_mutation('if (lock != 0x68736D53u)','if (lock == 0x68736D53u)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_word_clear_extent_mutation_is_detected(self):
        self.native_mutation('i < 4; ++i','i < 3; ++i')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_reverb_shift_mutation_is_detected(self):
        self.native_mutation('pcm_asr(sample * reverb, 9)','pcm_asr(sample * reverb, 8)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_packed_carry_mask_mutation_is_detected(self):
        self.native_mutation('~0x00FF0000u','~0u')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_master_gain_mutation_is_detected(self):
        self.native_mutation('(R8(sound + 7) + 1u)','(R8(sound + 7) + 0u)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_loop_start_mutation_is_detected(self):
        self.native_mutation('loop_start += offset;','loop_start += offset + 1u;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_fixed_count_mutation_is_detected(self):
        self.native_mutation('count -= budget;','count -= budget + 1u;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_resampling_step_mutation_is_detected(self):
        self.native_mutation('reciprocal * R32(channel + 32)','(reciprocal + 1u) * R32(channel + 32)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_partial_word_rotation_mutation_is_detected(self):
        self.native_mutation('pcm_ror(left, (3u - lane) * 8u)','pcm_ror(left, (2u - lane) * 8u)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_scanline_guard_mutation_is_detected(self):
        self.native_mutation('if (line >= deadline)','if (line > deadline)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_unlock_mutation_is_detected(self):
        self.native_mutation('W32(sound, 0x68736D53u);','W32(sound, 0x68736D54u);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_SoundMain(host);','return host->call(host->user, target, a0, a1, a2);',
            'port/audio/audio_helpers.c','--helpers-source')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_native_player_entry_fallback_is_rejected(self):
        self.native_mutation('Dbaa_MusicPlayerUpdate(host, a0);','host->call(host->user, target, a0, a1, a2);',
            'port/audio/audio_helpers.c','--helpers-source')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_pcm_mixer_player_wait_extra_read_is_detected(self):
        self.native_mutation('W8(track + 1, wait - 1);','W8(track + 1, R8(track + 1) - 1);',
            'port/audio/music_player_update.c','--player-source')


if __name__=='__main__':unittest.main()
