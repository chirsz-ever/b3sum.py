#!/usr/bin/env python3

import sys
import os
import argparse

enable_debug = os.environ.get('DEBUG')
enable_debug = enable_debug is not None and len(enable_debug) > 0

def debug(msg):
    if enable_debug:
        print(f'\033[34m[DEBUG]\033[0m {msg}')

IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]


def compress(h: list[int], m: list[int], t: int, b: int, d: int, truncate: bool) -> list[int]:
    """
    h: u32[8],
    m: u32[16],
    t: u64,
    b: u32,
    d: u32,
    return: u32[16]
    """

    debug(f'compress:')
    debug(f'  h:')
    debug(f'  {' '.join(f'{x:08x}' for x in h)}')
    debug(f'  m:')
    debug(f'  {' '.join(f'{x:08x}' for x in m[0:8])}')
    debug(f'  {' '.join(f'{x:08x}' for x in m[8:16])}')
    debug(f'  t: {t}')
    debug(f'  b: {b}')
    debug(f'  d: {d:02x}')

    v0, v1, v2, v3, v4, v5, v6, v7 = h
    v8,  v9,  v10, v11 = IV[0:4]
    v12, v13, v14, v15 = t & 0xffffffff, t >> 32, b, d

    v = [
        v0,  v1,  v2,  v3,
        v4,  v5,  v6,  v7,
        v8,  v9,  v10, v11,
        v12, v13, v14, v15,
    ]

    m = m[:]
    for i in range(7):
        if i != 0:
            round_permute(m)
        v = round_(m, v)
        debug(f'  after round {i}:')
        debug(f'  {' '.join(f'{x:08x}' for x in v[0:8])}')
        debug(f'  {' '.join(f'{x:08x}' for x in v[8:16])}')

    h_o = [v[i]^v[i+8] for i in range(8)]
    if not truncate:
        h_o += [v[i+8]^h[i] for i in range(8)]
    return h_o

def round_(m, v: list[int]) -> list[int]:
    # v = v[:]
    G(0, m, v, 0, 4, 8, 12)
    G(1, m, v, 1, 5, 9, 13)
    G(2, m, v, 2, 6, 10, 14)
    G(3, m, v, 3, 7, 11, 15)
    G(4, m, v, 0, 5, 10, 15)
    G(5, m, v, 1, 6, 11, 12)
    G(6, m, v, 2, 7, 8, 13)
    G(7, m, v, 3, 4, 9, 14)
    return v

def G(i: int, m: list[int], v: list[int], a: int, b: int, c: int, d: int):
    v[a] = (v[a] + v[b] + m[2 * i]) & 0xffffffff
    v[d] = rotate_r(v[d] ^ v[a], 16)
    v[c] = (v[c] + v[d]) & 0xffffffff
    v[b] = rotate_r(v[b] ^ v[c], 12)
    v[a] = (v[a] + v[b] + m[2 * i + 1]) & 0xffffffff
    v[d] = rotate_r(v[d] ^ v[a], 8)
    v[c] = (v[c] + v[d]) & 0xffffffff
    v[b] = rotate_r(v[b] ^ v[c], 7)

def rotate_r(x: int, n: int) -> int:
    return (x >> n) | ((x << (32 - n)) & 0xffffffff)

def round_permute(m: list[int]):
    m[0], m[2], m[3], m[10], m[12], m[9], m[11], m[5] = m[2], m[3], m[10], m[12], m[9], m[11], m[5], m[0]
    m[1], m[6], m[4], m[7], m[13], m[14], m[15], m[8] = m[6], m[4], m[7], m[13], m[14], m[15], m[8], m[1]

CHUNK_START = 1
CHUNK_END   = 2
PARENT      = 4
ROOT        = 8

class State:
    def __init__(self):
        self.cv_stack: list[list[int]] = []
        self.input_buffer: list[int] = []
        self.block_count = 0
        self.t = 0
        self.key = IV[0:8]

    def input_byte(self, b: int):
        if len(self.input_buffer) == 1024:
            new_cv = self.make_new_leave_cv()
            self.add_chunk_chaining_value(new_cv)
            self.input_buffer.clear()
            self.t += 1
        self.input_buffer.append(b)

    def make_new_leave_cv(self) -> list[int]:
        assert len(self.input_buffer) == 1024
        h = self.key
        for i in range(0, 1024, 64):
            block = self.input_buffer[i:i+64]
            b = 64
            d = 0
            if i == 0:
                d |= CHUNK_START
            if i + 64 >= 1024:
                d |= CHUNK_END
            m = split_message_block(block)
            h = compress(h, m, self.t, b, d, True)
        return h

    def add_chunk_chaining_value(self, new_cv: list[int]):
        total_chunks = self.t + 1
        while total_chunks & 1 == 0:
            new_cv = compress(self.key, self.cv_stack.pop() + new_cv, 0, 64, PARENT, True)
            total_chunks >>= 1
        self.cv_stack.append(new_cv)

    def finalize(self) -> list[int]:
        l = len(self.input_buffer)
        if l == 0:
            assert len(self.cv_stack) == 0
            return compress(self.key, [0]*16, self.t, 0, CHUNK_START|CHUNK_END|ROOT, True)

        h = self.key
        for i in range(0, l, 64):
            block = self.input_buffer[i:i+64]
            b = len(block)
            if b < 64:
                block += [0] * (64 - b)
            d = 0
            if i == 0:
                d |= CHUNK_START
            if i + 64 >= l:
                d |= CHUNK_END
                if len(self.cv_stack) == 0:
                    d |= ROOT
            m = split_message_block(block)
            h = compress(h, m, self.t, b, d, True)

        while len(self.cv_stack) != 0:
            cv = self.cv_stack.pop()
            d = PARENT
            if len(self.cv_stack) == 0:
                d |= ROOT
            h = compress(self.key, cv + h, 0, 64, d, True)
        return h

def run_hash(fname: str, input_bytes: bytes, bsd_format: bool):
    state = State()
    for b in input_bytes:
        state.input_byte(b)

    h = state.finalize()

    hashstr = format_hash(h)
    if bsd_format:
        print(f'BLAKE3 ({fname}) = {hashstr}')
    else:
        print(f'{hashstr}  {fname}')


def split_message_block(block: list[int]) -> list[int]:
    assert len(block) == 64
    return [int.from_bytes(block[i:i+4], 'little') for i in range(0, 64, 4)]

def format_hash(h: list[int]) -> str:
    return ''.join(f'{b:02x}' for n in h for b in n.to_bytes(4, 'little'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', action='store_true')
    parser.add_argument('inputs', nargs='*')
    args = parser.parse_args()

    bsd_format = args.tag

    if len(args.inputs) == 0:
        run_hash('-', sys.stdin.buffer.read(), bsd_format)
    else:
        for i in args.inputs:
            if i == '-':
                run_hash('-', sys.stdin.buffer.read(), bsd_format)
            else:
                run_hash(i, open(i, 'rb').read(), bsd_format)

main()
