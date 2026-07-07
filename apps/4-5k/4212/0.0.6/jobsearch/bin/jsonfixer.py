#!/usr/bin/python3

""" json fixer utility, this is pretty hacky but pretty robust... """

import json
import sys
import time

def jsonfixer(text: str, depth: int=0, debug: bool=False, debug_write_files: bool=False):
    """ tries to fix broken JSON
        uses json.loads and grabs the exception, looking for broken things.
        
        will only go a bunch of levels deep and bail if that doesn't work it'll give up and return False
        
        returns a dict or False
        """
    if depth > 50:
        raise ValueError("Depth too high!")
    try:
        data = json.loads(text)
        return data
    except json.JSONDecodeError as exception_data:
        if debug_write_files:
            with open(f"/tmp/jsonfixer-errordata-{int(time.time())}.json", 'w') as fh:
                fh.write(text)
        if debug:
            print(exception_data, file=sys.stderr)
        # iterate backwards from the error position to try and fix it
        
        # for some things you need to go back further to start with, to avoid other issues 
        # quotes are a big one - if you've got two quote marks in a row and the second one's 
        # the end of a string, but the first one's the unescaped thing, you don't want to replace
        # the "error causing" one
        min_iterate_range = 0 
        
        if "escape" in exception_data.msg:
            string_to_replace = '\\'
            string_replacement = ""
        elif "Expecting ',' delimiter" in exception_data.msg:
            min_iterate_range = 1
            string_to_replace = '"'
            string_replacement = '\\"'
        else:
            print(f"Unhandled exception in jsonfixer: {exception_data}", file=sys.stderr)
            print(text, file=sys.stderr)
            print(f"Error was at pos: {exception_data.pos}, character was '{text[exception_data.pos]}'", file=sys.stderr)
            print(f"Slice at -2:+2: '{text[(exception_data.pos-2):(exception_data.pos+2)]}'")
            string_to_replace = '"'
            string_replacement = '\\"'
            sys.exit()

        for i in range(min_iterate_range,10):
            if text[exception_data.pos-i] == string_to_replace:
                if debug:
                    print(f"found {string_to_replace} at {exception_data.pos-i}", file=sys.stderr)
                string_front_end = exception_data.pos - i
                string_back_start = exception_data.pos - i + 1
                newstring = text[:string_front_end] + string_replacement + text[string_back_start:]
                if debug:
                    print(f"Updated text:\n{newstring}", file=sys.stderr)
                return jsonfixer(newstring, depth+1, debug)
        if debug:
            print(f"Message: {exception_data.msg} position='{exception_data.pos}' text_two_chars_either_side='{text[exception_data.pos-2:exception_data.pos+2]}'", file=sys.stderr)
        return False

if __name__ == '__main__':
    print("This probably isn't the script you're looking for...")