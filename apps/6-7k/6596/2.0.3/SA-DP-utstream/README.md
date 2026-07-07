# UTStream

Welcome to UTStream a Splunk app by Datapunctum AG.<br>
This is version 2.0.3 released 2023-6-28.

Please see the documentation for help and contact information: @DOCLINK@.

Happy Replaying data from the past!

## Binary File Declaration

For cryptographic operations, UTStream uses the `pynacl` and `cffi` library. Furtherfore there are some compiled libraries by Datapunctum. UTStream ships with the following binaries:

## Linux

- lib/_cffi_backend.cpython-37m-x86_64-linux-gnu.so
    - Source: `cffi` from https://pypi.org/project/cffi/1.15.1/
    - SHA512: 7368f1cf892d908015ca7d0137aa7ac70a7a674b68367b09ac7f0960ae89fd4ad50b2330fac6123fc984574b059e85019f0558b9f197b147f7b9abc27fdf2fe7
- lib/nacl/_sodium.abi3.so
    - Source: `pynacl` from https://pypi.org/project/PyNaCl/1.5.0/
    - SHA512: f595fef7fe202c90151d7968723eb74ca2bc4cc4215c9d5f518542b44cffcfe2a091cba6d4e731bf61c03ac0935a5aa352a6e8eeb29a80d9fb6226396400d526
- lib/utstream_template/helper_license_validation.cpython-37m-x86_64-linux-gnu.so
    - Source: proprietary library owned by Datapunctum
    - SHA512: this file is generated during the build process - no static hash available

## Windows
- lib/utstream_template/python3.dll
    - Source: `python3.dll` from https://anaconda.org/anaconda/python/3.7.11/download/win-64/python-3.7.11-h6244533_0.tar.bz2
    - SHA512: 5d3605efa9c87d8610f79de3a195911b7fe49ad7c042282b33e58009dd744ff175746175e9abee57706340cf643c593786ffbc8e2f2411578e433abb5bf37cfd
- lib/nacl/python3.dll
    - Source: `python3.dll` from https://anaconda.org/anaconda/python/3.7.11/download/win-64/python-3.7.11-h6244533_0.tar.bz2
    - SHA512: 5d3605efa9c87d8610f79de3a195911b7fe49ad7c042282b33e58009dd744ff175746175e9abee57706340cf643c593786ffbc8e2f2411578e433abb5bf37cfd
- lib/_cffi_backend.cp37-win_amd64.pyd
    - Source: `cffi` from https://pypi.org/project/cffi/1.15.1/
    - SHA512: 99fd5c80372d878f722e4bcb1b8c8c737600961d3a9dffc3e8277e024aaac8648c64825820e20da1ab9ad9180501218c6d796af1905d8845d41c6dbb4c6ebab0
- lib/nacl/_sodium.pyd
    - Source: `pynacl` from https://pypi.org/project/PyNaCl/1.5.0/
    - SHA512: 49e7f6ab825d5047421641ed4618ff6cb2a8d22a8a4ae1bd8f2deefe7987d80c8e0acc72b950d02214f7b41dc4a42df73a7f5742ebc96670d1c5a28c47b97355
- lib/utstream_template/helper_license_validation.cp37-win_amd64.pyd
    - Source: proprietary library owned by Datapunctum
    - SHA512: 8068aae0c8fc0642cb32d852c348357df08af29b887d044ccb75cc77395a66d82e68aeab873e1177969e6250b0cf6fb78be2f8244f66db2b4ab386cc873b7e56