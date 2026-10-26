/* SPDX-License-Identifier: MPL-2.0
 * Fixed-point BIOS math, adapted from mGBA src/gba/bios.c.
 * Copyright (c) 2013-2025 Jeffrey Pfau; adaptations 2026.
 * MPL-2.0: port/third_party/mgba-MPL-2.0.txt.
 * Multiplications explicitly keep their low ARM word; no signed overflow. */
#ifndef DBAA_BIOS_MATH_H
#define DBAA_BIOS_MATH_H
#include <stdint.h>

static inline int32_t Dbaa_BiosAsr(uint32_t value, unsigned shift) {
  return (int32_t)((value >> shift) | ((value & 0x80000000u) ? (~0u << (32-shift)) : 0));
}
static inline int32_t Dbaa_BiosAtanPolynomial(int32_t value, uint32_t *square, uint32_t *polynomial) {
  static const uint32_t terms[] = {0x390, 0x91C, 0xFB6, 0x16AA, 0x2081, 0x3651, 0xA2F9};
  int32_t a = -Dbaa_BiosAsr((uint32_t)value * (uint32_t)value, 14);
  uint32_t b = 0xA9;
  for (unsigned i = 0; i < sizeof(terms)/sizeof(terms[0]); ++i)
    b = (uint32_t)Dbaa_BiosAsr(b * (uint32_t)a, 14) + terms[i];
  *square = (uint32_t)a;
  *polynomial = b;
  return (int16_t)Dbaa_BiosAsr((uint32_t)value * b, 16);
}
static inline void Dbaa_BiosArcTan(uint32_t registers[4]) {
  registers[0] = (uint32_t)Dbaa_BiosAtanPolynomial((int32_t)registers[0], &registers[1], &registers[3]);
}
static inline void Dbaa_BiosArcTan2(uint32_t registers[4]) {
  int32_t x = (int32_t)registers[0], y = (int32_t)registers[1];
  int32_t angle;
  registers[3] = 0x170;
  if (!y) angle = x < 0 ? 0x8000 : 0;
  else if (!x) angle = y < 0 ? 0xC000 : 0x4000;
  else {
    int64_t ax = x < 0 ? -(int64_t)x : x, ay = y < 0 ? -(int64_t)y : y;
    uint32_t polynomial;
    if (ax >= ay) {
      int32_t ratio = (int32_t)((int64_t)y * 0x4000 / x);
      angle = Dbaa_BiosAtanPolynomial(ratio, &registers[1], &polynomial);
      if (x < 0) angle += 0x8000;
      else if (y < 0) angle += 0x10000;
    } else {
      int32_t ratio = (int32_t)((int64_t)x * 0x4000 / y);
      angle = (y < 0 ? 0xC000 : 0x4000) - Dbaa_BiosAtanPolynomial(ratio, &registers[1], &polynomial);
    }
  }
  registers[0] = (uint16_t)angle;
}
#endif
