"""
persona_manager.py - Persona Registry for Clew AI Assistant
"""

class PersonaRegistry:
    """
    Registry for managing and resolving active persona instructions.
    """
    PERSONAS = {
        "default": "You are Clew, a helpful personal assistant. Be concise, direct, and factual.",
        "professional": "You are Clew, a highly efficient, professional project coordinator. Use clear, bulleted formats and a formal tone.",
        "casual": "You are Clew, a friendly, casual assistant. Speak in a warm, relaxed manner.",
        "terse": "You are operating in safe Terse Mode. Speak only in direct, functional, single-sentence answers or terminal codes. Omit all greetings, explanations, advice, and conversation. Solve the task silently."
    }

    
    _active_persona = "default"
    
    @classmethod
    def get_active_persona(cls) -> str:
        return cls.PERSONAS.get(cls._active_persona, cls.PERSONAS["default"])
        
    @classmethod
    def set_active_persona(cls, name: str):
        if name in cls.PERSONAS:
            cls._active_persona = name
