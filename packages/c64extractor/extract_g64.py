import os
import sys
import re
import struct
import logging

from packages.c64extractor.basic_tokens import detokenize_basic, hex_dump

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("extract_g64")

GCR5_TO_4 = {
    0x0A: 0, 0x0B: 1, 0x12: 2, 0x13: 3,
    0x0E: 4, 0x0F: 5, 0x16: 6, 0x17: 7,
    0x09: 8, 0x19: 9, 0x1A: 10, 0x1B: 11,
    0x0D: 12, 0x1D: 13, 0x1E: 14, 0x1F: 15,
}

SECTORS_PER_TRACK = {1: 21, 2: 21, 3: 21, 4: 21, 5: 21, 6: 21, 7: 21,
                     8: 21, 9: 21, 10: 21, 11: 21, 12: 21, 13: 21, 14: 21,
                     15: 21, 16: 21, 17: 21,
                     18: 19, 19: 19, 20: 19, 21: 19, 22: 19, 23: 19, 24: 19,
                     25: 18, 26: 18, 27: 18, 28: 18, 29: 18, 30: 18,
                     31: 17, 32: 17, 33: 17, 34: 17, 35: 17,
                     36: 17, 37: 17, 38: 17, 39: 17, 40: 17}


def read_g64_header(data):
    if len(data) < 12:
        raise ValueError("File troppo corto per header G64")
    sig = data[:8]
    if sig[:7] != b"GCR-1541":
        raise ValueError(f"Firma G64 non valida: {sig[:7]}")
    version = struct.unpack_from("<I", data, 8)[0]
    num_tracks = struct.unpack_from("<I", data, 12)[0]
    max_track_size = struct.unpack_from("<I", data, 16)[0]
    track_offsets = []
    for i in range(84):
        off = struct.unpack_from("<I", data, 20 + i * 4)[0]
        track_offsets.append(off)
    track_sizes = []
    for i in range(84):
        sz = struct.unpack_from("<I", data, 20 + 84 * 4 + i * 4)[0]
        track_sizes.append(sz)
    speed_zones = []
    for i in range(84):
        z = struct.unpack_from("<I", data, 20 + 168 * 4 + i * 4)[0]
        speed_zones.append(z)
    actual_tracks = []
    for t in range(min(num_tracks, 84)):
        off = track_offsets[t]
        sz = track_sizes[t]
        if off > 0 and sz > 0 and off + sz <= len(data):
            actual_tracks.append((t + 1, off, sz, speed_zones[t]))
    return {
        "version": version,
        "num_tracks": num_tracks,
        "max_track_size": max_track_size,
        "tracks": actual_tracks,
    }


def decode_sector(gcr_bytes):
    nibbles = []
    for b in gcr_bytes:
        g5 = b & 0x1F
        if g5 in GCR5_TO_4:
            nibbles.append(GCR5_TO_4[g5])
        else:
            return None
    decoded = bytearray()
    for i in range(0, len(nibbles) - 1, 2):
        decoded.append((nibbles[i] << 4) | nibbles[i + 1])
    return bytes(decoded)


def scan_track(track_data):
    sectors = []
    i = 0
    while i < len(track_data) - 10:
        if track_data[i] == 0xFF:
            sync_start = i
            while i < len(track_data) and track_data[i] == 0xFF:
                i += 1
            sync_len = i - sync_start
            if sync_len < 5:
                continue
            while i < len(track_data) and track_data[i] == 0x55:
                i += 1
            if i >= len(track_data):
                break
            marker = track_data[i]
            i += 1
            if marker == 0x08:
                header_gcr = track_data[i:i + 20]
                i += len(header_gcr)
                decoded = decode_sector(header_gcr)
                if decoded and len(decoded) >= 6:
                    sectors.append({
                        "type": "header",
                        "track": decoded[0],
                        "sector": decoded[1],
                        "id1": decoded[4],
                        "id2": decoded[5],
                        "offset": sync_start,
                    })
            elif marker == 0x07:
                data_gcr = track_data[i:i + 520]
                i += len(data_gcr)
                decoded = decode_sector(data_gcr)
                if decoded and len(decoded) >= 257:
                    if decoded[0] == 0:
                        sectors.append({
                            "type": "data",
                            "data": decoded[1:257],
                            "checksum": decoded[257],
                            "offset": sync_start,
                        })
        else:
            i += 1
    return sectors


def match_sectors(raw_sectors):
    headers = [s for s in raw_sectors if s["type"] == "header"]
    datas = [s for s in raw_sectors if s["type"] == "data"]
    result = {}
    for h in headers:
        key = (h["track"], h["sector"])
        best = None
        for d in datas:
            if best is None or abs(d["offset"] - h["offset"]) < abs(best["offset"] - h["offset"]):
                best = d
        if best:
            result[key] = best["data"]
    return result


def read_g64_sectors(g64_data):
    header = read_g64_header(g64_data)
    log.info(f"  Version: {header['version']}, Tracks: {header['num_tracks']}")
    all_sectors = {}
    for track_num, track_off, track_sz, _ in header["tracks"]:
        if track_num > 40:
            break
        track_data = g64_data[track_off:track_off + track_sz]
        raw = scan_track(track_data)
        matched = match_sectors(raw)
        for (t, s), data in matched.items():
            all_sectors[(t, s)] = data
        if track_num < 3 or track_num == 18:
            log.info(f"  Track {track_num}: {len(matched)}/{SECTORS_PER_TRACK.get(track_num, 0)} settori")
    return all_sectors


def read_directory_from_sectors(sectors):
    entries = []
    dir_sector = 18
    while True:
        key = (18, dir_sector)
        if key not in sectors:
            break
        sec = sectors[key]
        for i in range(8):
            off = i * 32
            if off + 32 > len(sec):
                break
            entry = sec[off:off + 32]
            file_type = entry[2]
            if file_type == 0x00:
                continue
            type_map = {0x80: "DEL", 0x81: "SEQ", 0x82: "PRG", 0x83: "USR", 0x84: "REL"}
            ftype = type_map.get(file_type & 0x87, "???")
            raw_name = entry[5:21]
            name = "".join(chr(b & 0x7F) for b in raw_name if b != 0xA0 and b != 0).strip()
            size = entry[30] + (entry[31] << 8)
            first_track = entry[3]
            first_sector = entry[4]
            entries.append((ftype, name, size, first_track, first_sector))
        next_track = sec[0]
        dir_sector = sec[1]
        if next_track == 0:
            break
    return entries


def read_file_from_sectors(sectors, start_track, start_sector):
    data = bytearray()
    t, s = start_track, start_sector
    while t != 0:
        key = (t, s)
        if key not in sectors:
            log.warning(f"  Settore mancante: track {t}, sector {s}")
            break
        sec = sectors[key]
        next_track = sec[0]
        next_sector = sec[1]
        data.extend(sec[2:])
        t, s = next_track, next_sector
    return bytes(data)


def extract_g64(g64_path, output_dir):
    log.info(f"Lettura: {g64_path}")
    with open(g64_path, "rb") as f:
        g64_data = f.read()
    try:
        sectors = read_g64_sectors(g64_data)
    except Exception as e:
        log.error(f"  Errore decodifica G64: {e}")
        return []
    if not sectors:
        log.warning("  Nessun settore decodificato.")
        return []
    entries = read_directory_from_sectors(sectors)
    if not entries:
        log.info("  Directory vuota o non trovata.")
        return []
    log.info(f"  Directory ({len(entries)} file):")
    for ftype, name, size, t, s in entries:
        log.info(f"    {ftype}: {name} ({size} blocchi)  track={t} sector={s}")
    extracted = []
    for ftype, name, size, start_track, start_sector in entries:
        if ftype == "PRG":
            try:
                prg_data = read_file_from_sectors(sectors, start_track, start_sector)
                safe = re.sub(r'[^\w\-_.]', '_', name.lower())
                source = detokenize_basic(prg_data)
                if source.strip():
                    out = os.path.join(output_dir, f"{safe}.bas.txt")
                    with open(out, "w") as f:
                        f.write(f"REM BASIC extracted from G64\nREM File: {name}\n\n{source}")
                    log.info(f"  BASIC → {out}")
                    extracted.append(out)
                ml_out = os.path.join(output_dir, f"{safe}.ml.txt")
                with open(ml_out, "w") as f:
                    f.write(f"; ML dump from G64: {name}\n")
                    if len(prg_data) >= 2:
                        addr = prg_data[0] + (prg_data[1] << 8)
                        f.write(f"; Load address: ${addr:04X}\n")
                    f.write(f"; Size: {len(prg_data)} bytes\n\n")
                    f.write(hex_dump(prg_data))
                log.info(f"  ML dump → {ml_out}")
                extracted.append(ml_out)
            except Exception as e:
                log.warning(f"  Errore estrazione {name}: {e}")
    return extracted


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/extract_g64.py <file.g64> [output_dir]")
        sys.exit(1)
    g64_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
    os.makedirs(output_dir, exist_ok=True)
    extracted = extract_g64(g64_path, output_dir)
    log.info(f"\nEstratti {len(extracted)} file.")


if __name__ == "__main__":
    main()
