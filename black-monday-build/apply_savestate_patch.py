#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply_savestate_patch.py <Play-source-root>')

root = Path(sys.argv[1]).resolve()
path = root / 'Source/ui_js/Main.cpp'
text = path.read_text()

anchor = '\nEMSCRIPTEN_BINDINGS(Play)\n{'
insert = '''\nbool saveState(unsigned int slot)\n{\n\tif(!g_virtualMachine) return false;\n\tauto stateFilePath = g_virtualMachine->GenerateStatePath(slot);\n\treturn g_virtualMachine->SaveState(stateFilePath).get();\n}\n\nbool loadState(unsigned int slot)\n{\n\tif(!g_virtualMachine) return false;\n\tauto stateFilePath = g_virtualMachine->GenerateStatePath(slot);\n\treturn g_virtualMachine->LoadState(stateFilePath).get();\n}\n\nEMSCRIPTEN_BINDINGS(Play)\n{'''
if text.count(anchor) != 1:
    raise RuntimeError(f'Main.cpp: expected one bindings anchor, got {text.count(anchor)}')
text = text.replace(anchor, insert, 1)

old = '\tfunction("setGsResolutionFactor", &setGsResolutionFactor);\n}'
new = '\tfunction("setGsResolutionFactor", &setGsResolutionFactor);\n\tfunction("saveState", &saveState);\n\tfunction("loadState", &loadState);\n}'
if text.count(old) != 1:
    raise RuntimeError(f'Main.cpp: expected one renderer binding anchor, got {text.count(old)}')
text = text.replace(old, new, 1)

path.write_text(text)
print('BLACK_MONDAY_WEB browser savestate bridge applied successfully.')
