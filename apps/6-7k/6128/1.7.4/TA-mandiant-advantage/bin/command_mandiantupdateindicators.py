import import_declare_test  # noqa: F401
import sys

from commands.mandiantupdateindicators import MandiantUpdateIndicators
from splunklib.searchcommands import dispatch

dispatch(MandiantUpdateIndicators, sys.argv, sys.stdin, sys.stdout, __name__)
