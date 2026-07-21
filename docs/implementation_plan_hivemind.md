# Hivemind Edge Proxy & Bit-Validation Rules Implementation Plan

Implement the **Hivemind Edge Proxy** binary protocol, 128-byte fixed binary frame layout parser & generator, bit-validation rules, Rust struct definition, and heartbeat integration in Clew.

## User Review Required

> [!IMPORTANT]
> - **128-Byte Binary Frame Layout**:
>   - Bytes `0x00 - 0x03`: Magic (`0x48 0x49 0x56 0x45` = `"HIVE"`).
>   - Byte `0x04`: Version (`0x01`).
>   - Byte `0x05`: Message Type (`0x01` Delta, `0x02` Heartbeat, `0x03` Sync).
>   - Bytes `0x06 - 0x07`: Flags (`u16` bitfield: Bit 0 = Encrypted, Bit 1 = Compressed).
>   - Bytes `0x08 - 0x0F`: Sequence Nonce (`u64` monotonic anti-replay nonce).
>   - Bytes `0x10 - 0x17`: HLC Timestamp (`u64` physical epoch timestamp in ms).
>   - Bytes `0x18 - 0x1B`: Payload Length (`u32` with a strict 16MB / 16,777,216 bytes ceiling).
>   - Bytes `0x1C - 0x1F`: Header CRC32C (`u32` checksum of bytes `0x00 - 0x1B`).
>   - Bytes `0x20 - 0x5F`: Ed25519 Cryptographic Signature (`[u8; 64]`).
>   - Bytes `0x60 - 0x7F`: Payload Digest (`[u8; 32]` BLAKE3 hash of raw payload).
>   - Bytes `0x80 - End`: Payload (`[u8]` variable length).
> - **Bit-Validation Pipeline**:
>   1. Magic bytes match `"HIVE"`.
>   2. Version equals `0x01`.
>   3. CRC32C checksum matches header bytes `0x00 - 0x1B`.
>   4. Payload length <= 16MB ceiling (16,777,216 bytes).
>   5. Monotonic sequence nonce tracking for replay defense.
>   6. Cryptographic signature and BLAKE3 payload hash verification.

## Open Questions

- None. The specification for the 128-byte frame header, bit fields, validation criteria, and Rust struct definition are fully specified in the prompt.

---

## Proposed Changes

### Protocol & Frame Validation Layer

#### [MODIFY] [protocol.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/protocol.py)
- Define `HivemindMessageType` enum (`DELTA = 0x01`, `HEARTBEAT = 0x02`, `SYNC = 0x03`).
- Define `HivemindFlags` bitfield flags (`ENCRYPTED = 0x0001`, `COMPRESSED = 0x0002`).
- Add `HivemindFrame` class with 128-byte header packing/unpacking using binary struct layout (`<4sBBHQQII64s32s`):
  - Strict 128-byte header alignment.
  - CRC32C computation for header validation (`0x00 - 0x1B`).
  - 16MB payload size ceiling enforcement (`16 * 1024 * 1024` bytes).
  - BLAKE3 / SHA256 digest validation.
  - Sequence nonce anti-replay validation.

#### [NEW] [hivemind_proxy.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/hivemind_proxy.py)
- High-performance Python edge proxy validator & decoder simulating microsecond-tier bit validation before forwarding payloads to Clew's cognitive core.
- Implements `validate_frame()`, `extract_payload()`, and `HivemindValidationResult`.

---

### Rust Reference Implementation

#### [NEW] [src/hivemind.rs](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/src/hivemind.rs)
- Add Rust header definition matching `#[repr(C, packed)] pub struct HivemindHeader`.
- Include `impl HivemindHeader` with constants, byte conversion (`from_bytes`, `to_bytes`), CRC32C verification, sequence validation, and 16MB ceiling checks.

---

### Heartbeat Daemon Integration

#### [MODIFY] [heartbeat_daemon.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py)
- Update `HeartbeatDaemon` to produce and parse 128-byte `HivemindFrame` binary pings (`msg_type = 0x02`).

---

### Documentation

#### [NEW] [docs/hivemind_edge_proxy.md](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/docs/hivemind_edge_proxy.md)
#### [MODIFY] [docs/architecture.md](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/docs/architecture.md)
- Document the 128-byte fixed binary frame layout, Rust struct definition, memory layout table, and bit-validation pipeline.

---

### Automated Unit Tests

#### [NEW] [tests/test_hivemind_proxy.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_hivemind_proxy.py)
- Test suite verifying:
  - 128-byte header binary packing and exact size (128 bytes).
  - Magic byte validation (`0x48 0x49 0x56 0x45`).
  - CRC32C checksum calculation and verification across header bytes `0x00 - 0x1B`.
  - Rejection of payloads exceeding 16MB ceiling (e.g. 16MB + 1 byte).
  - Rejection of invalid payload digests (BLAKE3 / SHA256 mismatch).
  - Anti-replay sequence nonce enforcement.
  - Heartbeat daemon binary frame generation.

---

## Verification Plan

### Automated Tests
- Run `python -m unittest tests/test_hivemind_proxy.py`
- Run `python -m unittest discover tests`

### Manual Verification
- Verify binary pack/unpack round-trip for 128-byte headers.
- Validate error responses for corrupt magic, payload overflow, and CRC32C mismatch.
