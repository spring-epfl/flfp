#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import json
import time
import re
import logging
import math

log = logging.getLogger('docker_stats')

data = {}
val = 1
count = 0



def run():
    global data
    global val
    while val == 1: 
        try:
            cmd = ["docker", "stats", "--no-stream"]
            run = subprocess.run(cmd, universal_newlines=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
            stdout = run.stdout
            stderr = run.stderr

            parse(stdout)
            # print(data)
            time.sleep(1.5)                
        except subprocess.CalledProcessError as e:
            log.error(f"Error collecting performance events: {e}")
        except KeyboardInterrupt:
            stop('docker_stats.json')

    return

def stop(fname):
    global data
    global val
    val = 0
    f = open(fname, "w")
    json.dump(data, f)
    f.close()
    return

def parse(stdout):
    global data
    global count
    # Parse RAM data
    print('-'*50)
    print('Count:', count)
    print('-'*50)
    lst = stdout.split('\n')

    if len(lst) == 2 and lst[1] == '':
        count += 1
        if count == 120:
            stop('docker_stats.json')

    if len(lst) > 2:
        for entry in lst[1:-1]:
            try:
                entry_lst = re.split("\s\s+", entry)
                if entry_lst[1] == '--' or '.' not in entry_lst[1].split("_")[1]:
                    count += 1
                    if count == 120:
                        stop('docker_stats.json')
                        return
                    continue

                ram = entry_lst[3].split(" / ")[0]
                if len(ram.split('KiB')) == 2:
                    ram = float(ram.split('KiB')[0])
                    ram = round(ram*math.pow(10,-3), 3)
                elif len(ram.split('MiB')) == 2:
                    ram = float(ram.split('MiB')[0])
                    ram = round(ram, 3)
                elif len(ram.split('GiB')) == 2:
                    ram = float(ram.split('GiB')[0])
                    ram = round(ram*math.pow(10, 3), 3)
                extn = entry_lst[1].split("_")[0]
                site = entry_lst[1].split("_")[1]
                count = 0                
                
                # print(data)
                if extn in data.keys():
                    # print(1)
                    if site in data[extn].keys():
                        # print(2)
                        data[extn][site].append(ram)
                    else:
                        # print(3)
                        data[extn][site] = [ram]
                else:
                    # print(4)
                    data[extn] = {site: [ram]}
            except Exception as e:
                print(e)
                continue
    return

run()

