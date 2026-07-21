//! Hivemind Edge Proxy Rust Definition & Bit-Validation Rules
//! High-performance microsecond-tier Rust edge proxy transport security & payload validation header.

use std::convert::TryInto;

pub const HIVEMIND_MAGIC: [u8; 4] = *b"HIVE";
pub const HIVEMIND_VERSION: u8 = 0x01;
pub const MAX_PAYLOAD_CEILING: u32 = 16 * 1024 * 1024; // Strict 16MB ceiling

#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HivemindMessageType {
    Delta = 0x01,
    Heartbeat = 0x02,
    Sync = 0x03,
}

pub bitflags::bitflags! {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    pub struct HivemindFlags: u16 {
        const NONE = 0x0000;
        const ENCRYPTED = 0x0001;
        const COMPRESSED = 0x0002;
    }
}

#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
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

    /// Creates a new HivemindHeader instance with zeroed signatures and payload digest.
    pub fn new(
        msg_type: HivemindMessageType,
        flags: u16,
        sequence_nonce: u64,
        hlc_timestamp: u64,
        payload_len: u32,
    ) -> Result<Self, &'static str> {
        if payload_len > MAX_PAYLOAD_CEILING {
            return Err("Payload length exceeds strict 16MB ceiling");
        }

        let mut header = Self {
            magic: Self::MAGIC,
            version: HIVEMIND_VERSION,
            msg_type: msg_type as u8,
            flags,
            sequence_nonce,
            hlc_timestamp,
            payload_len,
            header_crc32c: 0,
            signature: [0u8; 64],
            payload_digest: [0u8; 32],
        };

        header.header_crc32c = header.compute_crc32c();
        Ok(header)
    }

    /// Computes CRC32C checksum over bytes 0x00 - 0x1B (first 28 bytes of header).
    pub fn compute_crc32c(&self) -> u32 {
        let bytes = self.to_bytes();
        let pre_crc_bytes = &bytes[0..28];
        crc32fast::Hasher::new_with_initial_len(0, 0)
            .extend(pre_crc_bytes)
            .finalize()
    }

    /// Converts packed header struct into a 128-byte raw slice.
    pub fn to_bytes(&self) -> [u8; 128] {
        unsafe { std::mem::transmute_copy(self) }
    }

    /// Parses a 128-byte raw slice into a HivemindHeader and validates layout rules.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, &'static str> {
        if bytes.len() < Self::HEADER_SIZE {
            return Err("Header size must be at least 128 bytes");
        }

        let header: Self = unsafe {
            std::ptr::read_unaligned(bytes.as_ptr() as *const Self)
        };

        header.validate()?;
        Ok(header)
    }

    /// Bit-validation rules pipeline:
    /// 1. Magic bytes must equal "HIVE"
    /// 2. Version must equal 0x01
    /// 3. Payload length must not exceed 16MB ceiling
    /// 4. Header CRC32C checksum verification (bytes 0x00 - 0x1B)
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.magic != Self::MAGIC {
            return Err("Invalid magic bytes (expected 'HIVE')");
        }
        if self.version != HIVEMIND_VERSION {
            return Err("Unsupported protocol version (expected 0x01)");
        }
        if self.payload_len > MAX_PAYLOAD_CEILING {
            return Err("Payload length exceeds 16MB ceiling");
        }
        
        let expected_crc = self.compute_crc32c();
        if self.header_crc32c != expected_crc {
            return Err("Header CRC32C checksum mismatch");
        }

        Ok(())
    }
}
