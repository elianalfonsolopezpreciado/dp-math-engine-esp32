#include "benchmark_suite.h"
#include "uart_protocol.h"

extern "C" void app_main(void) {
    UartProtocol::init();
    UartProtocol::send_ready(BenchmarkSuite::FIRMWARE_NAME);

    char line[256];
    while (true) {
        if (!UartProtocol::read_line(line, sizeof(line), portMAX_DELAY)) {
            continue;
        }

        const UartProtocol::RunCommand cmd = UartProtocol::parse_run_command(line);
        if (cmd.valid) {
            BenchmarkSuite::run_benchmark_suite(cmd.seed, cmd.tests);
        }
    }
}
