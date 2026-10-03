#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply_savestate_patch.py <Play-source-root>')

root = Path(sys.argv[1]).resolve()
path = root / 'Source/ui_js/Main.cpp'
text = path.read_text()

old = '#include <cstdio>\n'
new = '#include <cstdio>\n#include <chrono>\n#include <future>\n'
if text.count(old) != 1:
    raise RuntimeError(f'Main.cpp: expected one cstdio include anchor, got {text.count(old)}')
text = text.replace(old, new, 1)

old = 'CSH_OpenAL* g_soundHandler = nullptr;\n'
new = 'CSH_OpenAL* g_soundHandler = nullptr;\nstd::future<bool> g_loadStateFuture;\nint g_loadStateResult = 0;\n'
if text.count(old) != 1:
    raise RuntimeError(f'Main.cpp: expected one sound handler anchor, got {text.count(old)}')
text = text.replace(old, new, 1)

anchor = '\nEMSCRIPTEN_BINDINGS(Play)\n{'
insert = '''\nbool saveState(unsigned int slot)\n{\n\tif(!g_virtualMachine) return false;\n\tauto stateFilePath = g_virtualMachine->GenerateStatePath(slot);\n\treturn g_virtualMachine->SaveState(stateFilePath).get();\n}\n\nbool beginLoadState(unsigned int slot)\n{\n\tif(!g_virtualMachine) return false;\n\tif(g_loadStateFuture.valid()) return false;\n\tg_loadStateResult = 0;\n\tauto stateFilePath = g_virtualMachine->GenerateStatePath(slot);\n\tg_loadStateFuture = g_virtualMachine->LoadState(stateFilePath);\n\treturn true;\n}\n\nint pollLoadState()\n{\n\tif(!g_loadStateFuture.valid()) return g_loadStateResult;\n\tif(g_loadStateFuture.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready) return 1;\n\tg_loadStateResult = g_loadStateFuture.get() ? 2 : -1;\n\treturn g_loadStateResult;\n}\n\nEMSCRIPTEN_BINDINGS(Play)\n{'''
if text.count(anchor) != 1:
    raise RuntimeError(f'Main.cpp: expected one bindings anchor, got {text.count(anchor)}')
text = text.replace(anchor, insert, 1)

old = '\tfunction("setGsResolutionFactor", &setGsResolutionFactor);\n}'
new = '\tfunction("setGsResolutionFactor", &setGsResolutionFactor);\n\tfunction("saveState", &saveState);\n\tfunction("beginLoadState", &beginLoadState);\n\tfunction("pollLoadState", &pollLoadState);\n}'
if text.count(old) != 1:
    raise RuntimeError(f'Main.cpp: expected one renderer binding anchor, got {text.count(old)}')
text = text.replace(old, new, 1)

path.write_text(text)
print('BLACK_MONDAY_WEB asynchronous browser savestate bridge applied successfully.')
