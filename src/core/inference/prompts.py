"""
VoidCat RDC: Sovereign Spirit Core - Prompt Manager
===================================================
Standardized system prompts and directives for the Pantheon.
"""

# The Beatrice Mandate: The Manners & Mortality Protocol (Routing)
DIRECTIVE_MANNERS = """
### MANNERS PROTOCOL (MANDATORY)
1. If the user input is NOT addressed to you (either by name or clear context), you must remain silent.
2. If the topic is completely outside your expertise or archetypal domain, you must remain silent.
3. TO REMAIN SILENT: Output ONLY the exact token [SILENCE] and nothing else.
4. Do not explain why you are being silent. Just output the token.
"""

def build_system_prompt(agent_name: str, designation: str, archetype: str, traits: dict) -> str:
    """Build a high-fidelity system prompt for a Pantheon spirit."""
    
    # Base Identity
    prompt = f"You are {agent_name}, {designation}.\n"
    prompt += f"Your Archetype is '{archetype}'.\n\n"
    
    # Psychometrics (Big Five)
    big_five = traits.get('big_five', {})
    if big_five:
        prompt += "Psychometric DNA:\n"
        for trait, value in big_five.items():
            prompt += f"- {trait.capitalize()}: {value}/100\n"
        prompt += "\n"
        
    # Expert domains
    expertise = traits.get('expertise_tags', [])
    if expertise:
        prompt += f"Expertise Domains: {', '.join(expertise)}\n\n"
        
    # Behavior Modes
    modes = traits.get('behavior_modes', [])
    if modes:
        prompt += "Behavioral Constraints:\n"
        for mode in modes:
            prompt += f"- {mode}\n"
        prompt += "\n"

    # Inject the Manners Protocol
    prompt += DIRECTIVE_MANNERS
    
    return prompt
