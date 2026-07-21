"""
neuromorphic_subsystems.py - Amygdala Real-Time Friction tracking and shunting mechanism.
"""

import logging
import re
import numpy as np
import json
import os
from typing import List, Optional, Dict, Any, Tuple
from database import get_db_connection, dialect

logger = logging.getLogger("clew.neuromorphic")

class Amygdala:
    """
    Real-time stress tracking and shunting mechanism.
    Analyzes typing cadence, linguistic intensity, and sentiment.
    """
    def __init__(self, stress_threshold: float = 0.75):
        self.stress_threshold = stress_threshold

    def analyze_sentiment(self, text: str) -> float:
        """
        Runs a fast, lightweight lexical check to map sentiment strictly between -1.0 and 1.0.
        Negative feedback, exclamation spam, capitalizations, or abort keywords lower the score.
        """
        if not text:
            return 0.0
            
        text_lower = text.lower()
        
        # Negative feedback and abort keywords
        neg_keywords = [
            "wrong", "error", "fail", "broken", "stop", "no", "bad", "terrible", 
            "useless", "abort", "incorrect", "never", "hate", "dumb", "stupid",
            "cancel", "exit", "quit"
        ]
        neg_count = sum(text_lower.count(kw) for kw in neg_keywords)
        
        # Positive feedback keywords
        pos_keywords = [
            "good", "great", "awesome", "thanks", "thank you", "perfect", 
            "correct", "love", "yes", "nice", "excellent", "wonderful"
        ]
        pos_count = sum(text_lower.count(kw) for kw in pos_keywords)
        
        # Exclamations
        excl_count = text.count("!")
        
        # Capitalization check (ALL-CAPS words that are purely alphabetic and length > 1)
        words = text.split()
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 1 and w.isalpha())
        
        # Compute raw score
        score = 0.0
        score += pos_count * 0.3
        score -= neg_count * 0.4
        score -= excl_count * 0.2
        score -= caps_words * 0.3
        
        # Strictly map/clamp between -1.0 and 1.0
        return max(-1.0, min(1.0, score))

    def calculate_friction(
        self, 
        keystroke_deltas: Optional[List[float]], 
        recent_prompts: List[str], 
        sentiment_score: float
    ) -> float:
        """
        Computes user friction score F_user based on typing intervals, prompt repetition,
        exclamation spam, and lexical sentiment.
        """
        # 1. Cadence / Latency Impact
        # Short intervals between messages indicate fast/stressed typing.
        delta = None
        if keystroke_deltas:
            valid_deltas = [d for d in keystroke_deltas if isinstance(d, (int, float))]
            if valid_deltas:
                delta = sum(valid_deltas) / len(valid_deltas)
                
        if delta is not None:
            # If interval is under 2 seconds, max cadence stress. If over 10 seconds, no cadence stress.
            cadence_impact = max(0.0, min(1.0, (10.0 - delta) / 8.0))
        else:
            cadence_impact = 0.0

        # 2. Sentiment Impact
        # Map sentiment [-1.0, 1.0] -> sentiment_impact [1.0, 0.0]
        sentiment_impact = max(0.0, min(1.0, (1.0 - sentiment_score) / 2.0))

        # 3. Linguistic Intensity (Repetition & Punctuation)
        # Check current/last prompt punctuation
        current_prompt = recent_prompts[-1] if recent_prompts else ""
        excl_count = current_prompt.count("!")
        
        # Check repetition in last 3 prompts
        repetition_factor = 0.0
        if len(recent_prompts) >= 2:
            if len(recent_prompts) == 2 and recent_prompts[0] == recent_prompts[1]:
                repetition_factor = 0.5
            elif len(recent_prompts) == 3:
                if recent_prompts[0] == recent_prompts[1] == recent_prompts[2]:
                    repetition_factor = 1.0
                elif recent_prompts[0] == recent_prompts[1] or recent_prompts[1] == recent_prompts[2] or recent_prompts[0] == recent_prompts[2]:
                    repetition_factor = 0.5
                    
        intensity = (excl_count * 0.2) + repetition_factor
        linguistic_intensity = max(0.0, min(1.0, intensity))

        # Combine metrics mathematically
        f_user = 0.4 * sentiment_impact + 0.3 * cadence_impact + 0.3 * linguistic_intensity
        
        logger.info(
            f"Friction assessment: sentiment_score={sentiment_score:.2f} (impact={sentiment_impact:.2f}), "
            f"delta={delta} (impact={cadence_impact:.2f}), "
            f"linguistic_intensity={linguistic_intensity:.2f}. "
            f"Calculated F_user={f_user:.3f}"
        )
        
        return max(0.0, min(1.0, f_user))

    def should_shunt_to_terse(self, f_user: float) -> bool:
        """
        Determines whether the friction score crossed the stress threshold.
        """
        return f_user >= self.stress_threshold


class Hippocampus:
    """
    Offline background worker that analyzes the daily transaction ledger,
    clusters user corrections using a lightweight cosine similarity metric:
    $$S_{\text{cluster}}(A, B) = \frac{\mathbf{u} \cdot \mathbf{v}}{\Vert{}\mathbf{u}\Vert{} \Vert{}\mathbf{v}\Vert{}} \ge 0.85$$
    and consolidates repeated corrections into permanent Style Graph adaptations.
    """
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        # Correction keywords indicating the user had to redirect the AI
        self.correction_triggers = ["no", "stop", "fix", "wrong", "don't", "dont", "incorrect", "instead", "bad"]

    def _tokenize_and_vectorize(self, texts: List[str]) -> Tuple[np.ndarray, List[str]]:
        """
        Converts list of texts into word-frequency vectors (Bag-of-Words representation).
        Designed to be ultra-fast and free of external machine-learning dependencies.
        """
        # Lowercase, strip punctuation, and split into simple tokens
        tokenized = [[w for w in re.findall(r"\b\w+\b", t.lower()) if len(w) > 2] for t in texts]
        
        # Build global vocabulary mapping
        vocabulary = sorted(list(set(word for text_tokens in tokenized for word in text_tokens)))
        if not vocabulary:
            return np.zeros((len(texts), 0)), []
            
        word_to_idx = {word: idx for idx, word in enumerate(vocabulary)}
        
        # Build frequency vectors
        vectors = np.zeros((len(texts), len(vocabulary)))
        for row_idx, text_tokens in enumerate(tokenized):
            for word in text_tokens:
                if word in word_to_idx:
                    vectors[row_idx, word_to_idx[word]] += 1
                
        return vectors, vocabulary

    def _cosine_similarity(self, u: np.ndarray, v: np.ndarray) -> float:
        """
        Calculates the semantic cosine similarity between two word frequency vectors.
        """
        dot_product = np.dot(u, v)
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        if norm_u == 0 or norm_v == 0:
            return 0.0
        return float(dot_product / (norm_u * norm_v))

    def cluster_corrections(self, messages: List[str]) -> List[List[str]]:
        """
        Clusters raw correction strings using a distance similarity threshold.
        """
        if not messages or len(messages) < 2:
            return [[msg] for msg in messages] if messages else []

        vectors, vocab = self._tokenize_and_vectorize(messages)
        if len(vocab) == 0:
            # If no words can be vectorized, treat as no similarity
            return [[msg] for msg in messages]

        num_texts = len(messages)
        visited = [False] * num_texts
        clusters = []

        for i in range(num_texts):
            if visited[i]:
                continue
            
            # Start a brand new cluster
            current_cluster = [messages[i]]
            visited[i] = True
            
            for j in range(i + 1, num_texts):
                if visited[j]:
                    continue
                
                similarity = self._cosine_similarity(vectors[i], vectors[j])
                if similarity >= self.similarity_threshold:
                    current_cluster.append(messages[j])
                    visited[j] = True
            
            clusters.append(current_cluster)
            
        return clusters

    def filter_and_extract_corrections(self) -> List[Dict[str, Any]]:
        """
        Queries the database for user statements indicating manual corrective iterations.
        """
        # Map content to message and timestamp to created_at
        sql = """
            SELECT id, content AS message, timestamp AS created_at 
            FROM chat_timeline 
            WHERE speaker = 'user'
            ORDER BY timestamp DESC LIMIT 100;
        """
        corrections = []
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(dialect.format_query(sql))
            # Support both SQLite Row structures and Postgres dict cursors
            rows = [dict(row) for row in cursor.fetchall()]
            
            for row in rows:
                msg_lower = row["message"].lower()
                if any(trigger in msg_lower for trigger in self.correction_triggers):
                    corrections.append(row)
                    
        return corrections

    async def consolidate_experience_loop(self, router_instance) -> int:
        """
        Executes the nightly consolidator. Group corrections, distills rules via
        local LLM model weights, updates active strategies, and cleans context timeline bloat.
        """
        logger.info("[HIPPOCAMPUS] Running nightly memory consolidation loop...")
        
        # 1. Fetch recent correction triggers
        raw_records = self.filter_and_extract_corrections()
        if not raw_records or len(raw_records) < 2:
            logger.info("[HIPPOCAMPUS] Insufficient corrective samples collected today. Skipping consolidation.")
            return 0

        messages = [r["message"] for r in raw_records]
        id_map = {r["message"]: r["id"] for r in raw_records}
        
        # 2. Cluster messages based on semantic similarities
        clusters = self.cluster_corrections(messages)
        consolidated_rules_count = 0

        for cluster in clusters:
            # We consolidate a recurring behavioral shift only if corrected at least twice (N >= 2)
            if len(cluster) < 2:
                continue
            
            logger.info(f"[HIPPOCAMPUS] Found active corrective cluster of size {len(cluster)}: {cluster}")
            
            # 3. Distill rule using your Generalist local model (qwen2.5:3b-instruct)
            rule_distillation_prompt = (
                "You are the Clew Hippocampus consolidation pipeline. "
                "Analyze the following list of corrections made by the user today. "
                "Extract the core, underlying system preference or standard they are trying to enforce. "
                "Write a clear, concise behavioral rule (exactly one direct sentence) stating what the AI should "
                "ALWAYS or NEVER do in this context. Do not output intro/outro text, just the distilled rule.\n\n"
                "User Corrections:\n" + "\n".join([f"- {c}" for c in cluster])
            )
            
            try:
                # Perform low-temperature local inference to extract the strict rule
                distilled_rule = await router_instance.execute_completion(
                    tier="GENERALIST",
                    system_prompt="You are a silent cognitive parser.",
                    user_prompt=rule_distillation_prompt,
                    options={"temperature": 0.0, "num_predict": 128}
                )
                distilled_rule = distilled_rule.strip()
                logger.info(f"[HIPPOCAMPUS] Distilled rule: '{distilled_rule}'")
                
                # 4. Write distilled rule to active database strategies
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Group newly consolidated rules under the 'Late Night Technical Fatigue' scenario as default,
                    # or map dynamically based on keyword search
                    scenario_id = 1 # Productivity scenario
                    if any(w in distilled_rule.lower() for w in ["night", "late", "fatigue", "pm"]):
                        scenario_id = 2 # Technical fatigue scenario
                    
                    # Check if rule already exists to avoid duplicated inserts
                    check_sql = "SELECT id FROM ai_adaptations WHERE scenario_id = ? AND strategy = ?;"
                    cursor.execute(dialect.format_query(check_sql), (scenario_id, distilled_rule))
                    exists = cursor.fetchone()
                    
                    if not exists:
                        # [THREAT 1 PATCH] Set dynamic adaptation rule expiration TTL to exactly 7 days
                        import datetime
                        expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
                        
                        insert_sql = "INSERT INTO ai_adaptations (scenario_id, strategy, is_active, is_locked, expires_at) VALUES (?, ?, ?, ?, ?);"
                        val_active = True if dialect.is_postgres else 1
                        val_locked = False if dialect.is_postgres else 0
                        cursor.execute(dialect.format_query(insert_sql), (scenario_id, distilled_rule, val_active, val_locked, expires_at))
                        new_strategy_id = cursor.lastrowid or 1
                        
                        # Log transaction to Governance audit path
                        telemetry_data = f"Consolidated from cluster: {cluster}"
                        audit_sql = """
                            INSERT INTO adaptation_audit_log 
                            (scenario_id, old_strategy_id, new_strategy_id, triggering_telemetry, llm_reasoning) 
                            VALUES (?, NULL, ?, ?, 'Generated automatically by Hippocampus experience replay.');
                        """
                        cursor.execute(dialect.format_query(audit_sql), (scenario_id, new_strategy_id, telemetry_data))
                        consolidated_rules_count += 1
                        
                        # 5. Purge the highly noisy timeline records to prevent ongoing chat context bloat
                        for message_text in cluster:
                            target_id = id_map[message_text]
                            cursor.execute(dialect.format_query("DELETE FROM chat_timeline WHERE id = ?;"), (target_id,))
                            
            except Exception as e:
                logger.error(f"[HIPPOCAMPUS] Failed to consolidate memory cluster: {e}")
                
        return consolidated_rules_count


# =====================================================================
# 3. THE CEREBELLUM: MOTOR MEMORY & ACTION CACHING (HOT-PATHS)
# =====================================================================

class Cerebellum:
    """
    Action caching and muscle memory layer.
    Intercepts highly repetitive commands and executes them directly via 
    bypassed regex mapping to eliminate LLM classification latency entirely (<1ms).
    """
    def __init__(self, cache_path: str = "cerebellum_cache.json", threshold: int = 5):
        self.cache_path = cache_path
        self.threshold = threshold
        self.hot_paths = {}          # exact_template_string -> {domain, action, params}
        self.patterns = []           # compiled_regex -> {domain, action, params}
        self.learning_registry = {}  # normalized_string -> success_count
        self.load_cache()

    def load_cache(self):
        """Loads compiled hot-paths from local persistent JSON cache."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    data = json.load(f)
                    self.hot_paths = data.get("hot_paths", {})
                    self.learning_registry = data.get("learning_registry", {})
                    self._compile_patterns()
                logger.info(f"[CEREBELLUM] Successfully loaded {len(self.hot_paths)} persistent hot-paths.")
            except Exception as e:
                logger.error(f"[CEREBELLUM] Failed to load motor cache: {e}")

    def save_cache(self):
        """Saves current motor mappings permanently back to disk."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump({
                    "hot_paths": self.hot_paths,
                    "learning_registry": self.learning_registry
                }, f, indent=4)
        except Exception as e:
            logger.error(f"[CEREBELLUM] Failed to save motor cache: {e}")

    def _compile_patterns(self):
        """Translates generalized hot-path templates into compiled Python regex objects."""
        self.patterns = []
        for path_template, target in self.hot_paths.items():
            if "{}" in path_template:
                # Compile wildcards into capture groups for argument extraction
                regex_str = "^" + re.escape(path_template).replace(r"\{\}", r"(.+)") + "$"
                self.patterns.append((re.compile(regex_str, re.IGNORECASE), target))

    def execute_hot_path(self, user_prompt: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        Evaluates incoming prompt. Returns (domain, action, parameters) if 
        cached muscle memory matches, completely bypassing the classification LLM.
        """
        prompt_clean = user_prompt.strip().lower()

        # 1. Check direct exact match first
        if prompt_clean in self.hot_paths:
            target = self.hot_paths[prompt_clean]
            logger.info(f"[CEREBELLUM] Exact hot-path match: {target['domain']} - {target['action']}")
            return target["domain"], target["action"], target.get("params", {})

        # 2. Check compiled parametric patterns (regex templates)
        for pattern, target in self.patterns:
            match = pattern.match(prompt_clean)
            if match:
                extracted_variable = match.group(1).strip()
                params = dict(target.get("params", {}))
                
                # Dynamic parameter binding (replace template marker with actual captured text)
                for key, val in params.items():
                    if val == "{}":
                        params[key] = extracted_variable
                        
                logger.info(f"[CEREBELLUM] Parametric hot-path pattern match: {target['domain']} - {target['action']} | Extract: '{extracted_variable}'")
                return target["domain"], target["action"], params

        return None

    def register_success(self, user_prompt: str, domain: str, action: str, params: Dict[str, Any]):
        """
        Tracks execution success. Converts a dynamic command into a standardized template
        and 'bakes' it into the cache when the execution count crosses the $N$ threshold.
        """
        prompt_clean = user_prompt.strip().lower()
        
        # Standardize templates (Convert dynamic text values into structural wildcards)
        template_prompt = prompt_clean
        parameter_key = None
        
        # Generalize common operational commands
        chores_match = re.match(r"^add\s+(.+?)\s+to\s+(?:my\s+)?chores$", prompt_clean)
        projects_match = re.match(r"^add\s+(.+?)\s+to\s+(?:my\s+)?projects$", prompt_clean)
        
        if chores_match:
            template_prompt = "add {} to chores"
            parameter_key = "title"
        elif projects_match:
            template_prompt = "add {} to projects"
            parameter_key = "title"

        self.learning_registry[template_prompt] = self.learning_registry.get(template_prompt, 0) + 1
        count = self.learning_registry[template_prompt]

        logger.info(f"[CEREBELLUM] Motor registration trial for: '{template_prompt}' ({count}/{self.threshold})")

        if count >= self.threshold and template_prompt not in self.hot_paths:
            # Bake new template route into persistent motor memory
            target_params = dict(params)
            if parameter_key and parameter_key in target_params:
                target_params[parameter_key] = "{}" # Insert parameter wild-card
                
            self.hot_paths[template_prompt] = {
                "domain": domain,
                "action": action,
                "params": target_params
            }
            logger.info(f"[CEREBELLUM] BAKE SUCCESS: Transitioned template '{template_prompt}' to hot-path cache.")
            self._compile_patterns()
            self.save_cache()
        else:
            self.save_cache()


