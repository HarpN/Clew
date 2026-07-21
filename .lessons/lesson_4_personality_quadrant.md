# Lesson 4: Limbic Personality Quadrants

## 🧠 Core Concept: Steerable Agent Personas & Temperature Modulation

Advanced AI agents need to adapt their conversational style, level of verbosity, and reasoning approach based on user context. In Clew, this is handled by the **Limbic Personality Quadrant** (`personality_quadrant.py`).
Rather than hardcoding static system instructions, Clew represents personality profiles as coordinates on a 2D grid:
- **Warm Companion (`WARM_PEER`)**: Coordinates `(0.5, 0.5)`. Collaborative, peer-like brainstorming.
- **Dry System Analyst (`DRY_ANALYST`)**: Coordinates `(-0.5, -0.5)`. High-precision, brief, and dry instructions.
- **Socratic Instructor (`SOCRATIC_TEACHER`)**: Coordinates `(-0.5, 0.5)`. Guides the user to self-correct rather than providing raw code directly.
- **Blunt Code Critic (`BLUNT_CRITIC`)**: Coordinates `(0.5, -0.5)`. Critical, unsparing software reviews.

By mapping these personas to coordinates, Clew can smoothly transition between states and dynamically interpolate prompt instructions and generation temperatures.

---

## 🔍 Code Breakdown

Let's look at how Clew resolves and shifts these states in [personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py).

### Linguistic Triggers & Stress Fallback (`_evaluate_dynamic_shift`)

In [personality_quadrant.py:L59-76](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py#L59-L76), Clew parses user inputs and system stress to determine the active persona:

```python
    def _evaluate_dynamic_shift(self, user_prompt: str, current_friction: float) -> Tuple[str, str]:
        """
        Analyzes the user's raw prompt for dynamic personality override triggers.
        Returns: (override_reason, override_profile_key) or (None, None)
        """
        # 1. Friction check: If friction is exceptionally high, force DRY_ANALYST (Terse Mode fallback)
        if current_friction >= 0.75:
            logger.info("[LIMBIC] Extreme session friction detected. Dynamically forcing DRY_ANALYST profile.")
            return "Amygdala Stress Emergency Shunt", "DRY_ANALYST"
            
        # 2. Check for explicit linguistic trigger patterns in the prompt
        for pattern, profile_key in self.linguistic_triggers:
            if pattern.search(user_prompt):
                logger.info(f"[LIMBIC] Dynamic trigger matched. Overriding personality profile to: {profile_key}")
                return "Direct Linguistic Intent Request", profile_key
                
        return "Standard Preference", self.user_static_preference
```

- **Friction Shunt**: If the user experiences high friction (measured by the Amygdala stress model), Clew immediately switches to the `DRY_ANALYST` persona. This drops conversational fluff to minimize delay and focus purely on resolving the issue.
- **Linguistic Triggers**: Regex checks scan the prompt for patterns like `"be blunt"` or `"teach me"` to update the profile match dynamically.

---

### Coordinate Smoothing & Transitions

When a transition occurs, Clew does not jump between styles instantly. Instead, it smoothly interpolates the coordinates using a smoothing coefficient `alpha` in [personality_quadrant.py:L95-110](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py#L95-L110):

```python
        # Calculate target coordinates
        x_target = profile["coordinates"]["x"]
        y_target = profile["coordinates"]["y"]
        
        # Determine effective alpha
        if manual_override_key or reason == "Amygdala Stress Emergency Shunt":
            effective_alpha = 1.0
        else:
            effective_alpha = alpha
            
        # Smooth coordinates
        x_new = effective_alpha * x_target + (1.0 - effective_alpha) * self.current_coords["x"]
        y_new = effective_alpha * y_target + (1.0 - effective_alpha) * self.current_coords["y"]
        
        # Update current coordinates
        self.current_coords = {"x": round(x_new, 3), "y": round(y_new, 3)}
```

This prevents sudden shifts in tone, maintaining a consistent assistant persona.

---

## 🔬 Deep Dives

### Inverse Distance Weighting (IDW) for Temperature Interpolation
To resolve the model generation temperature for arbitrary coordinates on the grid, Clew uses **Inverse Distance Weighting (IDW)** in [personality_quadrant.py:L113-133](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py#L113-L133):
```python
        distances = {}
        exact_match_temp = None
        for key, prof in PERSONALITY_PROFILES.items():
            cx = prof["coordinates"]["x"]
            cy = prof["coordinates"]["y"]
            d = math.sqrt((x_new - cx)**2 + (y_new - cy)**2)
            if d < 1e-5:
                exact_match_temp = prof["base_temperature"]
                break
            distances[key] = d
            
        if exact_match_temp is not None:
            interpolated_temp = exact_match_temp
        else:
            # Inverse distance weighting
            weights = {k: 1.0 / v for k, v in distances.items()}
            sum_weights = sum(weights.values())
            interpolated_temp = sum(w * PERSONALITY_PROFILES[k]["base_temperature"] for k, w in weights.items()) / sum_weights
```
This algorithm calculates the distance from the current smoothed coordinates `(x_new, y_new)` to the centroids of all four profiles. The closer the system is to a specific profile's centroid, the more weight that profile's `base_temperature` has. This allows Clew to smoothly interpolate between low-temperature deterministic coding modes (`0.15`) and high-temperature collaborative brainstorming modes (`0.60`).

---

## 📝 Interactive Quiz

### Question 1: What triggers the "Amygdala Stress Emergency Shunt"?
- **A)** The user types the word "Emergency".
- **B)** Session friction (stress level) exceeds or equals `0.75`.
- **C)** A database timeout error is encountered.
- **D)** The heartbeat daemon misses 3 consecutive pings.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: B**

**Explanation**: 
When `current_friction >= 0.75`, the system initiates the emergency shunt to switch the personality to `DRY_ANALYST` (Terse Mode) to reduce output length and focus on issue resolution.
</details>

### Question 2: Why does Clew use coordinates smoothing (`alpha`) instead of jumping directly to the targets?
- **A)** To avoid sudden, jarring changes in conversational tone across turn transitions.
- **B)** Because Python's float division does not support exact coordinates.
- **C)** To prevent database transaction locks.
- **D)** To encrypt the prompt modifier string.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: A**

**Explanation**: 
Smoothing coordinates with an `alpha` coefficient (default `0.25`) ensures the assistant's persona shifts gradually. This mimics standard human cognitive state transitions, rather than snapping between dry technical responses and companion-like banter instantly.
</details>

---

## 🛠️ Coding Exercise / Challenge

### Challenge: Add a New Trigger
Open [personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py). Add a linguistic trigger under `self.linguistic_triggers` that scans for the word `"socrates"` or `"teach me"` and switches the personality to `SOCRATIC_TEACHER`. Verify your edits by running:
`pytest tests/test_personality_quadrant.py`
