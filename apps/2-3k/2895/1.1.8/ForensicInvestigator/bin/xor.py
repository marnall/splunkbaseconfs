#!/usr/bin/python 
# XOR encoder/decoder
# For questions ask anlee2 -at- vt.edu 
# Takes a string and key to encode/decode
# Returns a encoded or decoded string

import sys,csv,splunk.Intersplunk,string

def xor(message, key):
    """
   Simple XOR cipher. Takes in a message and a key
   XORs the bits in the message with the characters in the key
   It cycles through the key if the message is longer than the key.
   EX:
   word: apple
   key: ba
   The encrypted message will be a^b, p^a, p^b, l^a, e^b (concatonated, though)
   """
    counter = 0
    length = len(key)
    cryptedMessage = ""
    for i in range(0, len(message)):
        cryptedMessage += chr(ord(message[counter]) ^ ord(key[counter % length]))
        counter += 1
    return cryptedMessage

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  result=xor(sys.argv[1],sys.argv[2])

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  datahex= [['answerhex'],[result.encode("hex")]]
  output.writerows(data)
  output.writerows(datahex)

main()

