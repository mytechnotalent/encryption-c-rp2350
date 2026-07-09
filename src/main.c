// MIT License
//
// Copyright (c) 2026 Kevin Thomas
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
//
// Author:  Kevin Thomas
// Email:   kevin@mytechnotalent.com
// GitHub:  https://github.com/mytechnotalent/encryption-c-rp2350
// File:    main.c
// Desc:    RP2350 firmware entry point with Ouroboros authentication over UART.
// Created: 2026

#include "auth.h"
#include "cli.h"
#include "pico/stdlib.h"

/**
 * @brief Maximum number of passphrase characters accepted from UART.
 *
 * Must match the hardened passphrase boundary declared in auth.h so the
 * CLI buffer can hold a full 12-word terminal phrase safely.
 */
#define PASS_BUF_LEN AUTH_PASSPHRASE_MAX_LEN

/**
 * @brief Run the RP2350 UART authentication loop.
 *
 * Initializes stdio and the hardened auth module, prints the interactive
 * prompt, then continuously services UART input for passphrase attempts.
 *
 * @param void No parameters.
 * @return int Process exit code (never returns during normal operation).
 */
int main(void)
{
    char buf[PASS_BUF_LEN];
    size_t idx = 0u;
    stdio_init_all();
    auth_init();
    print_prompt();
    while (true) {
        service_uart(buf, &idx);
    }
}
