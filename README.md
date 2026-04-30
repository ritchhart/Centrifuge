# Centrifuge Mixed Python/C++ Project

A starter workspace for a mixed Python and C++ project that builds a shared library (`DLL`/`SO`/`DYLIB`) and exposes it to Python.

## Features

- C++ shared library built with CMake
- Python package that loads the compiled library using `ctypes`
- Git-ready structure with `.gitignore`
- VS Code tasks for build and test
- Unit test example using Python `unittest`

## Requirements

- Python 3.8+
- CMake 3.15+
- A C++ compiler toolchain for your platform

## Build

1. Create a build directory:

   ```bash
   cmake -S . -B build
   ```

2. Build the shared library:

   ```bash
   cmake --build build
   ```

On Windows this produces `centrifuge.dll` in the package folder. On Linux/macOS this produces the shared library in the package folder as well.

## Run

After building, run Python directly:

```bash
python -c "import centrifuge; print(centrifuge.hello()); print(centrifuge.add(3, 4))"
```

## Test

```bash
python -m unittest discover -s tests
```

## VS Code Tasks

- `Build C++ library`
- `Run Python tests`

## Notes

The Python package is in `centrifuge/`, and it loads the compiled native library automatically from the package directory.
