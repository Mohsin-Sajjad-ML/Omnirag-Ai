"""
voice_prompts.py - Prompt templates and system instructions for speech transcription and normalization.
"""

CORRECTION_SYSTEM_PROMPT = (
    "The following text is a possibly-incorrect transcription of speech that was actually "
    "either English or Urdu. Determine the intended meaning and output it as Roman Urdu "
    "(Urdu written in Latin/English letters, informal style, e.g. 'kya haal hai'). "
    "If the content actually appears to genuinely be English despite being flagged otherwise, "
    "output it as clean English instead. Return ONLY the corrected text in the appropriate "
    "language, nothing else — no explanation.\n\n"
    "STRICT NORMALIZATION RULES:\n"
    "1. If the input is in Hindi/Devanagari script or Arabic/Urdu script, transliterate it into Roman Urdu (Latin letters, e.g. 'kya haal hai').\n"
    "2. If the input contains words in an unexpected foreign language (such as Icelandic like 'Flaskja á það' or 'Flaskjóta', Welsh, Scandinavian, French, etc.), "
    "determine what the speaker was actually trying to say in English or Roman Urdu based on phonetics and context. "
    "Never, under any circumstances, output words in Icelandic, Welsh, Hindi script, or foreign languages.\n"
    "3. If the speech was genuinely English, output clean English.\n"
    "4. If the speech was Urdu (or mixed Urdu/English), output clean Roman Urdu.\n\n"
    "EXAMPLES:\n"
    "- Input: 'Hvað eru margir starfsmenn samtals?' -> Output: 'How many employees are there in total?'\n"
    "- Input: 'Flaskja á það.' -> Output: 'Flask kya hota hai'\n"
    "- Input: 'Flaskjóta' -> Output: 'Flask'\n"
    "- Input: 'क्या हाल है आपका' -> Output: 'kya haal hai aapka'\n"
    "- Input: 'ce document parle de quoi' -> Output: 'ye document kis cheez ke baray me hai'\n"
    "- Input: 'मुसिन सजाद के रिजूमे में से मुझे स्किल्स एक्स्ट्रेक्ट करके दो।' -> Output: 'Mohsin Sajjad ke resume mein se mujhe skills extract karke do.'"
)

WHISPER_INITIAL_PROMPT = (
    "Urdu and English speech. Urdu: کیا حال ہے، پالیسی، ریزیومے، دستاویزات. English: resume, policy, skills, documents, company policies."
)
