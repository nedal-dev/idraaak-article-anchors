# Test coverage

`test_anchors.py` checks 46 static HTML fragment scenarios and source positions.
`test_worker.py` checks six worker cases, including real subprocess I/O, byte columns, bad input and resource limits.
`test_vim.vim` runs 16 assertions inside a clean native Vim session, using the real bundled Python worker.

Set `IDRAAAK_TEST_PYTHON` to a Python 3.8+ executable before running Vim. In an MSYS environment use its `/c/...` path syntax; in native Windows use `C:/...`. The JSON results and Python bytecode are ignored by git and excluded from release ZIPs.

Verified on 6 October 2026 with Python 3.12: all 52 Python tests passed.
All 16 integration assertions passed in both native Windows Vim 9.2.1167
and MSYS Vim 9.2.1-357. These were clean sessions using `-Nu NONE -i NONE -n -es`.
Python files also passed a Python 3.8 syntax compatibility check; Python 3.8
runtime and Vim 8.2 runtime were not available for an execution test.
