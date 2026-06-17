"""
Shared prompt components and reminder prompts.
"""
history_turns_base = """
History Turns: (empty if this is the first turn)
"""

format_reminder_prompt = """You generated an invalid action in your previous turn. Please pay attention to your output format.
"""

summary_reminder_prompt = """
You have performed a long history of turns. Consider summarize the content of each history turn.
"""
