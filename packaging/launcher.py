"""Native deployment entry; all workflow logic remains in the package."""

from load_research.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
