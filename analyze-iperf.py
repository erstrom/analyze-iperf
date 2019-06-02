#! /usr/bin/env python
#
# Script used to analyze the output from iperf (version2)
#
# Copyright (C) Erik Stromdahl <erik.stromdahl@gmail.com>

import re
import sys
import argparse

# example iperf line:
# [  3]  0.0- 1.0 sec  5.75 MBytes  48.2 Mbits/sec
iperf_regex_pattern = '.*\s+([0-9.]+)\s+(\w{0,1})bits/sec'

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

def calc_avg_bitrate(bitrate_sum, divisor):

    average_bitrate = bitrate_sum / divisor
    if average_bitrate / 1E9 >= 1.0:
        average_bitrate_prefix = 'G'
        average_bitrate /= 1E9
    elif average_bitrate / 1E6 >= 1.0:
        average_bitrate_prefix = 'M'
        average_bitrate /= 1E6
    elif average_bitrate / 1E3 >= 1.0:
        average_bitrate_prefix = 'k'
        average_bitrate /= 1E3
    else:
        average_bitrate_prefix = ''

    return (average_bitrate, average_bitrate_prefix)

def print_stats(outfp,
                bitrate_sum,
                matched_lines,
                nbr_of_zero_bitrate_lines,
                max_nbr_of_consecutive_zero_bitrate_lines,
                max_nbr_of_consecutive_zero_bitrate_end):

    (average_bitrate, average_bitrate_prefix) = \
        calc_avg_bitrate(bitrate_sum, matched_lines)
    (average_bitrate_no_zero, average_bitrate_prefix_no_zero) = \
        calc_avg_bitrate(bitrate_sum, matched_lines - nbr_of_zero_bitrate_lines)

    outfp.write("Statistics summary:\n\n".format(
        nbr_of_zero_bitrate_lines, matched_lines))
    outfp.write("Total number of zero drops: {} (out of {})\n\n".format(
        nbr_of_zero_bitrate_lines, matched_lines))
    outfp.write("Max len of zero drop burst: {} (ending at line {})\n\n".format(
        max_nbr_of_consecutive_zero_bitrate_lines,
        max_nbr_of_consecutive_zero_bitrate_end))
    outfp.write("+---------------+-------------------------------+\n")
    outfp.write("| Bitrate       | Bitrate (zero drops excluded) |\n")
    outfp.write("+---------------+-------------------------------+\n")
    outfp.write("| {:.2f} {:>1}bits/s | {:21.2f} {:>1}bits/s |\n".format(
        average_bitrate, average_bitrate_prefix,
        average_bitrate_no_zero, average_bitrate_prefix_no_zero))
    outfp.write("+---------------+-------------------------------+\n")

def main():

    global parsed_args
    iperf_regex = re.compile(iperf_regex_pattern)

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

        matched_lines = 0
        bitrate_sum = 0
        nbr_of_zero_bitrate_lines = 0
        nbr_of_consecutive_zero_bitrate_lines = 0
        max_nbr_of_consecutive_zero_bitrate_lines = 0
        for line in infp:
            match = iperf_regex.match(line)
            if match is None:
                continue

            bitrate = float(match.group(1))
            bitrate_prefix = match.group(2)

            if bitrate_prefix == 'G':
                bitrate_multiplier = 1E9
            elif bitrate_prefix == 'M':
                bitrate_multiplier = 1E6
            elif bitrate_prefix == 'k':
                bitrate_multiplier = 1E3
            else:
                bitrate_multiplier = 1
            matched_lines += 1
            bitrate_sum += bitrate * bitrate_multiplier

            # Special case: zero bitrate
            if nbr_of_consecutive_zero_bitrate_lines > \
                max_nbr_of_consecutive_zero_bitrate_lines:
                max_nbr_of_consecutive_zero_bitrate_lines = \
                    nbr_of_consecutive_zero_bitrate_lines
                max_nbr_of_consecutive_zero_bitrate_end = matched_lines
            if bitrate == 0:
                nbr_of_zero_bitrate_lines += 1
                nbr_of_consecutive_zero_bitrate_lines += 1
            else:
                nbr_of_consecutive_zero_bitrate_lines = 0

        print_stats(outfp,
                    bitrate_sum,
                    matched_lines,
                    nbr_of_zero_bitrate_lines,
                    max_nbr_of_consecutive_zero_bitrate_lines,
                    max_nbr_of_consecutive_zero_bitrate_end)

    except IOError as err:
        sys.stderr.write('{}\n'.format(err))

if __name__ == "__main__":
    main()
