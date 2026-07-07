from pathlib import Path
from sys import path
import platform


lib_folder = Path(__file__).parent.parent / "lib"
path.insert(0, str(lib_folder))


# Add platform-specific pydantic_core wheel
system = platform.system().lower()
machine = platform.machine().lower()
platform_lib = lib_folder / "pydantic_core_wheels" / f"{system}_{machine}"
path.insert(0, str(platform_lib))

# Check pydantic_core is installed, and install if necessary.
try:
    from pydantic_core import __version__ as __pydantic_core_version__
except ModuleNotFoundError:
    raise RuntimeError(f"[TA-code42-insider-threats-add-on] Unable to locate compatible pydantic-core install in {platform_lib}")