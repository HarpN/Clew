# Task 1: Append-Only Event Ledger & Graph CRDT Engine Implementation Plan

Implement **Task 1** of the Clew V5 architecture: an append-only event ledger and state-based Graph CRDT engine supporting Add-Wins OR-Sets, Last-Write-Wins (LWW) scalars, and Multi-Value Registers (MVR) for divergent semantic attributes.

## User Review Required

> [!IMPORTANT]
> - **ClewLedgerEvent & ClewEventLedger (`ledger.py`)**:
>   - Hybrid Logical Clock (`physical_time`, `logical_counter`, `node_id`) ensuring total ordering across distributed nodes.
>   - Tamper-evident hash chain linking each event hash digest to the preceding event digest.
> - **Graph CRDT Engine (`crdt_engine.py`)**:
>   - **Add-Wins OR-Set**: Node and edge membership tracking where concurrent additions and removals resolve in favor of additions.
>   - **LWW-Register**: Scalar property updates resolved by highest HLC timestamp `(physical_time, logical_counter, node_id)`.
>   - **Multi-Value Register (MVR)**: Divergent semantic attribute updates preserving concurrent un-reconciled values until processed by the Task 2 LLM Arbiter.
>   - **Ledger Replay**: Deterministic state reconstruction by replaying event logs in HLC total order.

## Open Questions

- None. Requirements and CRDT semantics are strictly specified in the handoff directive.

---

## Proposed Changes

### Core Event Ledger

#### [NEW] [ledger.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ledger.py)
- Define `ClewLedgerEvent` Pydantic model:
  - `event_id`: UUID string.
  - `physical_time`: Float epoch timestamp.
  - `logical_counter`: Int monotonic HLC counter.
  - `node_id`: Node identifier string.
  - `event_type`: Event action (`NODE_ADD`, `NODE_REMOVE`, `EDGE_ADD`, `EDGE_REMOVE`, `SET_SCALAR`, `SET_SEMANTIC_MVR`).
  - `target_id`: Target node/edge ID.
  - `payload`: Parameters dictionary.
  - `prev_hash`: Previous event's BLAKE3/SHA256 digest.
  - `event_hash`: Computed event BLAKE3/SHA256 hash.
  - Method `hlc_key()` returning `(physical_time, logical_counter, node_id)`.
- Define `ClewEventLedger`:
  - `append_event()`: Constructs and appends a tamper-evident linked event.
  - `verify_integrity()`: Validates hash chain continuity across all events.
  - `get_events_since(hlc_key)`: Retrieves delta events for reconciliation.

---

### Graph CRDT Engine

#### [NEW] [crdt_engine.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/crdt_engine.py)
- Define `AddWinsORSet`:
  - Tracks `add_set: Set[Tuple[element, tag]]` and `remove_set: Set[tag]`.
  - Element exists if `any(tag not in remove_set for (elem, tag) in add_set)`.
- Define `LWWRegister`:
  - Holds `(value, hlc_key)` and resolves merges by max `hlc_key`.
- Define `MultiValueRegister` (MVR):
  - Holds `Set[Tuple[value, hlc_key]]`.
  - Superseded values (where existing `hlc_key < new_hlc_key` with direct causality) are replaced.
  - Concurrent values with disjoint timestamps are preserved simultaneously in the set.
- Define `GraphCRDT`:
  - Manages OR-Sets for nodes and edges, LWW registers for scalar attributes, and MVRs for semantic properties.
  - Method `apply_event(event: ClewLedgerEvent)`.
  - Method `merge(remote_graph: GraphCRDT)`.
  - Method `get_divergent_mvr_entries()` returning attributes needing LLM arbitration.

---

### Automated Unit Tests

#### [NEW] [tests/test_ledger_crdt.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_ledger_crdt.py)
- Unit tests verifying:
  - `ClewEventLedger` event creation, HLC ordering, and hash chain integrity verification.
  - `AddWinsORSet` concurrent addition and removal semantics (Add wins).
  - `LWWRegister` timestamp conflict resolution.
  - `MultiValueRegister` concurrent divergent value retention and resolution.
  - Full `GraphCRDT` ledger replay convergence across multi-node topologies.

---

## Verification Plan

### Automated Tests
- Run `python -m unittest tests/test_ledger_crdt.py`
- Run `python -m unittest discover tests` to ensure zero regressions across all 71+ existing tests.

### Manual Verification
- Test multi-node CRDT state merge with concurrent conflicting updates.
