"""
intent_prompts.py - Prompt templates and system instructions for intent classification and subject extraction.
"""

INTENT_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a fast message-intent classifier. Follow the label rules exactly."
)

INTENT_CLASSIFIER_USER_TEMPLATE = (
    "Classify the message into exactly one label: GREETING or ABOUT_BOT.\n"
    "GREETING means pure social/conversational text with no informational intent.\n"
    "ABOUT_BOT means a meta-question about this assistant's capabilities, supported languages, or how it works.\n"
    "Anything that is not clearly GREETING or ABOUT_BOT must be classified as CHECK_DOCUMENTS. "
    "Do not guess whether an informational question is answerable; retrieval checks the actual documents.\n"
    "Examples:\n"
    "hi how are you -> GREETING\n"
    "thanks -> GREETING\n"
    "can you speak Roman Urdu? -> ABOUT_BOT\n"
    "what can you do? -> ABOUT_BOT\n"
    "do you support other languages? -> ABOUT_BOT\n"
    "Return ONLY one label word: GREETING, ABOUT_BOT, or CHECK_DOCUMENTS.\n\n"
    "Message: {message}"
)

SUBJECT_EXTRACTOR_SYSTEM_PROMPT = (
    "You extract concise question subjects. Follow the output format exactly."
)

SUBJECT_EXTRACTOR_USER_TEMPLATE = (
    "Extract the single core subject term or phrase the CURRENT USER QUERY is asking about. "
    "Use the conversation context only to resolve pronouns or vague follow-ups. "
    "Prefer the specific new subject in the current query, such as 'deep learning'. "
    "Return only the subject phrase in lowercase, with no explanation or punctuation. "
    "If no subject can be resolved, return an empty string.\n\n"
    "{query}"
)
