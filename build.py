"""Run python build.py --help for collection build commands."""
import sys
sys.dont_write_bytecode = True
from scripts.build import main

if __name__ == "__main__":
    raise SystemExit(main())
