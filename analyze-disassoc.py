#! /usr/bin/env python
#
# Script used to analyze the dmesg output for disassociations and
# re-associated to a wireless access point.
#
# A typical scenario looks like this:
#
# [ 1157.752107] wlan0: disassociated from 04:f0:21:2c:6c:e5 (Reason: 4=DISASSOC_DUE_TO_INACTIVITY)
# [ 1157.940929] wlan0: authenticate with 04:f0:21:2c:6c:e5
# [ 1157.990694] wlan0: send auth to 04:f0:21:2c:6c:e5 (try 1/3)
# [ 1157.999625] wlan0: authenticated
# [ 1158.010437] wlan0: associate with 04:f0:21:2c:6c:e5 (try 1/3)
# [ 1158.022205] wlan0: RX AssocResp from 04:f0:21:2c:6c:e5 (capab=0x421 status=0 aid=1)
# [ 1158.043526] wlan0: associated
#
# The above prints shows us that the station was disassociated from
# the AP at 1157.752107 and then re-associated at 1158.043526.
#
# The script will calculate the time the station was disconnected
# from the AP.
#
# In order for this script to work, the kernel must have timestamps
# for printks (CONFIG_PRINTK_TIME=y).
#
# Copyright (C) Erik Stromdahl <erik.stromdahl@gmail.com>

import re
import sys
import argparse

# example dmesg disassoc line:
# [ 4921.536527] wlan0: disassociated from 04:f0:21:2c:6c:e5 (Reason: 4=DISASSOC_DUE_TO_INACTIVITY)
disassoc_regex_pattern = '\[\s*([0-9.]+)\]\s+([a-zA-Z0-9]+)\: disassociated from.*'

# example dmesg deauth line:
# [ 3487.557109] wlan0: deauthenticated from 04:f0:21:2c:6c:e5 (Reason: 7=CLASS3_FRAME_FROM_NONASSOC_STA)
deauth_regex_pattern = '\[\s*([0-9.]+)\]\s+([a-zA-Z0-9]+)\: deauthenticated from.*'

# example dmesg reassoc line:
# [ 4921.802765] wlan0: associated
reassoc_regex_pattern = '\[\s*([0-9.]+)\]\s+([a-zA-Z0-9]+)\:\sassociated.*'

def load_options():

    global parsed_args
    parser = argparse.ArgumentParser(prog="analyze-iperf")

    parser.add_argument('-i', '--input-file',
                        help="Input file to analyze. If omitted, "
                             "stdin will be read")
    parser.add_argument('-o', '--output-file',
                        help="Statistics output file. If omitted, "
                             "the output will be written to stdout")

    parsed_args = parser.parse_args()

def main():

    global parsed_args
    disassoc_regex = re.compile(disassoc_regex_pattern)
    reassoc_regex = re.compile(reassoc_regex_pattern)
    deauth_regex = re.compile(deauth_regex_pattern)

    load_options()
    try:
        if parsed_args.input_file:
            infp = open(parsed_args.input_file, "r")
        else:
            infp = sys.stdin
        if parsed_args.output_file:
            outfp = open(parsed_args.output_file, "w")
        else:
            outfp = sys.stdout

        disassoc_time = {}
        reassoc_time = {}
        max_time_diff = 0
        for line in infp:
            match = disassoc_regex.match(line)
            if match is not None:
                interface = match.group(2)
                disassoc_time[interface] = float(match.group(1))
                continue

            match = deauth_regex.match(line)
            if match is not None:
                # Sometimes we get deauth's instead of disassoc's
                # We treat them in the same way (since a deauth also means
                # disassoc)
                interface = match.group(2)
                disassoc_time[interface] = float(match.group(1))
                sys.stderr.write("INFO: deauth instead of disassoc for {} @ {}\n".format(
                                 interface,
                                 disassoc_time[interface]))
                continue

            match = reassoc_regex.match(line)
            if match is not None:
                interface = match.group(2)
                reassoc_time[interface] = float(match.group(1))
                if not interface in disassoc_time:
                    sys.stderr.write("WARNING: reassoc without disassoc for {} @ {}\n".format(
                                     interface,
                                     reassoc_time[interface]))
                    continue
                time_diff = reassoc_time[interface] - disassoc_time[interface]
                if time_diff > max_time_diff:
                    max_time_diff = time_diff
                    max_time_diff_ts = reassoc_time[interface]
                outfp.write("[{:13.6f}] disassoc -> reassoc time for {}: {}\n".format(
                            disassoc_time[interface],
                            interface,
                            time_diff))
                disassoc_time.pop(interface, None)

        outfp.write("Max disassoc -> reassoc time for {}: {} (@ {})\n".format(
                    interface,
                    max_time_diff,
                    max_time_diff_ts))

    except IOError as err:
        sys.stderr.write('{}\n'.format(err))

if __name__ == "__main__":
    main()
