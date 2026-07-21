# Lesson 3: State Chaining & Graph CRDTs

## 🧠 Core Concept: Event Chaining & Conflict Resolution

In a distributed environment where multiple nodes (e.g., local app, desktop command center, cloud engine) update graph structures concurrently, synchronization issues are common:
- **Split-Brain States**: Two partitioned nodes make updates independently.
- **Out-of-Order Delivery**: Network latency causes updates to arrive out of order.
- **Tampering**: Modifying database state history without trace.

Clew resolves these issues with two core architectural patterns:
1. **Append-Only Event Ledger (`ledger.py`)**: All mutations are recorded as sequential ledger events linked via cryptographically secure hashes (similar to blockchain hash chaining).
2. **Conflict-Free Replicated Data Types (CRDTs) (`crdt_engine.py`)**: Data structures that merge mathematically, guaranteeing eventual consistency without a central coordinating node.

---

## 🔍 Code Breakdown

Let's review the code starting with the Event Ledger.

### Hash Chaining (`ClewLedgerEvent.calculate_hash`)

In [ledger.py:L41-54](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ledger.py#L41-L54), each event links to the preceding event's hash to prevent tampering:

```python
    def calculate_hash(self) -> str:
        """Computes deterministic hash digest over event fields and prev_hash."""
        data_to_hash = {
            "event_id": self.event_id,
            "physical_time": round(self.physical_time, 6),
            "logical_counter": self.logical_counter,
            "node_id": self.node_id,
            "event_type": self.event_type,
            "target_id": self.target_id,
            "payload": self.payload,
            "prev_hash": self.prev_hash
        }
        encoded = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return compute_hash_hex(encoded)
```
If any intermediate event's payload is modified retroactively, its hash changes, breaking the `prev_hash` reference chain for all subsequent entries. This is checked by `verify_integrity()`.

---

### Observed-Remove Sets (OR-Sets)

To sync graph nodes and edges without central coordination, Clew uses an **Add-Wins Observed-Remove Set (OR-Set)** in [crdt_engine.py:L11-45](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/crdt_engine.py#L11-L45):

```python
class AddWinsORSet:
    def __init__(self):
        self.add_set: Dict[str, Any] = {}
        self.remove_set: Set[str] = set()

    def add(self, element: Any, tag: str):
        """Adds element associated with a unique tag."""
        self.add_set[tag] = element

    def remove(self, element: Any) -> Set[str]:
        """Removes all currently observed tags for the element."""
        observed_tags = {tag for tag, elem in self.add_set.items() if elem == element}
        self.remove_set.update(observed_tags)
        return observed_tags

    def read(self) -> Set[Any]:
        """Returns set of active elements whose add tags have not been removed."""
        return {elem for tag, elem in self.add_set.items() if tag not in self.remove_set}
```

### 💡 How does it resolve conflicts?
If Node A adds item `X` with tag `t1` and Node B concurrently removes item `X` (which observes/removes existing tag `t1`), but Node A concurrently adds `X` with a newer tag `t2`, the union merge of both nodes retains `t2` in the active set.
Because addition of a new tag was not observed by the concurrent removal, the **Addition Wins**!

---

## 🔬 Deep Dives

### Multi-Value Registers (MVR) for Semantic Reconciliation
When scalar registers collide, a simple **Last-Write-Wins (LWW) Register** resolves the conflict by using the highest HLC timestamp.
However, semantic properties (like an LLM-derived description of an event) shouldn't be discarded just because one clock won by a millisecond.
Clew implements a **Multi-Value Register (MVR)** in [crdt_engine.py:L68-100](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/crdt_engine.py#L68-L100):
```python
class MultiValueRegister:
    def __init__(self):
        self.entries: Dict[Tuple[float, int, str], Any] = {}

    def set(self, value: Any, timestamp: Tuple[float, int, str], causal_supersedes: Optional[Set[Tuple[float, int, str]]] = None):
        if causal_supersedes:
            for old_ts in causal_supersedes:
                self.entries.pop(old_ts, None)
        else:
            to_remove = [ts for ts in self.entries if ts < timestamp and ts[2] == timestamp[2]]
            for old_ts in to_remove:
                self.entries.pop(old_ts, None)
        self.entries[timestamp] = value
```
- **Concurrency Preservation**: If two nodes write values concurrently (neither HLC causally dominates/supersedes the other), the MVR stores *both* values in `self.entries`.
- **Divergence Check**: The system calls `is_divergent()` to verify if conflicts exist. If so, a semantic Arbiter reconciles the divergent values using LLM context.

---

## 📝 Interactive Quiz

### Question 1: What does an "Add-Wins OR-Set" do if an element is added and removed concurrently?
- **A)** The element is deleted permanently.
- **B)** The addition takes precedence because the removal did not observe the concurrent addition's unique tag.
- **C)** The system crashes with a serialization exception.
- **D)** It falls back to PostgreSQL connectivity checks.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: B**

**Explanation**: 
Since removals only invalidate *currently observed* tags, any concurrent additions that introduce new tags will not be affected by the merge removal, ensuring the addition wins.
</details>

### Question 2: In the Append-Only Event Ledger, how is event integrity checked?
- **A)** By querying the database to see if records match the schema.
- **B)** By checking if each event's `prev_hash` matches the `event_hash` of the preceding element.
- **C)** By validating that the timestamp matches local time.
- **D)** By running a WebSockets broadcast.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: B**

**Explanation**: 
The ledger's chain integrity is verified sequentially. If any event has a `prev_hash` that doesn't match the preceding event's `event_hash`, the chain is invalid (indicating tampering or deletion).
</details>

---

## 🛠️ Coding Exercise / Challenge

### Challenge: Integrity Auditing
Open [ledger.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ledger.py). Inspect `verify_integrity()` around lines 95-108. Write a unit test that appends 3 events to `ClewEventLedger`, manually mutates the payload of the second event, and asserts that `verify_integrity()` returns `False`. Run the test suite:
`pytest tests/test_ledger_crdt.py`
