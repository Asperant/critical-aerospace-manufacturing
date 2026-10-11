import sys

# Default commands do not create Python bytecode files either.
sys.dont_write_bytecode = True

from projectctl.cli import app

app()
