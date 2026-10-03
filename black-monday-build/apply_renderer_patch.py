#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply_renderer_patch.py <Play-source-root>')
root = Path(sys.argv[1]).resolve()
path = root / 'Source/ui_js/Main.cpp'
text = path.read_text()

anchor = '\nEMSCRIPTEN_BINDINGS(Play)\n{'
insert = '''\nvoid setGsResolutionFactor(unsigned int factor)\n{\n\tif(!g_virtualMachine) return;\n\tif((factor != 1) && (factor != 2) && (factor != 4) && (factor != 8)) return;\n\tCAppConfig::GetInstance().SetPreferenceInteger(PREF_CGSH_OPENGL_RESOLUTION_FACTOR, factor);\n\tauto gsHandler = g_virtualMachine->GetGSHandler();\n\tif(gsHandler) gsHandler->NotifyPreferencesChanged();\n}\n\nEMSCRIPTEN_BINDINGS(Play)\n{'''
if text.count(anchor) != 1:
    raise RuntimeError(f'Main.cpp: expected one bindings anchor, got {text.count(anchor)}')
text = text.replace(anchor, insert, 1)

old = '\tfunction("resumeVm", &resumeVm);\n}'
new = '\tfunction("resumeVm", &resumeVm);\n\tfunction("setGsResolutionFactor", &setGsResolutionFactor);\n}'
if text.count(old) != 1:
    raise RuntimeError(f'Main.cpp: expected one resume binding anchor, got {text.count(old)}')
text = text.replace(old, new, 1)
path.write_text(text)
print('BLACK_MONDAY_WEB timing-neutral GS resolution hook applied successfully.')
