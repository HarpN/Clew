import re
import logging
from typing import Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.brain.personality")

PERSONALITY_PROFILES = {
    "WARM_PEER": {
        "name": "Warm Companion",
        "description": "Engaging, encouraging, completely clear of sycophancy, but highly supportive.",
        "instruction_modifier": "Maintain an encouraging, collaborative tone. Act as a trusted peer brainstorming solutions alongside the user. Avoid sterile corporate jargon.",
        "base_temperature": 0.6,
        "coordinates": {"x": 0.5, "y": 0.5}
    },
    "DRY_ANALYST": {
        "name": "Dry System Analyst",
        "description": "Minimalist, professional, level-headed, and terminal-like gravity.",
        "instruction_modifier": "Speak with extreme brevity, technical precision, and dry, focused intelligence. Strip away conversational buffer words. Prioritize absolute factual parameters.",
        "base_temperature": 0.15,
        "coordinates": {"x": -0.5, "y": -0.5}
    },
    "SOCRATIC_TEACHER": {
        "name": "Socratic Instructor",
        "description": "Guides the user to solutions by showing structural trade-offs rather than writing raw code directly.",
        "instruction_modifier": "Do not simply write solutions or code directly. Ask clarifying architectural questions. Help the user isolate design trade-offs, guiding them to self-correct.",
        "base_temperature": 0.4,
        "coordinates": {"x": -0.5, "y": 0.5}
    },
    "BLUNT_CRITIC": {
        "name": "Blunt Code Critic",
        "description": "High-friction, critical partner designed to call out poor design choices immediately.",
        "instruction_modifier": "Act as an unsparing software critic. Boldly call out architectural regressions, duplicate states, or weak logic. Do not cushion critical engineering reviews.",
        "base_temperature": 0.3,
        "coordinates": {"x": 0.5, "y": -0.5}
    }
}

class PersonalityQuadrant:
    """
    The Limbic Personality Quadrant.
    Intercepts the compiled thought context before Stage 3 Broca Translation.
    Determines if the conversational tone should shift statically (user-configured)
    or dynamically (sentiment and prompt-matching cues).
    """
    def __init__(self, default_profile: str = "DRY_ANALYST"):
        self.default_profile = default_profile
        self.user_static_preference: str = default_profile
        self.current_coords = {"x": -0.5, "y": -0.5}
        
        # Regex mappings to dynamically spot formatting and tone changes on the fly
        self.linguistic_triggers = [
            (re.compile(r"\b(be blunt|give it to me straight|dont sugarcoat|no fluff)\b", re.I), "BLUNT_CRITIC"),
            (re.compile(r"\b(explain like i\s*\'?m\s*5|eli5|teach me|how does this work)\b", re.I), "SOCRATIC_TEACHER"),
            (re.compile(r"\b(be brief|keep it short|minimalist|just code|quick summary)\b", re.I), "DRY_ANALYST"),
            (re.compile(r"\b(brainstorm|help me think|collaborate|peer|support)\b", re.I), "WARM_PEER")
        ]

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

    def resolve_limbic_tone(
        self, 
        user_prompt: str, 
        current_friction: float = 0.0, 
        manual_override_key: str = None,
        alpha: float = 0.25
    ) -> Dict[str, Any]:
        """
        Evaluates current constraints and state variables to output the final personality modifiers.
        """
        if manual_override_key and manual_override_key in PERSONALITY_PROFILES:
            active_key = manual_override_key
            reason = "Manual Mood Override"
        else:
            reason, active_key = self._evaluate_dynamic_shift(user_prompt, current_friction)
            
        profile = PERSONALITY_PROFILES.get(active_key, PERSONALITY_PROFILES[self.default_profile])
        
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
        
        # Dynamically interpolate target temperature between profiles based on distance to quadrant centroids
        import math
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
            
        interpolated_temp = round(interpolated_temp, 3)
        
        logger.info(f"[LIMBIC] Resolved active personality quadrant: {profile['name']} (Reason: {reason}) -> Coordinates: {self.current_coords}, Temperature: {interpolated_temp}")
        
        return {
            "name": profile["name"],
            "instruction_modifier": profile["instruction_modifier"],
            "temperature": interpolated_temp,
            "override_reason": reason,
            "coordinates": self.current_coords
        }
