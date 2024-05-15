"""Module primarly intended to be imported by tests.

It defines some directories and some utility functions that can be used
with or without conftest.
"""

from pathlib import Path

testdir = Path(__file__).resolve().parent
rootdir = testdir.parent
indir = testdir / "input"
outdir = testdir / "output"
