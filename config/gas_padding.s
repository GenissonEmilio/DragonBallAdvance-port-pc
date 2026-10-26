/* Reproduce zero-filled object alignment used by the original toolchain.
 * Modern ARM gas automatically fills a final Thumb section gap with a NOP.
 * This explicit alignment emits zero padding, not executable replacement code.
 */
.text
.balign 4, 0
