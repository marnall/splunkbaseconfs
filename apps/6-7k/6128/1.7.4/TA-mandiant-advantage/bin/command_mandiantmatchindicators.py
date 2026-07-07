import import_declare_test  # noqa: F401
import sys

from commands.mandiantmatchindicators import MandianMatchIndicatorsCommand
from splunklib.searchcommands import dispatch

dispatch(MandianMatchIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
