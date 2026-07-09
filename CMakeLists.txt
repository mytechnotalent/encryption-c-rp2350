# MIT License
#
# Copyright (c) 2026 Kevin Thomas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author:  Kevin Thomas
# Email:   kevin@mytechnotalent.com
# GitHub:  https://github.com/mytechnotalent/encryption-c-rp2350
# File:    CMakeLists.txt
# Desc:    Configures the RP2350 Pico SDK project and cryptographic module targets.
# Created: 2026

cmake_minimum_required(VERSION 3.13)

include(FetchContent)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(WIN32)
	set(USERHOME $ENV{USERPROFILE})
else()
	set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if(EXISTS ${picoVscode})
	include(${picoVscode})
endif()

set(PICO_BOARD pico2 CACHE STRING "Board type")

include(pico_sdk_import.cmake)
project(encryption_c_rp2350 C CXX ASM)
find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(DEMO_ARTIFACT_JSON ${CMAKE_CURRENT_LIST_DIR}/scripts/demo_artifact.json)
set(DEMO_ARTIFACT_HEADER_COMMITTED ${CMAKE_CURRENT_LIST_DIR}/include/demo_artifact.h)
set(DEMO_ARTIFACT_HEADER_GENERATED ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_artifact.h)

add_custom_command(
	OUTPUT ${DEMO_ARTIFACT_HEADER_GENERATED}
	COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_BINARY_DIR}/generated
	COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_LIST_DIR}/scripts/dec.py
			--from-json ${DEMO_ARTIFACT_JSON}
			--header-out ${DEMO_ARTIFACT_HEADER_GENERATED}
			--check-header-path ${DEMO_ARTIFACT_HEADER_COMMITTED}
	DEPENDS
		${CMAKE_CURRENT_LIST_DIR}/scripts/dec.py
		${DEMO_ARTIFACT_JSON}
		${DEMO_ARTIFACT_HEADER_COMMITTED}
	COMMENT "Regenerating demo artifact header from JSON and checking committed header freshness"
	VERBATIM
)

add_custom_target(check_demo_artifact_header DEPENDS ${DEMO_ARTIFACT_HEADER_GENERATED})

FetchContent_Declare(
	argon2_ref
	GIT_REPOSITORY https://github.com/P-H-C/phc-winner-argon2.git
	GIT_TAG master
)
FetchContent_GetProperties(argon2_ref)
if(NOT argon2_ref_POPULATED)
	FetchContent_Populate(argon2_ref)
endif()

pico_sdk_init()

add_library(argon2_ref STATIC
	${argon2_ref_SOURCE_DIR}/src/argon2.c
	${argon2_ref_SOURCE_DIR}/src/core.c
	${argon2_ref_SOURCE_DIR}/src/ref.c
	${argon2_ref_SOURCE_DIR}/src/encoding.c
	${argon2_ref_SOURCE_DIR}/src/blake2/blake2b.c
)
target_compile_definitions(argon2_ref PUBLIC ARGON2_NO_THREADS)
target_include_directories(argon2_ref PUBLIC
	${argon2_ref_SOURCE_DIR}/include
	${argon2_ref_SOURCE_DIR}/src
)

add_library(mbedtls_subset STATIC
	${PICO_MBEDTLS_PATH}/library/chacha20.c
	${PICO_MBEDTLS_PATH}/library/poly1305.c
	${PICO_MBEDTLS_PATH}/library/chachapoly.c
	${PICO_MBEDTLS_PATH}/library/constant_time.c
	src/mbedtls_shims.c
)
target_compile_definitions(mbedtls_subset PUBLIC MBEDTLS_CONFIG_FILE="mbedtls_config.h")
target_include_directories(mbedtls_subset PUBLIC
	include
	${PICO_MBEDTLS_PATH}/include
	${PICO_MBEDTLS_PATH}/library
)

add_library(auth STATIC src/auth.c)
add_dependencies(auth check_demo_artifact_header)
target_include_directories(auth PUBLIC
	${CMAKE_CURRENT_BINARY_DIR}/generated
	include
)
target_link_libraries(auth PUBLIC pico_stdlib mbedtls_subset argon2_ref)
add_executable(encryption_app src/main.c src/cli.c)
target_link_libraries(encryption_app PRIVATE auth pico_stdlib)
pico_enable_stdio_uart(encryption_app 0)
pico_enable_stdio_usb(encryption_app 1)
pico_add_extra_outputs(encryption_app)
