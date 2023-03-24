import hashlib
import os
import csv
import re
import sys
import argparse
from datetime import datetime


def parse_time(time_str):
    time = re.search(r'(\d+(\.\d+)?)\s+(ms|sec|min|hrs)', time_str)
    if time:
        time = time.group(0)
        if time.endswith('ms'):
            time_ms = time.split()[0]
        elif time.endswith('sec'):
            time_ms = float(time.split()[0]) * 1000
        elif time.endswith('hrs'):
            time_ms = float(time.split()[0]) * 1000 * 60 * 60
        elif time.endswith('min'):
            time_ms = float(time.split()[0]) * 1000 * 60
        else:
            raise Exception('Unknown time unit')
        return float(time_ms) / 1000.0
    else:
        raise Exception('Could not parse time')


def parse_speed(speed_str):
    match = re.search(r'(\d+\.\d+)\s+mbit/s', speed_str)
    if match:
        return float(match.group(1))
    else:
        raise Exception('Could not parse speed')


def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def convert_size(size):
    if size > 1024 * 1024 * 1024:
        return size / (1024 * 1024 * 1024), 'GB'
    elif size > 1024 * 1024:
        return size / (1024 * 1024), 'MB'
    elif size > 1024:
        return size / 1024, 'KB'
    else:
        return size, 'bytes'


parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="path to log file")
args = parser.parse_args()

try:
    log_file = args.logfile
    num_files = 0
    total_size = 0
    total_time = 0
    total_speed = 0
    high_speed = 0
    errmsg = ''
    errcount = 0
    folder_path = ''
    found_first_I = False

    with open(log_file, 'r') as f:
        errmsg += '\n'
        for line in f:
            try:
                if line.startswith('I') and not found_first_I:
                    folder_path = os.path.dirname(line.split()[5])
                    source_path = os.path.dirname(line.split()[8])
                    found_first_I = True
                elif line.startswith('F'):
                    fields = line.split('\t')
                    if len(fields) < 11:
                        raise Exception('Invalid line format')
                    size_time_speed = fields[10]
                    file_size_str, rest = size_time_speed.split(' in ')
                    time_sec = parse_time(rest)
                    speed_mbps = parse_speed(size_time_speed)
                    total_speed += speed_mbps
                    total_time += time_sec
                    if speed_mbps > high_speed:
                        high_speed = speed_mbps
                elif line.startswith('W'):
                    errcount += 1
                    timestamp = line.split()[1] + ' ' + line.split()[2]
                    if errmsg:
                        errmsg += '\n'
                    errmsg += f"{timestamp}: {' '.join(line.split()[3:])}"

                else:
                    continue
            except Exception as e:
                errcount += 1
                timestamp = line.split()[1] + ' ' + line.split()[2]
                if errmsg:
                    errmsg += '\n'
                errmsg += f"{timestamp}: {' '.join(line.split()[3:])}"
    # use folder_path to get total number of files
    num_files = len(os.listdir(folder_path))
    total_size = get_folder_size(folder_path)
    avg_speed = total_speed / num_files if num_files > 0 else 0
    total_size, size_unit = convert_size(total_size)

    print(f"Total number of files: {num_files}")
    print(f"Total size of files (in {size_unit}): {total_size}")
    print(f"Total time taken (in seconds): {total_time}")
    print(f"Best speed (in Mbps): {high_speed}")
    print(f"Average speed (in Mbps): {avg_speed}")
    print(f"Destination Path: {folder_path}")
    print(f"Source Path: {source_path}")
    print()
    print(f'Error count: {errcount}' if errcount > 0 else '')
    print(f"Error Logs: {errmsg}" if errcount > 0 else '')
except Exception as e:
    print("An error occurred: {}".format(str(e)))
    sys.exit(1)
