import os
import sys
import re
import logging

from packages.c64extractor.basic_tokens import BASIC_TOKENS, detokenize_basic

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("extract_d64")


def read_sector(d64_data, track, sector):
    """Read a sector from D64 image. Track 1-35, sector 0-16/17/20."""
    track_offsets = {}
    offset = 0
    for t in range(1, 36):
        sectors = 21 if t < 18 else 19 if t < 25 else 18 if t < 31 else 17
        track_offsets[t] = (offset, sectors)
        offset += sectors * 256
    if track not in track_offsets:
        raise ValueError(f"Track {track} out of range")
    t_off, t_sectors = track_offsets[track]
    if sector >= t_sectors:
        raise ValueError(f"Sector {sector} out of range for track {track}")
    start = t_off + sector * 256
    return d64_data[start:start + 256]


def read_directory(d64_data):
    """Read directory from D64 image. Returns list of (type, name, size_blocks)."""
    entries = []
    dir_sector = 18  # sector 18 on track 18
    while True:
        sec = read_sector(d64_data, 18, dir_sector)
        for i in range(8):
            off = i * 32
            entry = sec[off:off + 32]
            if len(entry) < 32:
                break
            file_type = entry[2]
            if file_type == 0x00:
                continue  # unused
            type_map = {0x80: "DEL", 0x81: "SEQ", 0x82: "PRG", 0x83: "USR", 0x84: "REL"}
            ftype = type_map.get(file_type & 0x87, "???")
            raw_name = entry[5:21]
            name = "".join(chr(b & 0x7F) for b in raw_name if b != 0xA0 and b != 0).strip()
            size = entry[30] + (entry[31] << 8)
            entries.append((ftype, name, size))
        next_track = sec[0]
        dir_sector = sec[1]
        if next_track == 0:
            break
    return entries


def extract_file(d64_data, name):
    """Extract a PRG file by name from D64. Returns (load_address_lo, load_addr_hi, data)."""
    dir_sector = 18
    target = name.upper().strip()
    while True:
        sec = read_sector(d64_data, 18, dir_sector)
        for i in range(8):
            off = i * 32
            entry = sec[off:off + 32]
            if len(entry) < 5:
                break
            raw_name = entry[5:21]
            fname = "".join(chr(b & 0x7F) for b in raw_name if b != 0xA0 and b != 0).strip()
            if fname.upper() == target:
                start_track = entry[3]
                start_sector = entry[4]
                size = entry[30] + (entry[31] << 8)
                return read_chain(d64_data, start_track, start_sector)
        next_track = sec[0]
        dir_sector = sec[1]
        if next_track == 0:
            break
    raise FileNotFoundError(f"File '{name}' not found in D64")


def read_chain(d64_data, track, sector):
    """Read a chain of sectors starting from track/sector. Returns full data."""
    data = bytearray()
    while track != 0:
        sec = read_sector(d64_data, track, sector)
        next_track = sec[0]
        next_sector = sec[1]
        data.extend(sec[2:])
        track, sector = next_track, next_sector
    return bytes(data)


def extract_d64(d64_path, output_dir):
    """Extract all BASIC programs from a D64 file."""
    log.info(f"Lettura: {d64_path}")
    with open(d64_path, "rb") as f:
        d64_data = f.read()

    entries = read_directory(d64_data)
    if not entries:
        log.info("  Nessun file trovato nel D64.")
        return []

    log.info(f"  Directory ({len(entries)} file):")
    for ftype, name, size in entries:
        log.info(f"    {ftype}: {name} ({size} blocchi)")

    extracted = []
    for ftype, name, size in entries:
        if ftype == "PRG":
            try:
                prg_data = extract_file(d64_data, name)
                source = detokenize_basic(prg_data)
                if source.strip():
                    safe = re.sub(r'[^\w\-_.]', '_', name.lower())
                    out_path = os.path.join(output_dir, f"{safe}.bas.txt")
                    with open(out_path, "w") as f:
                        f.write(f"REM BASIC program extracted from D64\n")
                        f.write(f"REM File: {name}\n\n")
                        f.write(source)
                    log.info(f"  Estratto BASIC: {name} → {out_path}")
                    extracted.append(out_path)
            except Exception as e:
                log.warning(f"  Errore estrazione {name}: {e}")

    return extracted


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/extract_d64.py <file.d64> [output_dir]")
        sys.exit(1)

    d64_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
    os.makedirs(output_dir, exist_ok=True)

    extracted = extract_d64(d64_path, output_dir)
    log.info(f"\nEstratti {len(extracted)} file BASIC.")


if __name__ == "__main__":
    main()
