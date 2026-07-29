import os
import numpy as np
from PIL import Image

# Palette standard C64 VIC-II (16 colori) come tuple (R, G, B)
C64_PALETTE = [
    (0, 0, 0),         # 0: Nero
    (255, 255, 255),   # 1: Bianco
    (136, 0, 0),       # 2: Rosso
    (170, 255, 238),   # 3: Ciano
    (204, 68, 204),    # 4: Viola
    (0, 204, 85),      # 5: Verde
    (0, 0, 170),       # 6: Blu
    (238, 238, 119),   # 7: Giallo
    (221, 136, 85),    # 8: Arancione
    (102, 68, 0),      # 9: Marrone
    (255, 119, 119),   # 10: Rosso chiaro (Rosa)
    (51, 51, 51),      # 11: Grigio scuro
    (119, 119, 119),   # 12: Grigio medio
    (170, 255, 102),   # 13: Verde chiaro
    (0, 136, 255),     # 14: Azzurro
    (187, 187, 187)    # 15: Grigio chiaro
]

def decode_sprite_hires(data, sprite_color_idx=1, bg_color_idx=0):
    """
    Decodifica uno sprite C64 Hires (24x21, 1 bit per pixel).
    Prende 63 byte di dati.
    """
    if len(data) < 63:
        # Pad with zeros if short
        data = bytes(data) + b'\x00' * (63 - len(data))

    img = Image.new("RGB", (24, 21), C64_PALETTE[bg_color_idx])
    pixels = img.load()

    for row in range(21):
        offset = row * 3
        # 3 byte per riga = 24 pixel
        row_bytes = data[offset:offset+3]
        for byte_idx, byte in enumerate(row_bytes):
            for bit_idx in range(8):
                pixel_x = byte_idx * 8 + bit_idx
                bit = (byte >> (7 - bit_idx)) & 1
                if bit == 1:
                    pixels[pixel_x, row] = C64_PALETTE[sprite_color_idx]

    return img

def decode_sprite_multicolor(data, sprite_color_idx=1, mc1_color_idx=2, mc2_color_idx=3, bg_color_idx=0):
    """
    Decodifica uno sprite C64 Multicolor (24x21, 2 bit per pixel, larghezza doppia).
    Prende 63 byte di dati.
    """
    if len(data) < 63:
        data = bytes(data) + b'\x00' * (63 - len(data))

    img = Image.new("RGB", (24, 21), C64_PALETTE[bg_color_idx])
    pixels = img.load()

    color_map = {
        0: C64_PALETTE[bg_color_idx],
        1: C64_PALETTE[mc1_color_idx],
        2: C64_PALETTE[sprite_color_idx],
        3: C64_PALETTE[mc2_color_idx]
    }

    for row in range(21):
        offset = row * 3
        row_bytes = data[offset:offset+3]
        for byte_idx, byte in enumerate(row_bytes):
            # Ogni byte definisce 4 coppie di bit (4 pixel di larghezza doppia)
            for pair_idx in range(4):
                pixel_x = (byte_idx * 4 + pair_idx) * 2
                bits = (byte >> (6 - pair_idx * 2)) & 3
                color = color_map[bits]
                # Scrivi pixel a larghezza doppia
                pixels[pixel_x, row] = color
                pixels[pixel_x + 1, row] = color

    return img

def decode_charset_char(data, char_color_idx=1, bg_color_idx=0):
    """
    Decodifica un singolo carattere 8x8 da un charset.
    Prende 8 byte di dati.
    """
    if len(data) < 8:
        data = bytes(data) + b'\x00' * (8 - len(data))

    img = Image.new("RGB", (8, 8), C64_PALETTE[bg_color_idx])
    pixels = img.load()

    for row in range(8):
        byte = data[row]
        for bit_idx in range(8):
            bit = (byte >> (7 - bit_idx)) & 1
            if bit == 1:
                pixels[bit_idx, row] = C64_PALETTE[char_color_idx]

    return img

def decode_bitmap_hires(data, screen_data=None, color_ram=None):
    """
    Decodifica una bitmap intera Hires (320x200).
    Prende 8000 byte di dati bitmap.
    Opzionalmente prende i dati dello schermo (1024 byte) per i colori delle celle 8x8.
    """
    if len(data) < 8000:
        data = bytes(data) + b'\x00' * (8000 - len(data))

    img = Image.new("RGB", (320, 200), C64_PALETTE[0])
    pixels = img.load()

    for char_y in range(25): # 25 righe di caratteri
        for char_x in range(40): # 40 colonne
            # Ogni cella ha colore di background e foreground
            fg_col, bg_col = 1, 0 # Default Bianco su Nero
            if screen_data and len(screen_data) > (char_y * 40 + char_x):
                color_byte = screen_data[char_y * 40 + char_x]
                fg_col = (color_byte >> 4) & 0x0F
                bg_col = color_byte & 0x0F

            cell_offset = (char_y * 40 + char_x) * 8
            for row in range(8):
                byte = data[cell_offset + row]
                pixel_y = char_y * 8 + row
                for bit_idx in range(8):
                    pixel_x = char_x * 8 + bit_idx
                    bit = (byte >> (7 - bit_idx)) & 1
                    color_idx = fg_col if bit == 1 else bg_col
                    pixels[pixel_x, pixel_y] = C64_PALETTE[color_idx]

    return img

def generate_synthetic_sprite_data(pattern_type="balloon"):
    """
    Genera dati di esempio (63 byte) per uno sprite C64 sintetico.
    """
    data = bytearray(63)
    if pattern_type == "balloon":
        # Disegna un palloncino tondo con un filo
        for r in range(15):
            # Cerchio approssimativo
            width = int(5 + 5 * np.sin(np.pi * r / 14))
            for x in range(12 - width, 12 + width):
                byte_idx = x // 8
                bit_idx = x % 8
                data[r * 3 + byte_idx] |= (1 << (7 - bit_idx))
        # Filo
        for r in range(15, 21):
            x = 12 + int(np.sin(r) * 1.5)
            byte_idx = x // 8
            bit_idx = x % 8
            data[r * 3 + byte_idx] |= (1 << (7 - bit_idx))
    elif pattern_type == "alien":
        # Disegna un piccolo alieno/astronave simmetrica
        for r in range(21):
            # Riga simmetrica
            active_pixels = [11, 12]
            if r in (2, 3, 4, 16, 17):
                active_pixels += [6, 7, 16, 17]
            if r in (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15):
                active_pixels += [4, 5, 8, 9, 10, 13, 14, 15, 18, 19]
            for x in active_pixels:
                byte_idx = x // 8
                bit_idx = x % 8
                data[r * 3 + byte_idx] |= (1 << (7 - bit_idx))
    return bytes(data)

def generate_synthetic_char_data():
    """Genera dati di esempio (8 byte) per una lettera 'A' sintetica."""
    return bytes([
        0b00011000,
        0b00111100,
        0b01100110,
        0b01100110,
        0b01111110,
        0b01100110,
        0b01100110,
        0b00000000
    ])

def extract_and_save_all_synthetic(output_dir="data/assets"):
    """
    Crea cartelle e genera asset sintetici di prova, salvandoli come PNG.
    Ritorna la lista degli asset generati con metadati.
    """
    os.makedirs(output_dir, exist_ok=True)
    assets_meta = []

    # 1. Sprite Palloncino (Hires)
    balloon_data = generate_synthetic_sprite_data("balloon")
    img_balloon = decode_sprite_hires(balloon_data, sprite_color_idx=7, bg_color_idx=0) # Giallo su nero
    path_balloon = os.path.join(output_dir, "sprite_balloon.png")
    img_balloon.save(path_balloon)
    assets_meta.append({
        "id": "sprite_balloon",
        "name": "Classic Balloon Sprite",
        "type": "sprite",
        "mode": "hires",
        "dimensions": "24x21",
        "filepath": path_balloon,
        "description": "Un palloncino classico del Commodore 64 con il filo, decodificato in modalita hires."
    })

    # 2. Sprite Alieno (Multicolor)
    alien_data = generate_synthetic_sprite_data("alien")
    img_alien = decode_sprite_multicolor(alien_data, sprite_color_idx=10, mc1_color_idx=3, mc2_color_idx=13, bg_color_idx=0)
    path_alien = os.path.join(output_dir, "sprite_alien.png")
    img_alien.save(path_alien)
    assets_meta.append({
        "id": "sprite_alien",
        "name": "Space Invaders Alien",
        "type": "sprite",
        "mode": "multicolor",
        "dimensions": "24x21",
        "filepath": path_alien,
        "description": "Un alieno in stile Space Invaders decodificato in modalita multicolor con palette a 4 colori."
    })

    # 3. Carattere 'A'
    char_data = generate_synthetic_char_data()
    img_char = decode_charset_char(char_data, char_color_idx=1, bg_color_idx=6) # Bianco su Blu
    path_char = os.path.join(output_dir, "char_a.png")
    img_char.save(path_char)
    assets_meta.append({
        "id": "char_a",
        "name": "Custom Font Char 'A'",
        "type": "charset",
        "mode": "hires",
        "dimensions": "8x8",
        "filepath": path_char,
        "description": "Un carattere personalizzato per la lettera 'A' decodificato a partire da un blocco di 8 byte."
    })

    return assets_meta
