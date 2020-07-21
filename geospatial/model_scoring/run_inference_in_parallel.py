#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
''' Script for running an inference script in parallel over a list of inputs.

This assumes the inference script has the signature:
    `python inference.py [-h] --input_fn INPUT_FN --model_fn MODEL_FN --output_dir OUTPUT_DIR [--gpu GPU]`
and will iteratively run the specified model over the list of tile filenames specified in `--input_fn` and save
the results to `--output_dir`.

In this script we split the actual list of filenames we want to run on into NUM_GPUS different batches, save those batches to
file, and call `inference.py` multiple times in parallel - pointing it to a different batch each time.
'''
import sys
import os
from multiprocessing import Process

import numpy as np

GPUS = [0, 1, 2, 3] # list of IDs of the GPUs that we want to use
TEST_MODE = True # if False then just print out the commands to be run, if True then run those commands
MODEL_FN = 'models/xception_patches_7_14_2020.hdf5' # path passed to `--model_fn` in the `inference.py` script
OUTPUT_DIR = 'tmp/'  # path passed to `--output_dir` in the `inference.py` script

# -------------------
# Calculate the list of files we want our model to run on (currently we are looking up all NAIP 2017 imagery from Illinois)
# -------------------
fns = []
with open('data/naip_v002_index.csv', 'r') as f:
    for line in f:
        line = line.strip()
        if line != '':
            if line.endswith('.tif'):
                if '/il/' in line and '/2017/' in line:
                    fns.append(line)

# -------------------
# Split the list of files up into approximately equal sized batches based on the number of GPUs we want to use.
# Each worker will then work on NUM_FILES / NUM_GPUS files in parallel. Save these batches of the original list
# to disk (as a simple list of files to be consumed by the `inference.py` script)
# -------------------
num_files = len(fns)
num_splits = len(GPUS)
num_files_per_split = np.ceil(num_files / num_splits)

output_fns = []
for split_idx in range(num_splits):
    output_fn = 'data/runs/7_20_2020_split_%d.txt' % (split_idx)
    with open('data/runs/7_20_2020_split_%d.txt' % (split_idx), 'w') as f:
        start_range = int(split_idx * num_files_per_split)
        end_range = min(num_files, int((split_idx+1) * num_files_per_split))
        print('Split %d: %d files' % (split_idx+1, end_range-start_range))
        for i in range(start_range, end_range):
            end = '' if i == end_range-1 else '\n'
            f.write('%s%s' % (fns[i], end))
    output_fns.append(output_fn)


# -------------------
# Start NUM_GPUS worker processes, each pointed to one of the lists of files we saved to disk in the previous step.
# -------------------
def do_work(fn, gpu_idx):
    command = f'python inference.py --input_fn {fn} --model_fn {MODEL_FN} --output_dir {OUTPUT_DIR} --gpu {gpu_idx}'
    print(command)
    if not TEST_MODE:
        os.system(command)


processes = []
for work, gpu_idx in zip(output_fns, GPUS):
    p = Process(target=do_work, args=(work, gpu_idx))
    processes.append(p)
    p.start()
for p in processes:
    p.join()
