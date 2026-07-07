import import_declare_test  # noqa: F401
import sys

from commands.mandiantretirevulns import MandianRetireVulnsCommand
from splunklib.searchcommands import dispatch

dispatch(MandianRetireVulnsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
