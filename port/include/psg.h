#ifndef DBAA_PSG_H
#define DBAA_PSG_H
#include <stdint.h>
typedef struct DbaaPsg DbaaPsg;
/* Native chip synthesis; there is no ARM/Thumb CPU in this component. Cycles
 * are monotonic 16.777216 MHz timestamps supplied by the game scheduler. */
DbaaPsg *Dbaa_PsgCreate(void);
void Dbaa_PsgDestroy(DbaaPsg *);
int Dbaa_PsgAdvance(DbaaPsg *, uint64_t cycles);
int Dbaa_PsgWrite(DbaaPsg *, uint64_t cycles, uint32_t address,
                  uint32_t value, unsigned width);
uint8_t Dbaa_PsgStatus(const DbaaPsg *);
void Dbaa_PsgSample(DbaaPsg *, int16_t *left, int16_t *right);
#endif
