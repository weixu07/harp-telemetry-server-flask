import hashlib

def hex_viewer(buf: bytes) -> str:
    ret = ''
    hex_line = ''
    ascii_line = ''

    for i in range(len(buf)):
        if (i > 0) and ((i % 16) == 0):
            ret += f'{hex_line} | {ascii_line}\r\n'
            ascii_line = ''
            hex_line = ''

        b = buf[i]

        hex_char = hex(b)[2:]
        if len(hex_char) == 1:
            hex_char = '0' + hex_char
        hex_line += hex_char

        if (b >= ord(' ')) and (b <= ord('~')):
            ascii_line += chr(b)
        else:
            ascii_line += '.'

    while (len(ascii_line) % 16) != 0:
        ascii_line += ' '
        hex_line += '  '
    if len(ascii_line) > 0:
        ret += f'{hex_line} | {ascii_line}\r\n'

    return ret

def calculate_pcrs_hash(fpath: str):
    with open(fpath, 'rb') as f:
        pcrs_hash = hashlib.sha256(f.read()).hexdigest()
    return pcrs_hash[:7]