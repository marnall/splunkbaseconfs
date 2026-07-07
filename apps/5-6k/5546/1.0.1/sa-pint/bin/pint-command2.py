#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Splunk specific dependencies
import sys, os
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators, splunklib_logger as logger

# Command specific dependencies
from pint import UnitRegistry

ureg = UnitRegistry()
ureg.auto_reduce_dimensions = True
ureg.autoconvert_offset_to_baseunit = True


#functions
"""
def convert(u_from, u_to=None, unc=None, factor=None):
    q = ureg.Quantity(u_from)
    fmt = ".{}g".format(args.prec)
    #if unc:
    #    q = q.plus_minus(unc)
    if u_to:
        nq = q.to(u_to)
    else:
        nq = q.to_base_units()
    if factor:
        q *= ureg.Quantity(factor)
        nq *= ureg.Quantity(factor).to_base_units()
    prec_unc = use_unc(nq.magnitude, fmt, args.prec_unc)
    if prec_unc > 0:
        fmt = ".{}uS".format(prec_unc)
    else:
        try:
            nq = nq.magnitude.n * nq.units
        except Exception:
            pass
    return nq.magnitude
"""

#handler
@Configuration()
class pintCommand2(StreamingCommand):
  #examples
  #url        = Option(require=True)
  #paramMap   = Option(require=False)
  inputField  = Option(require=True)
  fromUnitField = Option(require=True)
  toUnitField = Option(require=True)
  outputField = Option(require=True)
  debugOutput = Option(require=False, default='False')
  
  def stream(self, records):
    inputField  = self.inputField
    fromUnitField = self.fromUnitField
    toUnitField = self.toUnitField
    outputField = self.outputField
    debugOutput = self.debugOutput

    for record in records:
      if record[inputField]:
        try:
            #record[outputField] = record[inputField]
            q = ureg.Quantity
            q = q(float(record[inputField]),record[fromUnitField])
            nq = q.to(record[toUnitField])
            record[outputField] = str(nq.magnitude)
            if debugOutput == "True":
                record["units"] = str(nq.units)
                record["sourceQuantity"] = str(q)
                record["sourceMagnitude"] = str(q.magnitude)
                record["sourceUnits"] = str(q.units)
                record["sourceBaseUnits"] = q.to_base_units()
        except:
            pass
      else:
         record[outputField] = "test2"

      yield record

dispatch(pintCommand2, sys.argv, sys.stdin, sys.stdout, __name__)