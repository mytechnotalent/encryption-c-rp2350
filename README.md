![encryption-c-rp2350](https://raw.githubusercontent.com/mytechnotalent/encryption-c-rp2350/main/encryption-c-rp2350.png)

## FREE Reverse Engineering Self-Study Course [HERE](https://github.com/mytechnotalent/encryption-c-rp2350)

<br>

# encryption-c-rp2350

`encryption-c-rp2350` is bare-metal Pico 2 firmware for hardened Ouroboros: 12-word lowercase passphrases, Argon2id/XChaCha20-Poly1305, and GPIO25/UART dispatch.

## Highlights

- RP2350 firmware build using the Pico SDK
- Strict 12-word lowercase passphrase policy
- Argon2id key derivation with generated artifact parameters
- XChaCha20-Poly1305 payload decryption
- GPIO25 LED control from payload byte `0`
- UART output from payload bytes `1..7`
- Host generator writes both JSON and generated firmware header

## Getting Started

Because `encryption-c-rp2350` is a bare-metal Pico SDK firmware project, you need the RP2350 toolchain installed on your system.

### 1. Install Toolchain Prerequisites

- Pico SDK 2.2.0+
- ARM GNU toolchain (`arm-none-eabi`)
- CMake and Ninja
- Python 3.x

**Linux:**

```bash
export PICO_SDK_PATH="$HOME/.pico-sdk/sdk/2.2.0"
```

**macOS:**

```bash
brew install cmake ninja arm-none-eabi-gcc python
export PICO_SDK_PATH="$HOME/.pico-sdk/sdk/2.2.0"
```

**Windows:**

Install PowerShell, Visual Studio Build Tools, CMake, Ninja, Python 3, and the ARM embedded toolchain. The provided build script configures the MSVC environment automatically.

### 2. Build the Firmware

```bash
mkdir -p build && cmake -S . -B build -G Ninja -DPICO_BOARD=pico2 -DPICO_PLATFORM=rp2350-arm-s && cmake --build build
```

Build-time artifact guardrail:

- The build regenerates `demo_artifact.h` from `scripts/demo_artifact.json` before compiling.
- The build fails if committed `include/demo_artifact.h` is stale relative to the JSON artifact.

Generated outputs:

- `build/encryption_app.elf`
- `build/encryption_app.uf2`

### 3. Flash the RP2350

**picotool:**

```bash
"$HOME/.pico-sdk/picotool/2.2.0-a4/picotool/picotool" load build/encryption_app.uf2 -f && "$HOME/.pico-sdk/picotool/2.2.0-a4/picotool/picotool" reboot
```

**BOOTSEL mode:**

```bash
cp build/encryption_app.uf2 /Volumes/RP2350/
```

### 4. Open the UART Demo

After flashing, connect a serial terminal at `115200` baud.

| Platform | Command |
| --- | --- |
| macOS | `screen /dev/tty.usbserial-* 115200` |
| Linux | `screen /dev/ttyACM0 115200` |
| Windows | PuTTY or another serial terminal |

The firmware prints a policy hint and then a `> ` prompt.

## Running the Demo

The RP2350 firmware enforces the same strict passphrase policy as the Rust hardened demo: Enter exactly 12 lowercase words under ASCII-whitespace normalization (spaces/tabs/newlines). Inputs like `hello`, empty lines, or non-policy strings are rejected with a policy hint.

Successful decrypt also requires that your input exactly matches the passphrase used to generate the current `scripts/demo_artifact.json` and `include/demo_artifact.h` pair.

If you generated the artifact with the default README command, enter this exact 12-word phrase:

```text
orbit olive ladder marble quartz canyon ripple saddle violet ember walnut falcon
```

On success:

- GPIO25 is driven high
- UART prints `hello` followed by CRLF

If the passphrase violates policy, the firmware prints:

```text
Enter exactly 12 lowercase words separated by spaces.
```

If your artifact was generated with a different passphrase, this phrase will return:

```text
Authentication failed.
```

Expected behavior summary:

```text
correct phrase for current artifact -> GPIO25 on + hello
wrong phrase for current artifact   -> Authentication failed.
```

## Hardened Construction

This firmware now implements the hardened Ouroboros construction:

- Argon2id key derivation
- 16-byte random salt
- 24-byte XChaCha20 nonce
- XChaCha20-Poly1305 authenticated decryption
- fixed 48-byte payload dispatch

The JSON artifact schema matches the Rust repo:

- `format`
- `memory_kib`
- `iterations`
- `parallelism`
- `salt_hex`
- `nonce_hex`
- `ciphertext_and_tag_hex`

Important: the RP2350 cannot run the Rust repo's 1 GiB desktop demo profile in SRAM. This repo uses the same algorithm and artifact shape, but the checked-in embedded profile is calibrated for the microcontroller:

- `memory_kib: 64`
- `iterations: 3`
- `parallelism: 1`

That is an implementation constraint of the hardware, not a change in the cryptographic construction.

## Generating Hardened Demo Artifacts

The `scripts/dec.py` script is hardened-only and writes both:

- `scripts/demo_artifact.json`
- `include/demo_artifact.h`

Why those byte arrays are compiled into firmware:

- RP2350 firmware has no runtime JSON parser/filesystem in this demo path.
- `include/demo_artifact.h` is generated from the JSON artifact so the exact salt, nonce, and ciphertext/tag bytes are embedded in flash.
- This is provisioned data, not hand-written cryptographic constants; regenerate with `scripts/dec.py` whenever rotating passphrase or payload.

Run it with a strict 12-word lowercase passphrase:

```bash
python3 scripts/dec.py --key "orbit olive ladder marble quartz canyon ripple saddle violet ember walnut falcon" --text "hello"
```

By default this updates the embedded JSON artifact and the generated firmware header directly (no manual copy/paste needed).

To sync the committed header from an existing JSON artifact without re-encrypting:

```bash
python3 scripts/dec.py --from-json scripts/demo_artifact.json --header-out include/demo_artifact.h
```

`dec.py` enforces the same passphrase policy as the firmware: exactly 12 lowercase words under ASCII-whitespace normalization.

If your local `.venv` has native-extension architecture mismatch errors (for example, `_cffi_backend` incompatible architecture), rebuild it first:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip setuptools wheel
python3 -m pip install argon2-cffi pynacl
```

Otherwise, install required Python packages first:

```bash
python3 -m pip install argon2-cffi pynacl
```

You can override the output paths if needed:

```bash
python3 scripts/dec.py --key "<12 lowercase words>" --text "hello" --out scripts/demo_artifact.json --header-out include/demo_artifact.h
```

Then rebuild and flash:

```bash
cmake -S . -B build -G Ninja -DPICO_BOARD=pico2 -DPICO_PLATFORM=rp2350-arm-s
cmake --build build
```

Payload layout is fixed:

- byte `0`: LED state (`1` on, `0` off)
- bytes `1..7`: UART output bytes

By default, `dec.py` appends CRLF (`\r\n`) to `--text`, so output must fit within 7 bytes after that append. Use `--no-crlf` to keep the full 7-byte capacity for raw text.

## Security Notes

The firmware does not contain a plaintext secret and does not bypass the entered phrase. To light GPIO25 and print the payload, an attacker still needs a passphrase that derives the correct key for the embedded artifact.

Implementation-accurate claim boundary:

- This demo enforces cryptographic gating in the intended firmware path (policy check + Argon2id + authenticated decryption before payload dispatch).
- This demo does not claim full side-channel resistance or fault-injection resistance.
- Branchless code alone is not sufficient to claim side-channel or fault resistance.

Scope boundary: claims here are limited to intended execution with unmodified firmware; firmware patching, instruction-level control, and active fault injection are out of scope.

The important variables are:

- passphrase entropy
- Argon2id work factor
- physical extraction and side-channel assumptions for the device

### Side-Channel and Fault Hardening Checklist

Use this checklist before making stronger claims than "cryptographically gated demo path":

- Enable secure boot / signed image verification so patched firmware cannot run.
- Lock debug/programming interfaces in production lifecycle states.
- Add voltage/clock/temperature glitch detection and safe-fail behavior.
- Use constant-time verification paths where applicable and avoid secret-dependent early exits.
- Add redundant checks or control-flow integrity for critical auth decisions.
- Minimize secret lifetime in RAM and verify compiler-retained zeroization.
- Perform hardware side-channel and fault-injection testing on target boards.
- Get third-party security review before claiming resistance properties.

### Quantum Threat Model

Short answer: **not in the strict post-quantum-cryptography (PQC) sense**.

- This framework does not implement a NIST PQC KEM or signature scheme.
- Security here is symmetric-key plus password-guessing cost.
- Against Grover-style brute force, symmetric search exponents are roughly halved.

So the right claim is: **high modeled brute-force cost under stated entropy and KDF assumptions**, not "quantum-proof."

### Crack-Time Math (Reference Row)

The hardened framework uses the same reference entropy row and the same classical versus optimistic Grover-style formulas as the Rust repo:

```text
T_avg_classical_years = 2^(H-1) / (r * 31,557,600)
T_avg_quantum_years   = 2^(H/2 - 1) / (r_q * 31,557,600)
```

For the 12-word Diceware policy reference row:

- `H ≈ 155.1`
- `r = 0.1/s`
- `r_q = 0.1/s`
- Classical: `~7.76e39 years`
- Quantum (optimistic Grover model): `~3.51e16 years`

Age-of-universe comparison (`≈ 1.38e10 years`):

- Classical ratio: `~5.6e29`
- Quantum ratio: `~2.5e6`

Important: those are the same paper-standard reference numbers used in the Rust repo. They are not a measured claim that the RP2350's checked-in `memory_kib: 64` profile has the same real-world per-guess cost as the Rust repo's 1 GiB desktop demo profile.

#### Reproducibility Snippet

```python
SECONDS_PER_YEAR = 365.25 * 24 * 3600

def avg_years_classical(H, r):
	return 2 ** (H - 1) / (r * SECONDS_PER_YEAR)

def avg_years_quantum(H, r_q):
	return 2 ** (H / 2 - 1) / (r_q * SECONDS_PER_YEAR)

print(avg_years_classical(155.1, 0.1))
print(avg_years_quantum(155.1, 0.1))
```

This project is a demonstrator firmware, not a third-party audited security product or formal security proof.

## Project Layout

- `src/main.c`: firmware entry point
- `src/cli.c`: UART prompt and passphrase handling
- `src/auth.c`: Argon2id + XChaCha20-Poly1305 authentication path
- `src/mbedtls_shims.c`: minimal zeroize shim for the AEAD subset
- `include/auth.h`: public auth API and constants
- `include/demo_artifact.h`: generated artifact header consumed by firmware
- `scripts/dec.py`: hardened artifact generator
- `scripts/demo_artifact.json`: JSON source-of-truth artifact
- `paper.typ`: hardened paper

<br>

## License

MIT — see [LICENSE](LICENSE).