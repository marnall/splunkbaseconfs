# -*- coding: utf-8 -*-

# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#                                                                                                                     //
#   Author: Juan Alejandro Perez Chadia                                                                               //
#   Date: July 25th, 2019                                                                                             //
#   Personal brand: JPEngineer                                                                                        //
#                                                                                                                     //
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

import os
import sys
import base64
import hashlib

_PACKAGE_ = os.getcwd() + '/packages'
sys.path.append(_PACKAGE_)


class AESCipher(object):

    def __init__(self, key):
        sys.path.append(_PACKAGE_)
        global AES
        global Random
        from Crypto.Cipher import AES
        from Crypto import Random

        try:
            self.bs = 32
            self.key = hashlib.sha256(key.encode()).digest()
        except Exception as error:
            print("Error A: ", error)

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        # iv = "Tn/wvw0X7CmW7Q=="
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


class VerifyConfig(object):

    def __init__(self):
        self.magic_word = ''
        self.internal_key = ''
        self.security = None
        self.config = {}

    def load(self, dictionary):
        self.magic_word = 'i_dont_remember_the_magic_word'
        self.internal_key = 'I_call_the_big_one_CUCA'
        self.config = dictionary

        def verify_encrypt():
            key = verify_key(self.config['key'])
            if self.config['encryption']:
                aes = AESCipher(str(key))
                self.config['consumer_key'] = aes.encrypt(self.config['consumer_key'])
                self.config['consumer_secret'] = aes.encrypt(self.config['consumer_secret'])
                self.config['access_token'] = aes.encrypt(self.config['access_token'])
                self.config['access_secret'] = aes.encrypt(self.config['access_secret'])
                self.config['status'] = 'encrypted'
                self.config['encryption'] = False
                self.config['key'] = key
            return self.config

        def verify_key(key):
            try:
                self.security = AESCipher(self.internal_key)
                a = self.security.decrypt(key)
                print a
                if self.magic_word in self.security.decrypt(key.encode()):
                    return key
                else:
                    return self.security.encrypt(self.magic_word + key)
            except:
                return self.security.encrypt(self.magic_word + key)

        self.config = verify_encrypt()
        return self.config
