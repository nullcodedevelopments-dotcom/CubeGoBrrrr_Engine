import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from .paths import get_shaders_dir, get_textures_dir, get_models_dir
from .reader import read_text, read_bytes, write_text

# Image container
@dataclass
class Image:
    width:    int
    height:   int
    channels: int   # 3 = RGB, 4 = RGBA
    data:     bytes # raw pixel bytes, left-to-right, top-to-bottom



# Shaders
def load_shader(filename: str) -> str:
    return read_text(get_shaders_dir() / filename)


def load_shader_pair(name: str) -> tuple[str, str]:
    vert = load_shader(f"{name}.vert")
    frag = load_shader(f"{name}.frag")
    return vert, frag

# Textures - BMP Parser
def load_bmp(filename: str) -> Image:
    data = read_bytes(get_textures_dir() / filename)

    sig = data[0:2]
    if sig != b"BM":
        raise ValueError(f"Not a BMP file: {filename}")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]

    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise ValueError(f"Unsupported BMP DIB header size: {dib_size}")

    width, height = struct.unpack_from("<ii", data, 18)
    bpp           = struct.unpack_from("<H", data, 28)[0]
    compression   = struct.unpack_from("<I", data, 30)[0]

    if bpp not in (24, 32):
        raise ValueError(f"Unsupported BMP bit depth: {bpp} (only 24 and 32 supported)")
    if compression not in (0, 3):
        raise ValueError(f"Unsupported BMP compression: {compression}")

    flipped = height > 0 
    height  = abs(height)
    channels = bpp // 8
    row_size = (width * channels + 3) & ~3

    raw_pixels = bytearray(width * height * channels)

    for row in range(height):
        src_row = (height - 1 - row) if flipped else row
        row_start = pixel_offset + src_row * row_size
        dst_start = row * width * channels

        for col in range(width):
            src = row_start + col * channels
            dst = dst_start + col * channels

            raw_pixels[dst]     = data[src + 2]  # R
            raw_pixels[dst + 1] = data[src + 1]  # G
            raw_pixels[dst + 2] = data[src]      # B
            if channels == 4:
                raw_pixels[dst + 3] = data[src + 3]  # A

    return Image(width=width, height=height, channels=channels, data=bytes(raw_pixels))


# Textures - TGA Parser
def load_tga(filename: str) -> Image:
    data = read_bytes(get_textures_dir() / filename)

    id_length      = data[0]
    color_map_type = data[1]
    image_type     = data[2]

    if color_map_type != 0:
        raise ValueError("Colour-mapped TGA files are not supported")
    if image_type not in (2, 10):
        raise ValueError(f"Unsupported TGA image type: {image_type} (only 2 and 10 supported)")

    # Header: 18 bytes total; pixel data starts after header + image-id field
    width, height = struct.unpack_from("<HH", data, 12)
    pixel_depth   = data[16]
    image_desc    = data[17]

    if pixel_depth not in (24, 32):
        raise ValueError(f"Unsupported TGA bit depth: {pixel_depth}")

    channels  = pixel_depth // 8
    origin    = (image_desc >> 4) & 1  # bit 4: 0 = bottom-left, 1 = top-left
    offset    = 18 + id_length

    total_pixels = width * height
    raw_pixels   = bytearray(total_pixels * channels)

    if image_type == 2:
        # Uncompressed
        for i in range(total_pixels):
            src = offset + i * channels
            dst = i * channels
            raw_pixels[dst]     = data[src + 2]  # R
            raw_pixels[dst + 1] = data[src + 1]  # G
            raw_pixels[dst + 2] = data[src]      # B
            if channels == 4:
                raw_pixels[dst + 3] = data[src + 3]  # A
    else:
        # RLE compressed (type 10)
        pixel_index = 0
        pos = offset
        while pixel_index < total_pixels:
            rep_count = data[pos]; pos += 1
            if rep_count & 0x80:
                # Run-length packet: repeat the next pixel (rep_count & 0x7F + 1) times
                count = (rep_count & 0x7F) + 1
                r = data[pos + 2]
                g = data[pos + 1]
                b = data[pos]
                a = data[pos + 3] if channels == 4 else None
                pos += channels
                for _ in range(count):
                    dst = pixel_index * channels
                    raw_pixels[dst]     = r
                    raw_pixels[dst + 1] = g
                    raw_pixels[dst + 2] = b
                    if channels == 4:
                        raw_pixels[dst + 3] = a
                    pixel_index += 1
            else:
                # Raw packet: read (rep_count + 1) literal pixels
                count = rep_count + 1
                for _ in range(count):
                    dst = pixel_index * channels
                    raw_pixels[dst]     = data[pos + 2]
                    raw_pixels[dst + 1] = data[pos + 1]
                    raw_pixels[dst + 2] = data[pos]
                    if channels == 4:
                        raw_pixels[dst + 3] = data[pos + 3]
                    pos          += channels
                    pixel_index  += 1

    # Flip rows if origin is bottom-left (standard TGA)
    if not origin:
        row_bytes = width * channels
        flipped   = bytearray(len(raw_pixels))
        for row in range(height):
            src_row = (height - 1 - row) * row_bytes
            dst_row = row * row_bytes
            flipped[dst_row:dst_row + row_bytes] = raw_pixels[src_row:src_row + row_bytes]
        raw_pixels = flipped

    return Image(width=width, height=height, channels=channels, data=bytes(raw_pixels))

# Textures - PNG Parser
_PNG_SIG = b"\x89PNG\r\n\x1a\n"

def load_png(filename: str) -> Image:
    """Load an 8-bit RGB or RGBA PNG file.

    Uses stdlib zlib for DEFLATE decompression — no external dependencies.
    """
    data = read_bytes(get_textures_dir() / filename)

    if data[:8] != _PNG_SIG:
        raise ValueError(f"Not a valid PNG file: {filename}")

    # Parse chunks
    idat_chunks: list[bytes] = []
    width = height = bit_depth = color_type = 0
    pos = 8

    while pos < len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        chunk_type = data[pos + 4: pos + 8].decode("ascii", errors="replace")
        chunk_data = data[pos + 8: pos + 8 + length]
        pos += 12 + length  # length(4) + type(4) + data(length) + crc(4)

        if chunk_type == "IHDR":
            width, height = struct.unpack_from(">II", chunk_data, 0)
            bit_depth  = chunk_data[8]
            color_type = chunk_data[9]
        elif chunk_type == "IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == "IEND":
            break

    if bit_depth != 8:
        raise ValueError(f"Unsupported PNG bit depth: {bit_depth} (only 8-bit supported)")
    if color_type not in (2, 6):  # 2 = RGB, 6 = RGBA
        raise ValueError(f"Unsupported PNG colour type: {color_type} (only RGB and RGBA supported)")

    channels   = 3 if color_type == 2 else 4
    compressed = b"".join(idat_chunks)
    raw        = zlib.decompress(compressed)

    # Each row has a 1-byte filter type prefix
    stride     = width * channels
    raw_pixels = bytearray(width * height * channels)

    def _paeth(a: int, b: int, c: int) -> int:
        p  = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    for row in range(height):
        ftype  = raw[row * (stride + 1)]
        src    = row * (stride + 1) + 1
        dst    = row * stride

        row_data = bytearray(raw[src: src + stride])

        if ftype == 0:   # None
            pass
        elif ftype == 1: # Sub
            for i in range(channels, stride):
                row_data[i] = (row_data[i] + row_data[i - channels]) & 0xFF
        elif ftype == 2: # Up
            if row > 0:
                for i in range(stride):
                    row_data[i] = (row_data[i] + raw_pixels[dst - stride + i]) & 0xFF
        elif ftype == 3: # Average
            for i in range(stride):
                a = row_data[i - channels] if i >= channels else 0
                b = raw_pixels[dst - stride + i] if row > 0 else 0
                row_data[i] = (row_data[i] + (a + b) // 2) & 0xFF
        elif ftype == 4: # Paeth
            for i in range(stride):
                a = row_data[i - channels] if i >= channels else 0
                b = raw_pixels[dst - stride + i] if row > 0 else 0
                c = raw_pixels[dst - stride + i - channels] if (row > 0 and i >= channels) else 0
                row_data[i] = (row_data[i] + _paeth(a, b, c)) & 0xFF
        else:
            raise ValueError(f"Unknown PNG filter type: {ftype}")

        raw_pixels[dst: dst + stride] = row_data

    return Image(width=width, height=height, channels=channels, data=bytes(raw_pixels))


def load_texture(filename: str) -> Image:
    """Load a texture by file extension. Supports .bmp, .tga, .png."""
    ext = Path(filename).suffix.lower()
    loaders = {
        ".bmp": load_bmp,
        ".tga": load_tga,
        ".png": load_png,
    }
    if ext not in loaders:
        raise ValueError(f"Unsupported texture format: '{ext}' (supported: .bmp, .tga, .png)")
    return loaders[ext](filename)


# ---------------------------------------------------------------------------
# Models — custom OBJ parser (no external dependencies)
# ---------------------------------------------------------------------------

def load_obj(filename: str) -> dict:
    """Parse a Wavefront .obj file.

    Returns a dict with keys:
      - 'vertices': list of (x, y, z) tuples
      - 'normals':  list of (nx, ny, nz) tuples
      - 'uvs':      list of (u, v) tuples
      - 'faces':    list of face index groups [[v/vt/vn, ...], ...]
    """
    vertices: list[tuple] = []
    normals:  list[tuple] = []
    uvs:      list[tuple] = []
    faces:    list[list]  = []

    for line in read_text(get_models_dir() / filename).splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if parts[0] == "v":
            vertices.append(tuple(float(x) for x in parts[1:4]))
        elif parts[0] == "vn":
            normals.append(tuple(float(x) for x in parts[1:4]))
        elif parts[0] == "vt":
            uvs.append(tuple(float(x) for x in parts[1:3]))
        elif parts[0] == "f":
            faces.append([p.split("/") for p in parts[1:]])

    return {"vertices": vertices, "normals": normals, "uvs": uvs, "faces": faces}


# ---------------------------------------------------------------------------
# JSON configs — stdlib only
# ---------------------------------------------------------------------------

def load_json(path: str | Path) -> dict:
    return json.loads(read_text(path))


def save_json(path: str | Path, data: dict, indent: int = 4) -> None:
    write_text(path, json.dumps(data, indent=indent))
