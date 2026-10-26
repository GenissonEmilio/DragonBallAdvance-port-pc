"""Compare named gameplay observations without masking or editing game memory."""
from pathlib import Path
import argparse
import csv
import hashlib
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference-offset', type=int, default=-1)
    parser.add_argument('--first-frame', type=int, default=2450)
    parser.add_argument('--last-frame', type=int, default=6000)
    args = parser.parse_args()
    assert not args.out.exists(), 'preserve earlier comparison'
    native = list(csv.DictReader(args.native.open()))
    reference = {int(r['frame']): r for r in csv.DictReader(args.reference.open())}
    fields = ['x256', 'y256', 'camera_x', 'camera_y', 'state_00', 'state_08']
    count, mismatches = 0, []
    for row in native:
        frame = int(row['frame'])
        if not args.first_frame <= frame <= args.last_frame:
            continue
        ref = reference.get(frame + args.reference_offset)
        assert ref is not None, frame
        differences = {f: dict(native=int(row[f]), reference=int(ref[f])) for f in fields if int(row[f]) != int(ref[f])}
        count += 1
        if differences:
            mismatches.append(dict(native_frame=frame, reference_frame=int(ref['frame']), differences=differences))
    assert count
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(observations=count, fields=fields, differences=len(mismatches),
                  reference_frame_offset=args.reference_offset, first_frame=args.first_frame,
                  last_frame=args.last_frame, first_differences=mismatches[:24],
                  native_sha256=sha(args.native), reference_sha256=sha(args.reference), tool_sha256=sha(Path(__file__)),
                  observations_equal=not mismatches, full_memory_compared=False, native_game_parity_validated=False)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
