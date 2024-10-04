import sys
from typing import List, Tuple, Optional
from threading import Thread
import socket
import time
import fcntl
import select
from dataclasses import dataclass
import struct
import os
import time
import re

import pcr_fields
from pcr_fields import PacketMetadata, PacketRecipe
from hts_utils import hex_viewer, calculate_pcrs_hash

def load_config(fpath: str) -> List[PacketRecipe]:
    ret: List[PacketRecipe] = []
    id_list: List[int] = []
    rean_style = False
    harp_style = False
    f = open(fpath, 'r')

    while True:
        line = f.readline()
        if line == '':
            break
        line = line.strip()

        cur_harp_style = False
        pkt_id: int
        n_fields: int
        field_ids: List[int] = []

        if line.startswith(':wycfg pcr['):
            # expect format like:
            # :wycfg pcr[index] <id><cnt><fields...>
            harp_style = True
            cur_harp_style = True
            idx = int(re.search(r"\[([0-9]+)\]", line).group(1))
            recipe = line.strip().split()[-1]

            if (len(recipe) % 2) != 0 or (len(recipe) < 4):
                raise ValueError(f'Malformed Harp packet recipe: {line}')

            if (recipe[0] == '"') and (recipe[-1] == '"'):
                recipe = recipe[1:-1]

            pkt_id = int(recipe[0:2], 16)
            n_fields = int(recipe[2:4], 16)
            if len(recipe) != (4 + (2*n_fields)):
                raise ValueError(f'PCR field count does not match configured count: {line}')

            for i in range(4, len(recipe), 2):
                field_ids.append(int(recipe[i:i+2], 16))
        elif line.startswith('!cs:95'):
            # expect format like:
            # !cs:95,<index>,<id>,<cnt>,<fields...>
            rean_style = True
            toks = line.replace(':', ',').split(',')
            if len(toks) < 5:
                raise ValueError(f'Invalid config 95: {line}')
            idx = int(toks[2])
            pkt_id = int(toks[3])
            n_fields = int(toks[4])
            if len(toks) != (5 + n_fields):
                raise ValueError(f'PCR field count does not match configured count: {line}')

            field_ids = list(map(lambda f: int(f, 16), toks[5:]))
        else:
            continue

        # Try to find our packet
        new_pcr = PacketRecipe(idx, pkt_id, cur_harp_style)
        for field_id in field_ids:
            found = False
            for field in pcr_fields.PCR_FIELDS:
                if cur_harp_style and field.harp_id == field_id:
                    new_pcr.fields.append(field)
                    found = True
                    break
                elif field.rean_id == field_id:
                    new_pcr.fields.append(field)
                    found = True
                    break

            if not found:
                raise ValueError(f'Could not find PCR with ID {field_id}')

        if (len(new_pcr.fields) == 0) or (type(new_pcr.fields[0]) is not pcr_fields.PacketIdPcrField):
            raise ValueError(f'PCR {pkt_id} does not contain the packet ID as the first field')

        has_seq = False
        has_dsn = False
        has_lt = False
        has_ln = False
        for field in new_pcr.fields:
            if type(field) is pcr_fields.SequenceNumberPcrField:
                has_seq = True
            elif type(field) is pcr_fields.DsnPcrField:
                has_dsn = True
            elif type(field) is pcr_fields.LatitudePcrField:
                has_lt = True
            elif type(field) is pcr_fields.LongitudePcrField:
                has_ln = True
        if not has_seq:
            sys.stderr.write(f'WARN: PCR {pkt_id} does not contain sequence number, will not be able to ack packet\r\n')
        if not has_dsn:
            sys.stderr.write(f'WARN: PCR {pkt_id} does not contain DSN\r\n')
        if not has_lt or not has_ln:
            sys.stderr.write(f'WARN: PCR {pkt_id} does not contain GPS coordinates\r\n')

        ret.append(new_pcr)
        if pkt_id in id_list:
            sys.stderr.write(f'WARNING: Duplicate packet ID {pkt_id}\r\n')
        else:
            id_list.append(pkt_id)

        if cur_harp_style:
            to_print = f'Loaded Harp style PCR with ID {pkt_id}: '
        else:
            to_print = f'Loaded Reanimate style PCR with ID {pkt_id}: '
        for field_id in field_ids:
            to_print += hex(field_id) + ', '
        print(to_print)
        print()

    if harp_style and rean_style:
        sys.stderr.write('WARNING: Mixed Harp and Reanimate config styles\r\n')
    
    pcrs_hash = calculate_pcrs_hash(fpath)

    return ret, pcrs_hash

class HTS(Thread):
    pcrs: List[PacketRecipe]
    '''Configured packet recipes'''
    sock: socket.socket
    '''UDP socket'''
    addr: Tuple[str, int]
    '''Bound address'''
    output_folder: str
    '''Folder to store all device output'''

    def __init__(self, pcrs: List[PacketRecipe], pcrs_hash: str, ip: str, port: int, output_folder: str):
        super().__init__()
        self.pcrs = pcrs
        self.pcrs_hash = pcrs_hash
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (ip, port)
        self.running = False
        self.output_folder = output_folder

        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)

    def start(self) -> None:
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        print(f'### Listening for Harp UDP data on {self.addr[0]}:{self.addr[1]} ###\r\n')
        return super().start()

    def run(self):
        self.running = True
        while self.running:
            read_rdy, _, _ = select.select([ self.sock ], [], [], 1)
            if len(read_rdy) == 0:
                continue
            data, addr = self.sock.recvfrom(1024)

            print(f'Packet from {addr[0]}')
            print(hex_viewer(data))

            info: PacketMetadata = None
            for pcr in self.pcrs:
                if pcr.packet_is_this(data):
                    info = pcr.validate_packet(data)
                    break

            if info is None:
                print('Unrecognized packet!!!')
                continue

            if not info.validated:
                print('Invalid packet')
                continue

            if info.validated and info.seq_num is not None:
                ack = struct.pack('>BBH', 0x88, 0x88, info.seq_num)
                print(f'ACK message: {ack.hex()}')
                self.sock.sendto(ack, addr)

            self.store_data(data, addr[0], info)
            print(f'Stored data for DSN {info.dsn}\r\n')

    def kill(self):
        self.running = False

    def store_data(self, data: bytes, addr: str, metadata: PacketMetadata):
        if metadata.dsn is None:
            out_folder = os.path.join(self.output_folder, 'unknown_dsn')
        else:
            out_folder = os.path.join(self.output_folder, str(metadata.dsn))

        if not os.path.isdir(out_folder):
            os.mkdir(out_folder)

        today_str = time.strftime('%m-%d-%y', time.localtime())
        if metadata.dsn is not None:
            filename = os.path.join(out_folder, f'{metadata.dsn}_{today_str}_{self.pcrs_hash}.csv')
        else:
            filename = os.path.join(out_folder, f'unknown_dsn_{today_str}_{self.pcrs_hash}.csv')

        if not os.path.isfile(filename):
            f = open(filename, 'w')
            for recipe in self.pcrs:
                f.write(recipe.to_config()+'\r\n')
            f.write('timestamp,ip,data\r\n')
        else:
            f = open(filename, 'a')

        f.write(f'{int(time.time())},{addr},{data.hex()}\r\n')
        f.close()




if __name__ == '__main__':
    if len(sys.argv) != 5:
        print('Usage: hts.py <config file> <IP> <port> <output_folder>')
        sys.exit(0)

    config, pcrs_hash = load_config(sys.argv[1])
    server = HTS(config, pcrs_hash, sys.argv[2], int(sys.argv[3]), sys.argv[4])
    server.start()

    while True:
        try:
            _ = input()
        except KeyboardInterrupt:
            server.kill()
            server.join()
            sys.exit(0)
