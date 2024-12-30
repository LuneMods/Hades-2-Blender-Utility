import os
import struct
import tempfile


def compress_gr2(input_file, output_file):
    with open(input_file, 'rb') as file:
        data = bytearray(file.read())

    compressed = bytearray()
    data_length = len(data)

    if data_length <= 12:
        # Directly encode small files as literals
        prefix, _ = encode_literals(data_length, 0, -1)
        compressed += prefix + data
    else:
        sliding_window = {}
        literal_start = 0
        pos = 0
        max_compression_size = data_length / 1.25
        end_of_file = False

        while pos < data_length and not end_of_file:
            key = bytes(data[pos:pos + 4])
            remaining_bytes = calculate_extended_value_length(data_length - pos) + 1

            # Check if adding more data will exceed the max compressed size
            if len(compressed) + (data_length - pos) + remaining_bytes >= max_compression_size:
                if key not in sliding_window:
                    sliding_window[key] = pos
                    if pos >= data_length - 5:
                        # Encode trailing literals
                        prefix, _ = encode_literals(data_length - literal_start, 0, -1)
                        compressed += prefix + data[literal_start:]
                        pos = data_length
                    else:
                        pos += 1
                else:
                    match_pos, match_length = find_match(data, pos, sliding_window)
                    if match_pos == -1:
                        pos += 1
                    else:
                        if pos + match_length < data_length - 5:
                            # Encode match
                            end = pos + match_length
                            update_pos = pos + 1

                            # Update sliding window for sub-matches
                            while update_pos < end:
                                sub_key = bytes(data[update_pos:update_pos + 4])
                                sliding_window[sub_key] = update_pos
                                update_pos += 1

                            literal_length = pos - literal_start
                            match_size = match_length - 4
                            offset = pos - match_pos
                            prefix, match_encoding = encode_literals(literal_length, match_size, offset)
                            compressed += prefix + data[literal_start:pos] + match_encoding
                            pos += match_length
                            literal_start = pos
                        else:
                            # Encode remaining literals
                            prefix, _ = encode_literals(data_length - literal_start, 0, -1)
                            compressed += prefix + data[literal_start:]
                            pos = data_length
            else:
                # End of file: encode remaining data as literals
                prefix, _ = encode_literals(data_length - literal_start, 0, -1)
                compressed += prefix + data[literal_start:]
                end_of_file = True


    with open(output_file, "wb") as file:
        file.write(compressed)

def decompress_lz4(input_file):
    with open(input_file, 'rb') as f:
        compressed = f.read()

    decompressed = bytearray()
    pos = 0

    while pos < len(compressed):
        token = compressed[pos]
        pos += 1

        # Decode literal length
        literal_length = token >> 4
        if literal_length == 15:
            extra_length, pos = decode_extended_value(compressed, pos)
            literal_length += extra_length

        # Copy literals
        decompressed.extend(compressed[pos:pos + literal_length])
        pos += literal_length

        if pos >= len(compressed):
            break

        # Decode match offset
        match_offset = struct.unpack('<H', compressed[pos:pos + 2])[0]
        pos += 2

        # Decode match length
        match_length = (token & 0xF) + 4
        if match_length - 4 == 15:
            extra_length, pos = decode_extended_value(compressed, pos)
            match_length += extra_length

        # Copy match
        match_start = len(decompressed) - match_offset
        for _ in range(match_length):
            decompressed.append(decompressed[match_start])
            match_start += 1

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gr2", mode='wb')
    temp_file.write(decompressed)
    temp_file.close()

    return temp_file.name

# Supporting Functions
def encode_literals(lit_len, match_len, offset):
    lit_token = []
    match_token = []

    if offset != -1:
        match_token.append(offset % 256)
        match_token.append(offset // 256)

    if lit_len >= 15:
        lit_token.append(240)
        lit_len -= 15
        lit_token.extend(encode_extended_value(lit_len))
    else:
        lit_token.append(lit_len * 16)

    if match_len >= 15:
        lit_token[0] += 15
        match_len -= 15
        match_token.extend(encode_extended_value(match_len))
    else:
        lit_token[0] += match_len

    return bytearray(lit_token), bytearray(match_token)

def encode_extended_value(value):
    result = []
    while value >= 255:
        result.append(255)
        value -= 255
    result.append(value)
    return result

def calculate_extended_value_length(value):
    return (value // 255) + (1 if value % 255 != 0 else 0)

def find_match(data, pos, sliding_window):
    key = bytes(data[pos:pos + 4])
    if key in sliding_window:
        match_pos = sliding_window[key]
        match_offset = pos - match_pos

        if match_offset > 65535:
            return -1, 0  # Ignore matches with offsets > 65535

        match_length = 4
        while pos + match_length < len(data) and data[match_pos + match_length] == data[pos + match_length]:
            match_length += 1

        return match_pos, match_length

    sliding_window[key] = pos
    return -1, 0

def decode_extended_value(data, pos):
    value = 0
    while data[pos] == 255:
        value += 255
        pos += 1
    value += data[pos]
    pos += 1
    return value, pos