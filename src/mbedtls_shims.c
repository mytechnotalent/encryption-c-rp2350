// MIT License
//
// Copyright (c) 2026 Kevin Thomas

#include "mbedtls/platform_util.h"

/**
 * @brief Securely clear a memory region.
 *
 * Provides the mbedTLS platform zeroization hook for this firmware build.
 * The volatile pointer prevents the compiler from optimizing away the
 * clearing loop.
 *
 * @param buf Pointer to mutable memory region to clear.
 * @param len Number of bytes to clear.
 * @return void
 */
void mbedtls_platform_zeroize(void *buf, size_t len)
{
    volatile unsigned char *ptr = (volatile unsigned char *)buf;
    while (len-- > 0u) {
        *ptr++ = 0u;
    }
}
