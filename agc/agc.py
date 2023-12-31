#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""OTU clustering"""

import argparse
import sys
import os
import gzip
import statistics
import textwrap
from pathlib import Path
from collections import Counter
from typing import Iterator, Dict, List
# https://github.com/briney/nwalign3
# ftp://ftp.ncbi.nih.gov/blast/matrices/
import nwalign3 as nw
import numpy as np
np.int = int

__author__ = "Roude JEAN MARIE"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Roude JEAN MARIE"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Roude JEAN MARIE"
__email__ = "roude.etu@gmail.com"
__status__ = "Developpement"



def isfile(path: str) -> Path:  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file does not exist

    :return: (Path) Path object of the input file
    """
    myfile = Path(path)
    if not myfile.is_file():
        if myfile.is_dir():
            msg = f"{myfile.name} is a directory."
        else:
            msg = f"{myfile.name} does not exist."
        raise argparse.ArgumentTypeError(msg)
    return myfile


def get_arguments(): # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', '-amplicon_file', dest='amplicon_file', type=isfile, required=True, 
                        help="Amplicon is a compressed fasta file (.fasta.gz)")
    parser.add_argument('-s', '-minseqlen', dest='minseqlen', type=int, default = 400,
                        help="Minimum sequence length for dereplication (default 400)")
    parser.add_argument('-m', '-mincount', dest='mincount', type=int, default = 10,
                        help="Minimum count for dereplication  (default 10)")
    parser.add_argument('-o', '-output_file', dest='output_file', type=Path,
                        default=Path("OTU.fasta"), help="Output file")
    return parser.parse_args()


def read_fasta(amplicon_file: Path, minseqlen: int) -> Iterator[str]:
    """Read a compressed fasta and extract all fasta sequences.

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length
    :return: A generator object that provides the Fasta sequences (str).
    """
    with gzip.open(amplicon_file, "rt") as fasta_in:
        iterator = iter(fasta_in)
        line = next(iterator, None)
        while(line):
            sequence = ""
            while(line[0] != ">"):
                sequence += line.strip()
                line = next(iterator, None)
                if line is None:
                    break
            line = next(iterator, None)
            if len(sequence) >= minseqlen:
                yield sequence


def dereplication_fulllength(amplicon_file: Path, minseqlen: int, mincount: int) -> Iterator[List]:
    """Dereplicate the set of sequence

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length
    :param mincount: (int) Minimum amplicon count
    :return: A generator object that provides a (list)[sequences, count] of sequence with a count >= mincount and a length >= minseqlen.
    """
    occ_dict = dict()
    for sequence in read_fasta(amplicon_file, minseqlen):
        occ_dict[sequence] = occ_dict.get(sequence, 0) + 1
    # Sorted dictionnary
    occ_dict = {key: value for key, value in occ_dict.items() if value >= mincount}
    for key, value in sorted(occ_dict.items(), key=lambda kv: kv[1], reverse=True):
        if value >= mincount:
            yield [key, value]

def get_identity(alignment_list: List[str]) -> float:
    """Compute the identity rate between two sequences

    :param alignment_list:  (list) A list of aligned sequences in the format ["SE-QUENCE1", "SE-QUENCE2"]
    :return: (float) The rate of identity between the two sequences.
    """
    count_same = 0
    for i, j in zip(alignment_list[0], alignment_list[1]):
        if i == j:
            count_same += 1
    return (count_same / len(alignment_list[0])) * 100

def abundance_greedy_clustering(amplicon_file: Path, minseqlen: int, mincount: int, chunk_size: int, kmer_size: int) -> List:
    """Compute an abundance greedy clustering regarding sequence count and identity.
    Identify OTU sequences.

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length.
    :param mincount: (int) Minimum amplicon count.
    :param chunk_size: (int) A fournir mais non utilise cette annee
    :param kmer_size: (int) A fournir mais non utilise cette annee
    :return: (list) A list of all the [OTU (str), count (int)] .
    """
    dereplication = list(dereplication_fulllength(amplicon_file, minseqlen, mincount))
    all_otu = [list(dereplication[0])]
    for sequence, count in dereplication[1:]:
        app = True
        for seq_j, count_j in all_otu:
            aligned_seq = nw.global_align(seq_j, sequence, gap_open=-1, gap_extend=-1,
                                         matrix=str(Path(__file__).parent / "MATCH"))
            if get_identity(aligned_seq) > 97:
                app = False
                break
        if app:
            all_otu.append([sequence, count])

    return all_otu

def write_OTU(OTU_list: List, output_file: Path) -> None:
    """Write the OTU sequence in fasta format.

    :param OTU_list: (list) A list of OTU sequences
    :param output_file: (Path) Path to the output file
    """
    write_str = ""
    for i, (sequence, count) in enumerate(OTU_list):
        write_str += f">OTU_{i+1} occurrence:{count}\n"
        write_str += textwrap.fill(sequence, width=80) + "\n"

    with open(output_file, "w") as out:
        out.write(write_str)


#==============================================================
# Main program
#==============================================================
def main(): # pragma: no cover
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    # Votre programme ici
    ALL_OTU = abundance_greedy_clustering(args.amplicon_file, args.minseqlen, args.mincount, 0, 0)
    write_OTU(ALL_OTU, args.output_file)


if __name__ == '__main__':
    main()
