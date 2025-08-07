"""CLI script used for testing subprocess calls that should go to openflexure-stitch."""

import sys
import time


def main():
    """Echo command-line arguments with a short delay between each."""
    input_arguments = sys.argv[1:]
    for arg in input_arguments:
        # This is used to check we catch errors correctly.
        if arg == "ERROR":
            raise RuntimeError("I was told to do this.")
        print(arg, flush=True)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
