# Alert Manager Enterprise

This is the enterprise version of the alert manager by datapunctum.

# Setup Page

During the setup process, the platform administrator can setup the default tenant. This will create the fallback collection and index to send data to. Please make sure you have the capability to `admin_all_objects`, `edit_user`, `edit_roles` and `edit_roles_grantable` if you perform the initial setup.

# Binary File Declaration

For cryptographic operations, the enterprise version of the alert manager uses two proprietary go binaries. These binaries are compiled for Linux and Windows. The binaries are located in the `lib/datapunctum/bin` directory. Source code for these binaries is available for review upon request and a license agreement.

## Linux

- lib/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so
    - Source: `markupsafe` from https://pypi.org/project/MarkupSafe/1.1.1/
    - SHA512: markupsafe-37
- lib/markupsafe/_speedups.cpython-39-x86_64-linux-gnu.so
    - Source: `markupsafe` from https://pypi.org/project/MarkupSafe/1.1.1/
    - SHA512: markupsafe-39
- lib/pydantic_core/_pydantic_core.cpython-37m-x86_64-linux-gnu.so
    - Source: `pydantic-core` from https://pypi.org/project/pydantic-core/2.14.5/
    - SHA512: pydantic-core-37
- lib/pydantic_core/_pydantic_core.cpython-39-x86_64-linux-gnu.so
    - Source: `pydantic-core` from https://pypi.org/project/pydantic-core/2.14.5/
    - SHA512: pydantic-core-39
- bin/vsl
    - Source: proprietary library owned by Datapunctum
    - SHA512: dd09ed35892c37cd2fc05811e43c628f0152ffbcba7b86a8aa017dbc9e841ee889b98a25080734fe46925264ad01f65933dd726f7c4368697ea69aad91c326d1

## Windows

- lib/markupsafe/_speedups.cp37-win_amd64.pyd
    - Source: `markupsafe` from https://pypi.org/project/MarkupSafe/1.1.1/
    - SHA512: markupsafe-pyd37
- lib/markupsafe/_speedups.cp39-win_amd64.pyd
    - Source: `markupsafe` from https://pypi.org/project/MarkupSafe/1.1.1/
    - SHA512: 27dbaf19cf3231e015f7fe940055f71dab62a27eea04d4056af8439dc43d6cdf8a50e4daf65b3a2adbd2f4e5d890256c4621a6f4de875324f10fda0c9a4f3760
- lib/pydantic_core/_pydantic_core.pyd
    - Source: `pydantic-core` from https://pypi.org/project/pydantic-core/2.14.5/
    - SHA512: pydantic-core-pyd37
- lib/pydantic_core/_pydantic_core.cp39-win_amd64.pyd
    - Source: `pydantic-core` from https://pypi.org/project/pydantic-core/2.14.5/
    - SHA512: a6138b70771c2eec3c1c21436cad32359a7113bd468018dd18136fb40ac82e037203a99bbdf21240f7e3fbeed876ec51dc618c7dcf610a5a0ea545a88f7833e8
- bin/vsw.exe
    - Source: proprietary library owned by Datapunctum
    - SHA512: d049c6d13f884718522d27ad97f9c9afb9cdaa2c4db7604214b495f443fd7ad60083a6acbfe7fce14452a859af0d95647b2294173bc9f1f8b3c031457b65845b
