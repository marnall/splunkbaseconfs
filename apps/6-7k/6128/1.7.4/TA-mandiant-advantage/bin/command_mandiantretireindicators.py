import import_declare_test  # noqa: F401
import sys

from commands.mandiantretireindicators import MandianRetireIndicatorsCommand
from splunklib.searchcommands import dispatch

dispatch(MandianRetireIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
