#include <iomanip>
#include <iostream>

#include "dsp56kEmu/dsp.h"
#include "dsp56kEmu/dspconfig.h"
#include "dsp56kEmu/memory.h"
#include "dsp56kEmu/peripherals.h"

int main()
{
    using namespace dsp56k;

    if (g_jitSupported || g_useJIT)
    {
        std::cerr << "FAIL: WebAssembly build unexpectedly has JIT enabled\n";
        return 2;
    }

    DefaultMemoryValidator validator;
    Peripherals56362 peripheralsX;
    Peripherals56367 peripheralsY;
    Memory memory(validator, 0x080000, 0x800000, 0x200000);
    DSP dsp(memory, &peripheralsX, &peripheralsY);

    // Upstream assembler regression test establishes the short-immediate form:
    //   0x240000 = move #$00,x0
    //   0x24ff00 = move #$ff,x0
    // Therefore 0x245a00 is move #$5a,x0.
    constexpr TWord moveImmediate5aToX0 = 0x245a00;

    dsp.resetHW();
    dsp.setPC(0);
    if (!dsp.memWriteP(0, moveImmediate5aToX0))
    {
        std::cerr << "FAIL: could not write probe opcode into P memory\n";
        return 3;
    }

    // Use the normal dispatcher, not execInterpreter() directly. With the WASM
    // compile-time configuration this must select the real interpreter path.
    dsp.exec();

    TReg24 x0;
    if (!dsp.readReg(Reg_X0, x0))
    {
        std::cerr << "FAIL: could not read X0\n";
        return 4;
    }

    const auto value = x0.toWord();
    if (value != 0x5a)
    {
        std::cerr << "FAIL: X0=$" << std::hex << std::setw(6) << std::setfill('0')
                  << value << ", expected $00005a\n";
        return 5;
    }

    std::cout << "WASM_INTERPRETER_REGISTER_PROBE_OK X0=$00005a PC=$"
              << std::hex << std::setw(6) << std::setfill('0')
              << dsp.getPC().toWord() << "\n";
    return 0;
}
