"""
broca_translator.py - Broca's Area Semantic Translation & Styling Layer
"""
import re
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import numpy as np

from persona_manager import PersonaRegistry
from personality_validator import PersonalityValidator
from router import ModelRouter, query_ollama_chat, GENERALIST_MODEL, OLLAMA_OPTIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.broca")

class BrocaArea:
    """
    Broca's Area is the translation layer that receives verified factual payloads
    from the Prefrontal Orchestrator, applies active personas, and outputs clean prose.
    """
    def __init__(self):
        self.router = ModelRouter()

    def compute_semantic_distance(self, response: str, grounded_payload: Any) -> float:
        """
        Computes a local cosine distance between the response and the grounded factual payload.
        Ensures D(S_response, F_grounded) < epsilon.
        """
        # Convert grounded_payload to string representation
        if isinstance(grounded_payload, (dict, list)):
            payload_str = json.dumps(grounded_payload)
        else:
            payload_str = str(grounded_payload)

        # Tokenize and compute term frequencies
        words1 = re.findall(r'\w+', response.lower())
        words2 = re.findall(r'\w+', payload_str.lower())

        if not words1 or not words2:
            return 1.0  # Maximum distance if empty

        # Get union of all unique words
        all_words = list(set(words1 + words2))

        # Vector representation
        v1 = np.zeros(len(all_words))
        v2 = np.zeros(len(all_words))

        for i, w in enumerate(all_words):
            v1[i] = words1.count(w)
            v2[i] = words2.count(w)

        # Cosine distance computation
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)

        if norm_v1 == 0 or norm_v2 == 0:
            return 1.0

        similarity = dot_product / (norm_v1 * norm_v2)
        distance = 1.0 - similarity
        return distance

    async def compile_response(
        self, verified_payload: Any, epsilon: float = 0.6, terse_mode: bool = False,
        personality_directives: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compiles the factual payload into natural human prose synchronously (non-streaming).
        """
        logger.info(f"Compiling prose non-streaming from factual payload (terse_mode={terse_mode}).")
        system_prompt = self._build_system_prompt(terse_mode=terse_mode, personality_directives=personality_directives)
        user_prompt = self._build_user_prompt(verified_payload)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Use generalist model with low temperature
        options = OLLAMA_OPTIONS.copy()
        if personality_directives and "temperature" in personality_directives:
            options["temperature"] = personality_directives["temperature"]
        else:
            options["temperature"] = 0.1
        if terse_mode:
            options["max_tokens"] = 64
            options["num_predict"] = 64

        # Query Ollama
        raw_response = query_ollama_chat(messages, model=GENERALIST_MODEL, options=options)
        
        # Sub-millisecond Personality Validation Cleaning
        cleaned_response = PersonalityValidator.clean(raw_response)

        # Semantic Divergence Check (Broca Guard)
        distance = self.compute_semantic_distance(cleaned_response, verified_payload)
        logger.info(f"Broca Guard: Cosine Distance = {distance:.4f} (Threshold epsilon = {epsilon})")
        if not terse_mode and distance >= epsilon:
            warning_msg = f"Broca Guard Warning: Semantic divergence {distance:.4f} exceeds threshold {epsilon}."
            logger.warning(warning_msg)
            raise ValueError(warning_msg)

        return cleaned_response

    async def compile_response_stream(
        self, verified_payload: Any, epsilon: float = 0.6, terse_mode: bool = False,
        personality_directives: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Compiles the factual payload into natural human prose asynchronously (streaming).
        Dynamically strips preambles, sycophancy, and exclamations in real-time.
        """
        logger.info(f"Compiling prose streaming from factual payload (terse_mode={terse_mode}).")
        system_prompt = self._build_system_prompt(terse_mode=terse_mode, personality_directives=personality_directives)
        user_prompt = self._build_user_prompt(verified_payload)

        # Use generalist model with low temperature
        options = OLLAMA_OPTIONS.copy()
        if personality_directives and "temperature" in personality_directives:
            options["temperature"] = personality_directives["temperature"]
        else:
            options["temperature"] = 0.1
        if terse_mode:
            options["max_tokens"] = 64
            options["num_predict"] = 64

        # Get stream from ModelRouter
        stream = self.router.execute_streaming_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            options=options
        )

        accumulated_text = ""
        yielded_len = 0

        async for chunk in stream:
            accumulated_text += chunk
            # Real-time cleaning
            cleaned = PersonalityValidator.clean(accumulated_text)
            if len(cleaned) > yielded_len:
                new_part = cleaned[yielded_len:]
                yielded_len = len(cleaned)
                yield new_part

        # Post-inference semantic divergence check
        cleaned_final = PersonalityValidator.clean(accumulated_text)
        distance = self.compute_semantic_distance(cleaned_final, verified_payload)
        logger.info(f"Broca Guard Stream: Cosine Distance = {distance:.4f} (Threshold epsilon = {epsilon})")
        if not terse_mode and distance >= epsilon:
            warning_msg = f"Broca Guard Warning: Semantic divergence {distance:.4f} exceeds threshold {epsilon}."
            logger.warning(warning_msg)
            raise ValueError(warning_msg)

    def _build_system_prompt(self, terse_mode: bool = False, personality_directives: Optional[Dict[str, Any]] = None) -> str:
        if terse_mode:
            return "You are operating in safe Terse Mode. Speak only in direct, functional, single-sentence answers or terminal codes. Omit all greetings, explanations, advice, and conversation. Solve the task silently."

        persona = PersonaRegistry.get_active_persona()
        base_prompt = f"""{persona}

You are Broca's Area, the semantic translation and styling layer.
Your sole job is to translate the raw grounded factual payload into clean, natural human prose.
Follow these constraints strictly:
1. Speak concisely, direct, and factual.
2. Rely ONLY on the facts in the payload. Do not invent tasks, numbers, or details.
3. Do not include preambles (e.g. "Sure! Here is...", "Okay, I will..."), opening remarks, sycophancy, or exclamations.
4. Output ONLY the styled human response. No commentary.
"""
        if personality_directives:
            override_block = (
                f"\n=== LIMBIC PERSONALITY OVERRIDE ===\n"
                f"Active Mood: {personality_directives['name']}\n"
                f"Directive: {personality_directives['instruction_modifier']}\n"
                f"==================================\n"
            )
            return base_prompt + override_block
            
        return base_prompt

    def _build_user_prompt(self, verified_payload: Any) -> str:
        return f"Grounded factual payload: {json.dumps(verified_payload)}"

