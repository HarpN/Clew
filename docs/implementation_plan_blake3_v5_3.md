# Implementation Plan - BLAKE3 Merkle DAG Versioning & Atomic Rollback

This task builds the version control and state audit layer (`merkle_dag.py` and `version_engine.py`) that captures snapshots of the `GraphCRDT` state into immutable, BLAKE3-hashed Merkle Directed Acyclic Graphs (DAGs). This allows Clew to compute state diffs, verify historical integrity, and perform deterministic atomic rollbacks to any prior commit state.

## User Review Required

> [!IMPORTANT]
> The atomic rollback is implemented by replacing the internal structures of `GraphCRDT` (sets, registers, MVRs) in place rather than replacing the `GraphCRDT` object reference itself. This ensures that any component holding a reference to the `GraphCRDT` instance will automatically see the rolled-back state.

## Open Questions
None at this stage. The requirements are clear and can be implemented directly.

## Proposed Changes

### Merkle DAG Core Layer

We will introduce a new module `merkle_dag.py` that implements:
- `MerkleCommit`: Holds commit metadata, parent hashes, physical/logical clock timestamps, author ID, state root hashes, and the serialized graph snapshot. It uses `compute_hash_hex` from `ledger.py` to calculate a BLAKE3 (or fallback SHA256) hash of the commit's content.
- `MerkleDAG`: Houses the commit history as a DAG, supports adding commits, retrieving commits, diffing two commits, and recursively validating the DAG from the leaves to the root commits to ensure no tampering has occurred.

#### [NEW] [merkle_dag.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/merkle_dag.py)

---

### Version Engine Layer

We will introduce `version_engine.py` that wraps a `GraphCRDT` instance and handles commits, atomic rollbacks (checkouts), and chronological history traversal.

#### [NEW] [version_engine.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/version_engine.py)

---

### Version Control Tests

We will introduce unit tests under `tests/test_merkle_versioning.py` verifying commit creation, hash chaining, atomic rollbacks, diff computation, and DAG integrity checks.

#### [NEW] [test_merkle_versioning.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_merkle_versioning.py)

## Verification Plan

### Automated Tests
- Run the newly created versioning tests:
  `python -m unittest tests/test_merkle_versioning.py`
- Run the entire test suite to ensure no regressions:
  `python -m unittest discover tests`

### Manual Verification
- Verify code readability, check for correct imports, and ensure adherence to project styling guidelines.
