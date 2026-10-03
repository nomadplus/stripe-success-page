#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply_patches.py <Play-source-root>')
root = Path(sys.argv[1]).resolve()


def replace_once(rel, old, new):
    path = root / rel
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{rel}: expected exactly one match, got {count}: {old[:80]!r}')
    path.write_text(text.replace(old, new, 1))
    print(f'patched {rel}')

# Direct analogue/button injection.
replace_once(
    'Source/input/PH_GenericInput.h',
    '#pragma once\n\n#include "PadHandler.h"',
    '#pragma once\n\n#include <array>\n#include <atomic>\n#include "PadHandler.h"',
)
replace_once(
    'Source/input/PH_GenericInput.h',
    '\tCPH_GenericInput() = default;\n\tvirtual ~CPH_GenericInput() = default;\n\n\tvoid Update(uint8*) override;',
    '\tCPH_GenericInput();\n\tvirtual ~CPH_GenericInput() = default;\n\n\tvoid Update(uint8*) override;\n\tvoid SetDirectInputValue(uint32, PS2::CControllerInfo::BUTTON, uint32);\n\tvoid ClearDirectInputValue(uint32, PS2::CControllerInfo::BUTTON);\n\tvoid ClearDirectInputValues();',
)
replace_once(
    'Source/input/PH_GenericInput.h',
    'private:\n\tCInputBindingManager m_bindingManager;',
    'private:\n\tstatic constexpr uint32 DIRECT_INPUT_DISABLED = 0x100;\n\tstd::array<std::array<std::atomic<uint32>, PS2::CControllerInfo::MAX_BUTTONS>, CInputBindingManager::MAX_PADS> m_directInputValues;\n\tCInputBindingManager m_bindingManager;',
)
replace_once(
    'Source/input/PH_GenericInput.cpp',
    '#include <utility>\n\nvoid CPH_GenericInput::Update(uint8* ram)',
    '#include <utility>\n\nCPH_GenericInput::CPH_GenericInput()\n{\n\tClearDirectInputValues();\n}\n\nvoid CPH_GenericInput::Update(uint8* ram)',
)
replace_once(
    'Source/input/PH_GenericInput.cpp',
    '\t\t\t\tconst auto& binding = m_bindingManager.GetBinding(pad, button);\n\t\t\t\tif(!binding) continue;\n\t\t\t\tuint32 value = binding->GetValue();',
    '\t\t\t\tuint32 value = m_directInputValues[pad][buttonIdx].load(std::memory_order_relaxed);\n\t\t\t\tif(value == DIRECT_INPUT_DISABLED)\n\t\t\t\t{\n\t\t\t\t\tconst auto& binding = m_bindingManager.GetBinding(pad, button);\n\t\t\t\t\tif(!binding) continue;\n\t\t\t\t\tvalue = binding->GetValue();\n\t\t\t\t}',
)
replace_once(
    'Source/input/PH_GenericInput.cpp',
    '\nCInputBindingManager& CPH_GenericInput::GetBindingManager()\n{',
    '\nvoid CPH_GenericInput::SetDirectInputValue(uint32 pad, PS2::CControllerInfo::BUTTON button, uint32 value)\n{\n\tif(pad >= CInputBindingManager::MAX_PADS) return;\n\tif(button >= PS2::CControllerInfo::MAX_BUTTONS) return;\n\tif(value > 0xFF) value = 0xFF;\n\tm_directInputValues[pad][button].store(value, std::memory_order_relaxed);\n}\n\nvoid CPH_GenericInput::ClearDirectInputValue(uint32 pad, PS2::CControllerInfo::BUTTON button)\n{\n\tif(pad >= CInputBindingManager::MAX_PADS) return;\n\tif(button >= PS2::CControllerInfo::MAX_BUTTONS) return;\n\tm_directInputValues[pad][button].store(DIRECT_INPUT_DISABLED, std::memory_order_relaxed);\n}\n\nvoid CPH_GenericInput::ClearDirectInputValues()\n{\n\tfor(auto& pad : m_directInputValues)\n\t{\n\t\tfor(auto& value : pad) value.store(DIRECT_INPUT_DISABLED, std::memory_order_relaxed);\n\t}\n}\n\nCInputBindingManager& CPH_GenericInput::GetBindingManager()\n{',
)

# Browser host hooks. Insert in one block to avoid overlapping patch hunks.
replace_once(
    'Source/ui_js/Main.cpp',
    '\nEMSCRIPTEN_BINDINGS(Play)\n{',
    '''\nvoid setPadValue(unsigned int pad, unsigned int button, unsigned int value)\n{\n\tif(!g_virtualMachine) return;\n\tif(button >= PS2::CControllerInfo::MAX_BUTTONS) return;\n\tauto padHandler = static_cast<CPH_GenericInput*>(g_virtualMachine->GetPadHandler());\n\tif(!padHandler) return;\n\tpadHandler->SetDirectInputValue(pad, static_cast<PS2::CControllerInfo::BUTTON>(button), value);\n}\n\nvoid clearPadValue(unsigned int pad, unsigned int button)\n{\n\tif(!g_virtualMachine) return;\n\tif(button >= PS2::CControllerInfo::MAX_BUTTONS) return;\n\tauto padHandler = static_cast<CPH_GenericInput*>(g_virtualMachine->GetPadHandler());\n\tif(!padHandler) return;\n\tpadHandler->ClearDirectInputValue(pad, static_cast<PS2::CControllerInfo::BUTTON>(button));\n}\n\nvoid clearPadValues()\n{\n\tif(!g_virtualMachine) return;\n\tauto padHandler = static_cast<CPH_GenericInput*>(g_virtualMachine->GetPadHandler());\n\tif(padHandler) padHandler->ClearDirectInputValues();\n}\n\nvoid setEeFrequencyScale(unsigned int numerator, unsigned int denominator)\n{\n\tif(!g_virtualMachine) return;\n\tif((numerator == 0) || (denominator == 0)) return;\n\tg_virtualMachine->SetEeFrequencyScale(numerator, denominator);\n}\n\nvoid pauseVm()\n{\n\tif(g_virtualMachine) g_virtualMachine->Pause();\n}\n\nvoid resumeVm()\n{\n\tif(g_virtualMachine) g_virtualMachine->Resume();\n}\n\nEMSCRIPTEN_BINDINGS(Play)\n{''',
)
replace_once(
    'Source/ui_js/Main.cpp',
    '\tfunction("clearStats", &clearStats);\n}',
    '\tfunction("clearStats", &clearStats);\n\tfunction("setPadValue", &setPadValue);\n\tfunction("clearPadValue", &clearPadValue);\n\tfunction("clearPadValues", &clearPadValues);\n\tfunction("setEeFrequencyScale", &setEeFrequencyScale);\n\tfunction("pauseVm", &pauseVm);\n\tfunction("resumeVm", &resumeVm);\n}',
)

# Include Emscripten IDBFS so the host can mount persistent memory-card storage.
replace_once(
    'Source/ui_js/CMakeLists.txt',
    'target_link_options(Play PRIVATE "-sFORCE_FILESYSTEM")\n',
    'target_link_options(Play PRIVATE "-sFORCE_FILESYSTEM")\ntarget_link_options(Play PRIVATE "-lidbfs.js")\n',
)

print('BLACK_MONDAY_WEB Play! source transforms applied successfully.')
