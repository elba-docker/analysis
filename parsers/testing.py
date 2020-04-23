import tarfile
import os
import platform
import sys
import numpy as np
from dateutil import parser
from collections import OrderedDict
from more_itertools import peekable
import glob, json, csv, argparse
from csv import Error
import re
from decimal import Decimal
import gzip
from glob import glob


import nbench_parser
import radvisor_parser
import moby_parser
import config_parser
import cpu
import disk
import mem
import milliscope_parser
import head_parser

# print(head_parser.getListOfFiles('results/256896565/results/17041182/conf'))

# def config(root):
#     listoffiles = head_parser.getListOfFiles("root")

#     if (len(listoffiles) == 0):
#         return {}

#     confdict = {}
#     for i in listoffiles:
#         with open(i, 'r') as file:
#             print(i)
#             confdict[i] = config_parser.main(iter(file))
#     return confdict

# config('results/256896565/results/17041182/conf')
# path_to_file = 'results/ii-rc-s (1).tar.gz'
root = 'results'
# time = head_parser.creation_date(path_to_file)
# if not os.path.exists('./results/' + str(time)):
#     print("worked")
# print(os.path.exists('./results/' + str(time)))
listoffiles = [f for f in os.listdir(root) if f.endswith('.gz')]
for i in listoffiles:
    print(i)
# for i in listoffiles:
#     print(typeof(i))
# print(listoffiles)