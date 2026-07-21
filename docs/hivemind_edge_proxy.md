# Hivemind Edge Proxy & Bit-Validation Protocol Specifications

## Overview
Hivemind is a microsecond-tier Rust edge proxy that sits directly in front of Clew. It handles transport security, mutual authentication, anti-replay defense, and bit-level payload validation to protect Clew's cognitive core from malformed, oversized, or unauthorized data streams.

---

## 128-Byte Fixed Binary Frame Layout

Every transmission through Hivemind begins with a fixed 128-byte binary header followed by a variable-length payload.

| Byte Offset | Field Name | Size | Data Type | Purpose & Validation Rules |
|---|---|---|---|---|
| `0x00 - 0x03` | `magic` | 4 B | `[u8; 4]` | Magic bytes (`0x48 0x49 0x56 0x45` = `"HIVE"`). Must match exactly. |
| `0x04` | `version` | 1 B | `u8` | Protocol version (`0x01`). Rejects unsupported versions. |
| `0x05` | `msg_type` | 1 B | `u8` | Message type (`0x01` Delta, `0x02` Heartbeat, `0x03` Sync). |
| `0x06 - 0x07` | `flags` | 2 B | `u16` | Bitfield flags (Bit 0: Encrypted `0x0001`, Bit 1: Compressed `0x0002`). |
| `0x08 - 0x0F` | `sequence_nonce` | 8 B | `u64` | Monotonic sequence number for anti-replay verification. |
| `0x10 - 0x17` | `hlc_timestamp` | 8 B | `u64` | Physical epoch timestamp in milliseconds. |
| `0x18 - 0x1B` | `payload_len` | 4 B | `u32` | Length of payload. Enforces strict **16MB ceiling** (`16,777,216` bytes). |
| `0x1C - 0x1F` | `header_crc32c` | 4 B | `u32` | SIMD-accelerated CRC32C checksum of header bytes `0x00 - 0x1B`. |
| `0x20 - 0x5F` | `signature` | 64 B | `[u8; 64]` | Ed25519 cryptographic signature. |
| `0x60 - 0x7F` | `payload_digest` | 32 B | `[u8; 32]` | BLAKE3 cryptographic hash of raw payload bytes. |
| `0x80 - End` | `payload` | Var | `[u8]` | Encrypted event ledger payload (`0` to `16MB`). |

---

## Rust Header Definition

```rust
#[repr(C, packed)]
pub struct HivemindHeader {
    pub magic: [u8; 4],
    pub version: u8,
    pub msg_type: u8,
    pub flags: u16,
    pub sequence_nonce: u64,
    pub hlc_timestamp: u64,
    pub payload_len: u32,
    pub header_crc32c: u32,
    pub signature: [u8; 64],
    pub payload_digest: [u8; 32],
}

impl HivemindHeader {
    pub const MAGIC: [u8; 4] = *b"HIVE";
    pub const HEADER_SIZE: usize = std::mem::size_of::<Self>(); // 128 bytes
}
```

---

## Bit-Validation Rules & Security Pipeline

When a frame is received by Hivemind Edge Proxy:
1. **Header Size Check**: Frame length must be >= 128 bytes.
2. **Magic Byte Verification**: Bytes `0x00 - 0x03` must equal `"HIVE"`.
3. **Version Check**: Byte `0x04` must equal `0x01`.
4. **Header CRC32C Verification**: CRC32C of bytes `0x00 - 0x1B` must match byte `0x1C - 0x1F`.
5. **16MB Payload Ceiling**: `payload_len` must be <= `16,777,216` bytes.
6. **Anti-Replay Nonce Verification**: `sequence_nonce` must be strictly greater than the last processed nonce for the client node.
7. **Payload Digest Verification**: 32-byte BLAKE3 hash of payload must match `payload_digest`.
8. **Forwarding**: Validated frames are dispatched to Clew's cognitive core.
