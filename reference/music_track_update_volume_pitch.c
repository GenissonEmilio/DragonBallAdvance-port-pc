/* Readable algorithm reference: NONMATCHING and excluded from production. */
#include "audio.h"
void MusicTrack_UpdateVolumePitch(struct MusicPlayer *player,
                                  struct MusicTrack *object) {
  struct MusicTrack *track = object;
  if (track->status & 1) {
    DbaaU32 volume = (DbaaU32)(track->volumePublic * track->volume) >> 5;
    int pan;
    if (track->modType == 1)
      volume = (volume * (track->modulation + 128)) >> 7;
    pan = 2 * track->pan + track->panPublic;
    if (track->modType == 2)
      pan += track->modulation;
    if (pan < -128)
      pan = -128;
    else if (pan > 127)
      pan = 127;
    track->right = ((pan + 128) * volume) >> 8;
    track->left = ((127 - pan) * volume) >> 8;
  }
  if (track->status & 4) {
    int bend = track->bend * track->bendRange;
    int pitch = (track->tune + bend) * 4 + track->keyShift * 256 +
                track->keyShiftPublic * 256 + track->pitchPublic;
    if (!track->modType)
      pitch += track->modulation * 16;
    track->calculatedKey = pitch >> 8;
    track->calculatedPitch = pitch;
  }
  track->status &= 0xFA;
}
