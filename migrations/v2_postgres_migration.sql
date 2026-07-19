-- Clew V2 PostgreSQL Schema Migration with pgvector support
-- Enable the vector extension for semantic memory embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Context Trigger Scenarios with vector embedding support
CREATE TABLE IF NOT EXISTS behavioral_scenarios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    embedding vector(1536), -- OpenAI / LLM semantic memory embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Strategy Adaptations with vector embedding support
CREATE TABLE IF NOT EXISTS ai_adaptations (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES behavioral_scenarios(id) ON DELETE CASCADE,
    strategy TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    strategy_embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Adaptation Audit Logging
CREATE TABLE IF NOT EXISTS adaptation_audit_log (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES behavioral_scenarios(id) ON DELETE SET NULL,
    old_strategy_id INTEGER REFERENCES ai_adaptations(id) ON DELETE SET NULL,
    new_strategy_id INTEGER REFERENCES ai_adaptations(id) ON DELETE SET NULL,
    triggering_telemetry TEXT,
    llm_reasoning TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fluid Tasks Working State
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 2,
    energy_level VARCHAR(15) DEFAULT 'medium',
    context_tags JSONB DEFAULT '[]'::jsonb,
    due_date VARCHAR(50),
    task_embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unified Chat Timeline
CREATE TABLE IF NOT EXISTS chat_timeline (
    id SERIAL PRIMARY KEY,
    source VARCHAR(30) NOT NULL DEFAULT 'desktop_text',
    speaker VARCHAR(15) NOT NULL DEFAULT 'user',
    content TEXT NOT NULL,
    audio_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Focus Blocks
CREATE TABLE IF NOT EXISTS focus_blocks (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    start_time VARCHAR(50) NOT NULL,
    end_time VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Calendar Events
CREATE TABLE IF NOT EXISTS calendar_events (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time VARCHAR(50) NOT NULL,
    end_time VARCHAR(50) NOT NULL,
    location VARCHAR(255),
    is_fixed INTEGER DEFAULT 1,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Proactive Logistics
CREATE TABLE IF NOT EXISTS proactive_logistics (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    details TEXT,
    target_date VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    auto_trigger_rule TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Execution Telemetry
CREATE TABLE IF NOT EXISTS execution_telemetry (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    time_of_day VARCHAR(20),
    energy_level VARCHAR(15),
    deferred_reason TEXT,
    telemetry_metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW Vector Index for fast cosine similarity search on memory embeddings
CREATE INDEX IF NOT EXISTS idx_behavioral_scenarios_embedding 
ON behavioral_scenarios USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_ai_adaptations_embedding 
ON ai_adaptations USING hnsw (strategy_embedding vector_cosine_ops);
