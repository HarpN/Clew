"""
tests/test_hivemind_proxy.py - Test suite for Hivemind Edge Proxy & Bit-Validation Rules
Verifies 128-byte binary frame header layout, bit-validation rules, CRC32C checksums,
16MB payload ceilings, BLAKE3 payload digests, anti-replay nonces, and Heartbeat Daemon binary pings.
"""

import unittest
import struct
from protocol import (
    HivemindFrame,
    HivemindMessageType,
    HivemindFlags,
    HIVEMIND_MAGIC,
    HIVEMIND_VERSION,
    HIVEMIND_HEADER_SIZE,
    MAX_PAYLOAD_CEILING,
    calculate_crc32c,
    calculate_blake3_digest
)
from hivemind_proxy import HivemindEdgeProxy, HivemindValidationResult
from heartbeat_daemon import HeartbeatDaemon

class TestHivemindEdgeProxy(unittest.TestCase):

    def setUp(self):
        self.proxy = HivemindEdgeProxy(node_id="test-edge-node", require_monotonic_nonce=True)

    def test_128_byte_header_packing_and_unpacking(self):
        """Verifies exact 128-byte header size and pack/unpack roundtrip."""
        frame = HivemindFrame(
            msg_type=HivemindMessageType.DELTA,
            flags=HivemindFlags.ENCRYPTED | HivemindFlags.COMPRESSED,
            sequence_nonce=1001,
            hlc_timestamp=1700000000000,
            signature=b'S' * 64,
            payload=b"Test Event Ledger Payload Data"
        )
        packed_data = frame.pack()
        header_bytes = packed_data[:128]
        self.assertEqual(len(header_bytes), HIVEMIND_HEADER_SIZE)

        unpacked_frame = HivemindFrame.unpack(packed_data)
        self.assertEqual(unpacked_frame.magic, HIVEMIND_MAGIC)
        self.assertEqual(unpacked_frame.version, HIVEMIND_VERSION)
        self.assertEqual(unpacked_frame.msg_type, HivemindMessageType.DELTA)
        self.assertEqual(unpacked_frame.flags, HivemindFlags.ENCRYPTED | HivemindFlags.COMPRESSED)
        self.assertEqual(unpacked_frame.sequence_nonce, 1001)
        self.assertEqual(unpacked_frame.hlc_timestamp, 1700000000000)
        self.assertEqual(unpacked_frame.payload, b"Test Event Ledger Payload Data")

    def test_crc32c_header_validation(self):
        """Verifies header CRC32C checksum calculation and corruption detection."""
        frame = HivemindFrame(
            msg_type=HivemindMessageType.SYNC,
            sequence_nonce=50,
            payload=b"Sync payload"
        )
        packed = frame.pack()
        
        # Validate clean frame
        res = self.proxy.validate_and_forward(packed, client_id="client_1")
        self.assertTrue(res.valid)
        self.assertEqual(res.error_code, "OK")

        # Corrupt first byte of header (magic byte)
        corrupted_bytes = bytearray(packed)
        corrupted_bytes[0] ^= 0xFF
        res_corrupt = self.proxy.validate_and_forward(bytes(corrupted_bytes), client_id="client_2")
        self.assertFalse(res_corrupt.valid)
        self.assertIn(res_corrupt.error_code, ["INVALID_MAGIC", "HEADER_CRC_MISMATCH"])

    def test_invalid_magic_bytes_rejection(self):
        """Verifies rejection when magic bytes do not equal 'HIVE'."""
        bad_magic_bytes = b"BADM" + b"\x00" * 124
        res = self.proxy.validate_and_forward(bad_magic_bytes, client_id="client_bad")
        self.assertFalse(res.valid)
        self.assertEqual(res.error_code, "INVALID_MAGIC")

    def test_unsupported_version_rejection(self):
        """Verifies rejection of unsupported protocol version."""
        # Version set to 0x02 instead of 0x01
        header_pre_crc = struct.pack("<4sBBHQQI", b"HIVE", 0x02, 0x01, 0, 1, 100, 0)
        crc = calculate_crc32c(header_pre_crc)
        raw_header = struct.pack("<4sBBHQQII64s32s", b"HIVE", 0x02, 0x01, 0, 1, 100, 0, crc, b"\x00"*64, b"\x00"*32)
        
        res = self.proxy.validate_and_forward(raw_header, client_id="client_ver")
        self.assertFalse(res.valid)
        self.assertEqual(res.error_code, "UNSUPPORTED_VERSION")

    def test_16mb_payload_ceiling_enforcement(self):
        """Verifies strict 16MB payload ceiling enforcement."""
        oversized_len = MAX_PAYLOAD_CEILING + 1  # 16,777,217 bytes
        header_pre_crc = struct.pack("<4sBBHQQI", b"HIVE", 0x01, 0x01, 0, 1, 100, oversized_len)
        crc = calculate_crc32c(header_pre_crc)
        raw_header = struct.pack("<4sBBHQQII64s32s", b"HIVE", 0x01, 0x01, 0, 1, 100, oversized_len, crc, b"\x00"*64, b"\x00"*32)

        res = self.proxy.validate_and_forward(raw_header, client_id="client_oversized")
        self.assertFalse(res.valid)
        self.assertEqual(res.error_code, "PAYLOAD_CEILING_EXCEEDED")

    def test_blake3_payload_digest_verification(self):
        """Verifies payload integrity using BLAKE3 hash digest."""
        payload = b"High-frequency algorithmic trade message"
        digest = calculate_blake3_digest(payload)
        
        frame = HivemindFrame(
            msg_type=HivemindMessageType.DELTA,
            sequence_nonce=1,
            payload_digest=digest,
            payload=payload
        )
        packed = frame.pack()

        # Modify payload byte without updating header
        corrupted = bytearray(packed)
        corrupted[-1] ^= 0x01
        
        res = self.proxy.validate_and_forward(bytes(corrupted), client_id="client_digest")
        self.assertFalse(res.valid)
        self.assertEqual(res.error_code, "PAYLOAD_DIGEST_MISMATCH")

    def test_anti_replay_monotonic_sequence_nonce(self):
        """Verifies anti-replay protection rejects out-of-order or duplicate sequence nonces."""
        frame1 = HivemindFrame(msg_type=HivemindMessageType.DELTA, sequence_nonce=10, payload=b"Msg 1").pack()
        frame2 = HivemindFrame(msg_type=HivemindMessageType.DELTA, sequence_nonce=11, payload=b"Msg 2").pack()
        frame_replayed = HivemindFrame(msg_type=HivemindMessageType.DELTA, sequence_nonce=10, payload=b"Replayed Msg 1").pack()

        # Nonce 10 -> OK
        res1 = self.proxy.validate_and_forward(frame1, client_id="client_nonce")
        self.assertTrue(res1.valid)

        # Nonce 11 -> OK
        res2 = self.proxy.validate_and_forward(frame2, client_id="client_nonce")
        self.assertTrue(res2.valid)

        # Replayed Nonce 10 -> REPLAY_ATTACK_DETECTED
        res_replay = self.proxy.validate_and_forward(frame_replayed, client_id="client_nonce")
        self.assertFalse(res_replay.valid)
        self.assertEqual(res_replay.error_code, "REPLAY_ATTACK_DETECTED")

    def test_heartbeat_daemon_binary_frame_ping(self):
        """Verifies HeartbeatDaemon generates valid 128-byte binary Hivemind frames."""
        daemon = HeartbeatDaemon(node_id="clew-test-node")
        binary_ping = daemon.send_binary_frame_ping()
        
        self.assertGreaterEqual(len(binary_ping), 128)
        header_bytes = binary_ping[:128]
        self.assertEqual(len(header_bytes), 128)

        # Validate through proxy
        res = self.proxy.validate_and_forward(binary_ping, client_id="clew-test-node")
        self.assertTrue(res.valid)
        self.assertEqual(res.frame.msg_type, HivemindMessageType.HEARTBEAT)

if __name__ == "__main__":
    unittest.main()
