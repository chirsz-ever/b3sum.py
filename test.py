#!/usr/bin/env python3

import json
from itertools import cycle, islice
import subprocess
import sys

# from https://github.com/BLAKE3-team/BLAKE3/blob/master/test_vectors/test_vectors.json
with open('test_vectors.json', 'r') as f:
    test_vectors = json.load(f)

for case in test_vectors['cases']:
    input_len = case['input_len']
    hash_ = case['hash']
    input_data = bytes(islice(cycle(range(0, 251)), input_len))
    hash_len_in_bytes = str(len(hash_) // 2)
    proc = subprocess.run(['./b3sum.py', '-l', hash_len_in_bytes], input=input_data, capture_output=True, check=True)
    h1 = proc.stdout.decode('utf-8').split()[0]
    if h1 != hash_:
        print(f"Test failed for length {input_len}:\nexpected\n  {hash_}\ngot\n  {h1}", file=sys.stderr)
