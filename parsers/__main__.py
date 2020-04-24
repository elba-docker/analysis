
import argparse
from parsers import parse_all

DESCRIPTION = "Script to parse rAdvisor container stat logs"

def main():
    """
    [CLI-only] Configures argparse
    """

    parser = argparse.ArgumentParser(description=DESCRIPTION, prog="python -m parsers")
    parser.add_argument("--root", "-r", metavar="path",
                        help="the path to find log files in (defaults to current directory)")
    parser.add_argument("--working", "-w", metavar="path",
                        help="the path to extract archives to (defaults to ./working)")

    parsed_args = parser.parse_args()
    parse_all(root=parsed_args.root, working_dir=parsed_args.working)

main()
