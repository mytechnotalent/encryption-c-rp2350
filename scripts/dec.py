"""Generate hardened demo artifacts for the RP2350 Ouroboros firmware.

This script writes the same JSON schema used by the Rust demo and also emits
the generated C header consumed by the embedded firmware.
"""

import argparse
import json
from pathlib import Path
import platform
import secrets
import sys
from typing import Optional


DEFAULT_PASSPHRASE = (
    "orbit olive ladder marble quartz canyon "
    "ripple saddle violet ember walnut falcon"
)
DEFAULT_TEXT = "hello"
DEFAULT_OUTPUT_JSON = "scripts/demo_artifact.json"
DEFAULT_OUTPUT_HEADER = "include/demo_artifact.h"
DEFAULT_MEMORY_KIB = 64
DEFAULT_ITERATIONS = 3
DEFAULT_PARALLELISM = 1
ARTIFACT_FORMAT = "ouroboros-hardened-demo-v1"


def _raise_dependency_error(package_name, install_hint, exc):
    """Raise a RuntimeError with environment-aware dependency diagnostics."""
    detail = str(exc)
    message = f"Hardened mode requires {package_name}. Install with: {install_hint}"
    mismatch = (
        "incompatible architecture" in detail
        or "_cffi_backend" in detail
        or "mach-o file, but is an incompatible architecture" in detail
    )
    if mismatch:
        message += (
            "\nDetected a Python native-extension architecture mismatch. "
            f"Current interpreter reports machine={platform.machine()}, executable={sys.executable}."
            "\nRecreate this virtual environment with a native Python and reinstall deps:"
            "\n  rm -rf .venv"
            "\n  python3 -m venv .venv"
            "\n  source .venv/bin/activate"
            "\n  python3 -m pip install -U pip setuptools wheel"
            "\n  python3 -m pip install argon2-cffi pynacl"
        )
    raise RuntimeError(message) from exc


def _is_policy_compliant(passphrase):
    """Return True when passphrase is exactly 12 lowercase ASCII words."""
    words = passphrase.split()
    if len(words) != 12:
        return False
    return all(word and all(ch.isascii() and ch.islower() for ch in word) for word in words)


def _build_payload(text_str, led_on=True, append_crlf=True):
    """Build the fixed 48-byte payload dispatched by the firmware."""
    tx_bytes = text_str.encode() + (b"\r\n" if append_crlf else b"")
    if len(tx_bytes) > 7:
        raise ValueError("Output text is too long for fixed dispatch (max 7 bytes after CRLF handling).")
    payload = bytearray(48)
    payload[0] = 1 if led_on else 0
    payload[1:1 + len(tx_bytes)] = tx_bytes
    return bytes(payload)


def _derive_hardened_key(passphrase, salt, memory_kib, iterations, parallelism):
    """Derive a 32-byte key with Argon2id."""
    try:
        from argon2.low_level import Type, hash_secret_raw
    except ImportError as exc:
        _raise_dependency_error("argon2-cffi", "python3 -m pip install argon2-cffi", exc)
    return hash_secret_raw(
        secret=passphrase.encode(),
        salt=salt,
        time_cost=iterations,
        memory_cost=memory_kib,
        parallelism=parallelism,
        hash_len=32,
        type=Type.ID,
    )


def build_hardened_entry(
    key_str,
    text_str,
    led_on=True,
    append_crlf=True,
    salt: Optional[bytes] = None,
    nonce: Optional[bytes] = None,
    memory_kib=DEFAULT_MEMORY_KIB,
    iterations=DEFAULT_ITERATIONS,
    parallelism=DEFAULT_PARALLELISM,
):
    """Build a hardened encrypted entry with Argon2id + XChaCha20-Poly1305."""
    if not _is_policy_compliant(key_str):
        raise ValueError("Hardened mode requires exactly 12 lowercase ASCII words in --key.")
    try:
        from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_encrypt
    except ImportError as exc:
        _raise_dependency_error("PyNaCl", "python3 -m pip install pynacl", exc)
    payload = _build_payload(text_str, led_on=led_on, append_crlf=append_crlf)
    salt = secrets.token_bytes(16) if salt is None else salt
    nonce = secrets.token_bytes(24) if nonce is None else nonce
    if len(salt) != 16:
        raise ValueError("Hardened salt must be exactly 16 bytes.")
    if len(nonce) != 24:
        raise ValueError("Hardened nonce must be exactly 24 bytes.")
    key = _derive_hardened_key(key_str, salt, memory_kib, iterations, parallelism)
    ciphertext_and_tag = crypto_aead_xchacha20poly1305_ietf_encrypt(payload, b"", nonce, key)
    return salt, nonce, ciphertext_and_tag


def _hex_decode(value, expected_len, label):
    """Decode a hex string and validate expected byte length."""
    try:
        decoded = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be valid hex.") from exc
    if len(decoded) != expected_len:
        raise ValueError(f"{label} must decode to exactly {expected_len} bytes.")
    return decoded


def _write_demo_json(path, memory_kib, iterations, parallelism, salt, nonce, ciphertext_and_tag):
    """Write the hardened JSON artifact consumed by docs and validation."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "format": ARTIFACT_FORMAT,
        "memory_kib": memory_kib,
        "iterations": iterations,
        "parallelism": parallelism,
        "salt_hex": salt.hex(),
        "nonce_hex": nonce.hex(),
        "ciphertext_and_tag_hex": ciphertext_and_tag.hex(),
    }
    output_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return output_path.resolve(), artifact


def _format_c_array(data, width=8):
    """Format bytes as an indented C array literal body."""
    items = [f"0x{value:02X}u" for value in data]
    lines = []
    for index in range(0, len(items), width):
        lines.append("    " + ", ".join(items[index:index + width]))
    return ",\n".join(lines)


def _write_header(path, artifact):
    """Write the generated firmware header from the hardened artifact."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    salt = bytes.fromhex(artifact["salt_hex"])
    nonce = bytes.fromhex(artifact["nonce_hex"])
    ciphertext_and_tag = bytes.fromhex(artifact["ciphertext_and_tag_hex"])
    header = f'''// MIT License
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
// This file is generated by scripts/dec.py. Do not edit by hand.

#ifndef DEMO_ARTIFACT_H
#define DEMO_ARTIFACT_H

#include <stdint.h>

#define DEMO_ARTIFACT_FORMAT "{ARTIFACT_FORMAT}"
#define DEMO_MEMORY_KIB {artifact["memory_kib"]}u
#define DEMO_ITERATIONS {artifact["iterations"]}u
#define DEMO_PARALLELISM {artifact["parallelism"]}u

static const uint8_t DEMO_SALT[16] = {{
{_format_c_array(salt)}
}};

static const uint8_t DEMO_NONCE[24] = {{
{_format_c_array(nonce)}
}};

static const uint8_t DEMO_CIPHERTEXT_AND_TAG[64] = {{
{_format_c_array(ciphertext_and_tag)}
}};

#endif // DEMO_ARTIFACT_H
'''
    output_path.write_text(header, encoding="utf-8")
    return output_path.resolve()


def _load_artifact_json(path):
    """Load and validate a hardened artifact JSON for header generation."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Artifact JSON at {path} is invalid JSON.") from exc
    if parsed.get("format") != ARTIFACT_FORMAT:
        raise ValueError(
            f"Artifact format must be '{ARTIFACT_FORMAT}', got '{parsed.get('format')}'."
        )
    try:
        memory_kib = int(parsed["memory_kib"])
        iterations = int(parsed["iterations"])
        parallelism = int(parsed["parallelism"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Artifact must include integer memory_kib, iterations, and parallelism fields.") from exc
    salt = _hex_decode(parsed.get("salt_hex", ""), 16, "salt_hex")
    nonce = _hex_decode(parsed.get("nonce_hex", ""), 24, "nonce_hex")
    ciphertext_and_tag = _hex_decode(parsed.get("ciphertext_and_tag_hex", ""), 64, "ciphertext_and_tag_hex")
    return {
        "format": ARTIFACT_FORMAT,
        "memory_kib": memory_kib,
        "iterations": iterations,
        "parallelism": parallelism,
        "salt_hex": salt.hex(),
        "nonce_hex": nonce.hex(),
        "ciphertext_and_tag_hex": ciphertext_and_tag.hex(),
    }


def _check_header_match(generated_path, expected_path):
    """Fail when generated header does not exactly match an expected header file."""
    generated = Path(generated_path).read_text(encoding="utf-8")
    expected = Path(expected_path).read_text(encoding="utf-8")
    if generated != expected:
        raise RuntimeError(
            "Generated header does not match committed include/demo_artifact.h. "
            "Regenerate and commit updated artifacts with scripts/dec.py."
        )


def _parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", default=DEFAULT_PASSPHRASE, help="12-word lowercase passphrase")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Text to place in payload bytes 1..7")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_JSON, help="Output JSON artifact path")
    parser.add_argument("--header-out", default=DEFAULT_OUTPUT_HEADER, help="Output generated C header path")
    parser.add_argument("--from-json", help="Load existing JSON artifact and emit header without re-encrypting")
    parser.add_argument("--check-header-path", help="Optional path to compare against generated header and fail if stale")
    parser.add_argument("--memory-kib", type=int, default=DEFAULT_MEMORY_KIB, help="Argon2 memory cost in KiB")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="Argon2 time cost")
    parser.add_argument("--parallelism", type=int, default=DEFAULT_PARALLELISM, help="Argon2 parallel lanes")
    parser.add_argument("--salt-hex", help="Optional fixed 16-byte salt as hex")
    parser.add_argument("--nonce-hex", help="Optional fixed 24-byte nonce as hex")
    parser.add_argument("--no-crlf", action="store_true", help="Do not append CRLF to payload text")
    parser.add_argument("--led-off", action="store_true", help="Encode LED off instead of on")
    return parser.parse_args()


def main():
    """Generate the hardened artifact JSON and C header."""
    args = _parse_args()
    if args.from_json:
        artifact = _load_artifact_json(args.from_json)
        header_path = _write_header(args.header_out, artifact)
        print(f"Wrote generated firmware header: {header_path}")
        if args.check_header_path:
            _check_header_match(header_path, args.check_header_path)
            print(f"Verified header matches: {Path(args.check_header_path).resolve()}")
        return
    salt = _hex_decode(args.salt_hex, 16, "salt_hex") if args.salt_hex else None
    nonce = _hex_decode(args.nonce_hex, 24, "nonce_hex") if args.nonce_hex else None
    salt, nonce, ciphertext_and_tag = build_hardened_entry(
        key_str=args.key,
        text_str=args.text,
        led_on=not args.led_off,
        append_crlf=not args.no_crlf,
        salt=salt,
        nonce=nonce,
        memory_kib=args.memory_kib,
        iterations=args.iterations,
        parallelism=args.parallelism,
    )
    json_path, artifact = _write_demo_json(
        args.out,
        args.memory_kib,
        args.iterations,
        args.parallelism,
        salt,
        nonce,
        ciphertext_and_tag,
    )
    header_path = _write_header(args.header_out, artifact)
    print(f"Wrote hardened demo artifact JSON: {json_path}")
    print(f"Wrote generated firmware header: {header_path}")
    if args.check_header_path:
        _check_header_match(header_path, args.check_header_path)
        print(f"Verified header matches: {Path(args.check_header_path).resolve()}")


if __name__ == "__main__":
    main()