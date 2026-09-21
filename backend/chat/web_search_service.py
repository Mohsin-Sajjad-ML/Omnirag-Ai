"""
web_search_service.py - Real-time web search and hybrid RAG+Web synthesis.
"""
from langfuse import observe

import logging
import re
import sys
from typing import List, Optional

from backend.chat.llm_service import (
    DEFAULT_GROQ_MODEL,
    FALLBACK_GROQ_MODELS,
    get_groq_client,
)

logger = logging.getLogger(__name__)


def _get_active_groq_client():
    mod_chat = sys.modules.get("backend.chat")
    if mod_chat and hasattr(mod_chat, "get_groq_client"):
        return getattr(mod_chat, "get_groq_client")()
    mod_llm = sys.modules.get("backend.llm")
    if mod_llm and hasattr(mod_llm, "get_groq_client"):
        return getattr(mod_llm, "get_groq_client")()
    return get_groq_client()


def _is_conversational_meta_instruction(query: str) -> bool:
    """
    Detects if the user query is an instruction to modify, format, shorten, summarize,
    simplify, or clarify previous responses rather than asking an independent new factual query.
    """
    q = query.lower().strip()
    words = re.findall(r"[a-z0-9']+", q)
    if not words:
        return False

    meta_patterns = [
        r"\b(?:short|shorten|shorter)\b",
        r"\btoo long\b",
        r"\b(?:dont|do not) explain (?:it )?too long\b",
        r"\bgive (?:me )?(?:a )?short answer\b",
        r"\ba bit long\b",
        r"\bmake it\b",
        r"\bin short\b",
        r"\bsummariz",
        r"\bin brief\b",
        r"\bconcise\b",
        r"\bsimplify\b",
        r"\bin simple words\b",
        r"\bbullet points?\b",
        r"\bone line\b",
        r"\bexplain more\b",
        r"\belaborate\b",
        r"\bgive (?:an )?example\b",
        r"\bwhat do you mean\b",
    ]
    if any(re.search(pat, q) for pat in meta_patterns):
        return True

    if len(words) <= 5 and any(w in words for w in ["short", "shorter", "brief", "long", "summarize", "simplify"]):
        return True

    return False


@observe(as_type="generation", name="general-answer")
def _call_groq_general(query: str, history: Optional[List[dict]] = None, client=None) -> str:
    """
    Generates a substantive answer using the standard configured Groq model.
    Includes conversation history for multi-turn conversational coherence.
    Never declines: acts as a general-purpose AI assistant in the matching user language/script.
    """
    groq_client = client or _get_active_groq_client()
    system_prompt = (
        "You are OmniRAG AI, a knowledgeable, direct, and helpful conversational AI assistant.\n"
        "Conversational continuity instructions:\n"
        "- Always maintain full context of earlier messages in this conversation.\n"
        "- If the user asks to shorten, simplify, summarize, clarify, elaborate, rephrase, or format previous messages "
        "(e.g., 'short it', 'too long', 'make it shorter', 'give me short answer', 'explain more', 'what does that mean?'):\n"
        "  * You MUST immediately apply their instruction directly to the most recent relevant topic or response.\n"
        "  * NEVER ask clarifying questions like 'which answer would you like shortened?' or 'what would you like a short answer about?' "
        "when the conversation history clearly provides the subject. Deliver the shortened or modified answer directly.\n"
        "Language & script matching instructions:\n"
        "- You MUST respond in the EXACT same language and script that the user used to ask the question.\n"
        "- If the user asks in English, reply in English.\n"
        "- If the user asks in Roman Urdu (Urdu written in Latin alphabet), you MUST reply in natural Roman Urdu.\n"
        "- If the user asks in Urdu (Arabic/Nastaliq script), reply in Urdu.\n"
        "- Never hallucinate unrelated scripts or languages (do not use Hindi/Devanagari unless explicitly asked in Devanagari).\n"
        "Always provide a complete, substantive response."
    )
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-6:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    models_to_try = [DEFAULT_GROQ_MODEL] + [m for m in FALLBACK_GROQ_MODELS if m != DEFAULT_GROQ_MODEL]
    for model in models_to_try:
        try:
            resp = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            try:
                usage = None
                if hasattr(resp, "usage") and resp.usage:
                    usage = {
                        "input": resp.usage.prompt_tokens,
                        "output": resp.usage.completion_tokens,
                        "total": resp.usage.total_tokens,
                    }
                from backend.config import get_langfuse_client
                get_langfuse_client().update_current_generation(
                    model=model,
                    usage_details=usage,
                )
            except Exception:
                pass
            content = resp.choices[0].message.content or ""
            if content.strip():
                return content.strip()
        except Exception as err:
            logger.warning("Groq general model '%s' failed: %s. Trying fallback model...", model, err)

    return "I am OmniRAG AI. I am ready to assist you. Please let me know what you would like to discuss."


def _derive_search_query(query: str, history: Optional[List[dict]] = None, client=None) -> str:
    """
    If the user query is a follow-up or re-prompt (e.g. 'thats not right answer search the web and answer again'),
    extract or synthesize the search topic from conversation history so the search engine receives a targeted query.
    """
    if not history:
        return query

    user_msgs = [m.get("content", "").strip() for m in history if isinstance(m, dict) and m.get("role") == "user" and m.get("content")]
    if not user_msgs:
        return query

    lower_q = query.lower().strip()
    follow_up_cues = [
        "again", "search", "google", "web", "wrong", "not right", "not write",
        "recheck", "what about", "who won", "result", "tell me more", "update", "latest"
    ]
    is_followup = any(cue in lower_q for cue in follow_up_cues) or len(lower_q.split()) <= 4
    if not is_followup:
        return query

    # Try fast model query derivation
    groq_client = client or _get_active_groq_client()
    try:
        recent_context = []
        for m in history[-4:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
                recent_context.append(f"{m['role'].upper()}: {m['content']}")
        prompt = (
            "Given the conversation context and current user request, output the single best, concise web search query (3 to 8 words) "
            "to find the necessary current factual information on the web. Output ONLY the search query text without quotes or explanations.\n\n"
            f"Conversation:\n" + "\n".join(recent_context) + "\n\n"
            f"Current User Request: {query}"
        )
        resp = groq_client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=35,
            temperature=0.0,
        )
        derived = (resp.choices[0].message.content or "").strip().strip('"').strip("'")
        if derived and len(derived) >= 3:
            logger.info("Derived targeted search query: '%s' from user query: '%s'", derived, query)
            return derived
    except Exception as exc:
        logger.warning("LLM search query derivation failed (%s). Using fallback combination.", exc)

    # Heuristic fallback: combine last user topic with query
    return f"{user_msgs[-1]} {query}".strip()


def _perform_web_search(search_query: str, max_results: int = 5) -> str:
    """Executes live web search using DuckDuckGo (ddgs)."""
    try:
        from ddgs import DDGS
        results = list(DDGS().text(search_query, max_results=max_results))
        if not results:
            return ""
        snippets = []
        for r in results:
            title = r.get("title", "").strip()
            snippet = r.get("body", "").strip()
            href = r.get("href", "").strip()
            if snippet:
                snippets.append(f"Title: {title}\nURL: {href}\nSnippet: {snippet}")
        return "\n\n".join(snippets)
    except Exception as exc:
        logger.warning("DDGS live web search error: %s", exc)
        return ""


@observe(as_type="generation", name="web-search-answer")
def _call_groq_web_search(query: str, history: Optional[List[dict]] = None, client=None) -> str:
    """
    Generates an answer using real-time web search capabilities.
    1. Resolves follow-up queries using conversation history.
    2. If the query is an instruction to modify, shorten, summarize, or reformat previous responses,
       applies directly using history without noisy external search.
    3. Performs live search via DuckDuckGo (ddgs).
    4. Synthesizes a current, substantive answer using Groq with live search results.
    5. Falls back gracefully if web search or model encounters API limits.
    """
    groq_client = client or _get_active_groq_client()

    if history and _is_conversational_meta_instruction(query):
        logger.info("Query is conversational meta-instruction ('%s'); applying directly to history without web search.", query)
        return _call_groq_general(query, history=history, client=groq_client)

    search_term = _derive_search_query(query, history=history, client=groq_client)
    logger.info("Performing live web search for: '%s'", search_term)

    web_results = _perform_web_search(search_term, max_results=5)

    system_prompt = (
        "You are OmniRAG AI with real-time web search capabilities.\n"
        "Conversational continuity instructions:\n"
        "- Always maintain full awareness of earlier messages in this conversation.\n"
        "- If the user's question refers to earlier topics or messages, answer seamlessly in context.\n"
        "- If the user asks to shorten, simplify, summarize, or format, apply it directly to the subject discussed.\n"
    )
    if web_results:
        system_prompt += (
            f"\nLive Web Search Results for '{search_term}':\n"
            f"{web_results}\n\n"
            "Use the above live web search results to provide the latest, accurate, and substantive answer.\n"
        )
    system_prompt += (
        "Language & script matching instructions:\n"
        "- You MUST respond in the EXACT same language and script that the user used to ask the question.\n"
        "- If the user asks in English, reply in English.\n"
        "- If the user asks in Roman Urdu (Urdu written in Latin alphabet), you MUST reply in natural Roman Urdu.\n"
        "- If the user asks in Urdu (Arabic/Nastaliq script), reply in Urdu.\n"
        "- Never hallucinate unrelated scripts or languages (do not use Hindi/Devanagari unless explicitly asked in Devanagari).\n"
        "Always provide a complete, substantive response."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-6:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    models_to_try = [DEFAULT_GROQ_MODEL] + [m for m in FALLBACK_GROQ_MODELS if m != DEFAULT_GROQ_MODEL]
    for model in models_to_try:
        try:
            resp = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            try:
                usage = None
                if hasattr(resp, "usage") and resp.usage:
                    usage = {
                        "input": resp.usage.prompt_tokens,
                        "output": resp.usage.completion_tokens,
                        "total": resp.usage.total_tokens,
                    }
                from backend.config import get_langfuse_client
                get_langfuse_client().update_current_generation(
                    model=model,
                    usage_details=usage,
                )
            except Exception:
                pass
            content = resp.choices[0].message.content or ""
            if content.strip():
                return content.strip()
        except Exception as err:
            logger.warning("Groq model '%s' failed in web search synthesis: %s", model, err)

    return _call_groq_general(query, history=history, client=groq_client)


@observe(as_type="generation", name="rag-web-hybrid-answer")
def _generate_hybrid_rag_web_answer(
    query: str,
    subject: str,
    doc_matches: List[dict],
    chat_history: Optional[List[dict]] = None,
    client=None,
) -> str:
    """
    Synthesizes a response when both RAG and Web Search are enabled.
    1. Obtains live web search results/knowledge for the query.
    2. Acknowledges the subject found in the user's document(s).
    3. Provides a full, high-quality answer to the user's query from web search.
    4. Explains how and where the subject appears in the user's document(s),
       including technical skills, projects, and practical applications.
    """
    groq_client = client or _get_active_groq_client()

    # 1. Fetch live web search results for the query
    search_term = _derive_search_query(query, history=chat_history, client=groq_client)
    web_results = _perform_web_search(search_term, max_results=4)

    # 2. Format document context
    doc_sections = []
    doc_names = []
    for match in doc_matches:
        fname = match.get("filename", "Uploaded Document")
        if fname not in doc_names:
            doc_names.append(fname)
        context = match.get("context_text", "")
        doc_sections.append(f"Document: {fname}\nRelevant Context:\n{context}")

    docs_formatted = "\n\n---\n\n".join(doc_sections)
    doc_names_str = ", ".join(doc_names) if doc_names else "your uploaded document"

    system_prompt = (
        "You are OmniRAG AI with integrated Document Analysis (RAG) and Live Web Search.\n"
        f"The user enabled both Document Retrieval and Web Search. "
        f"The subject '{subject or query}' was found in the user's uploaded document(s) ({doc_names_str}), "
        "but the document does not contain an exhaustive textbook definition.\n\n"
        "STRICT FORMATTING REQUIREMENTS:\n"
        "- Use clean, beautiful Markdown formatting with clear visual hierarchy.\n"
        "- Use '### ' for all major section headings.\n"
        "- Separate the 3 main sections with horizontal rules ('---').\n"
        "- EVERY SINGLE explanation point, feature, or project MUST be a formatted Markdown bullet point starting with '- '.\n"
        "- NEVER output bare, floating title lines without a bullet point ('- ') or heading ('### ').\n"
        "- Highlight concepts with bold prefixes, e.g.: '- **Concept Name**: Clear explanation...'\n"
        "- DO NOT output raw HTML (no <table>, <tr>, <td>, <ul>, <li>, or <br>).\n\n"
        "MANDATORY RESPONSE STRUCTURE:\n\n"
        "### 📄 Document Acknowledgment\n"
        f"State clearly in 1 concise sentence that **{subject or query}** was identified in the uploaded document (**{doc_names_str}**).\n\n"
        "---\n\n"
        f"### 🌐 What is {subject or query}?\n"
        "Provide a clean, well-structured explanation using live web knowledge. Every item MUST be a bullet:\n"
        "- **Definition & Overview**: A concise explanation of the technology and its primary paradigms.\n"
        "- **Core Features**: Key strengths, syntax readability, typing system, and standard library.\n"
        "- **Popular Libraries & Frameworks**: Major tools grouped by domain (e.g., Web, Data Science, Machine Learning).\n"
        "- **Typical Use Cases**: Where and why it is commonly utilized in the industry.\n\n"
        "---\n\n"
        f"### 💼 {subject or query} in Your Document ({doc_names_str})\n"
        "Provide a clean, bulleted breakdown of how it appears in the uploaded document:\n"
        f"- **Skills & Qualifications**: Note where and how it is listed (e.g., Technical Skills, Languages, Core Concepts).\n"
        "- **Projects & Practical Experience**:\n"
        "  - **[Project 1 Name]**: Specific role, tools combined with it, and what was accomplished.\n"
        "  - **[Project 2 Name]**: Specific role, tools combined with it, and what was accomplished.\n\n"
        "Language & Tone:\n"
        "- Match the user's language (English or Roman Urdu).\n"
        "- Ensure clean spacing between bullet points so the text is beautiful, organized, and effortless to read."
    )

    user_content = f"User Question: {query}\n\n"
    if web_results:
        user_content += f"Live Web Search Context:\n{web_results}\n\n"
    user_content += f"Uploaded Document Content ({doc_names_str}):\n{docs_formatted}"

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history[-4:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_content})

    models_to_try = [DEFAULT_GROQ_MODEL] + [m for m in FALLBACK_GROQ_MODELS if m != DEFAULT_GROQ_MODEL]
    for model in models_to_try:
        try:
            resp = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            try:
                usage = None
                if hasattr(resp, "usage") and resp.usage:
                    usage = {
                        "input": resp.usage.prompt_tokens,
                        "output": resp.usage.completion_tokens,
                        "total": resp.usage.total_tokens,
                    }
                from backend.config import get_langfuse_client
                get_langfuse_client().update_current_generation(
                    model=model,
                    usage_details=usage,
                )
            except Exception:
                pass
            content = resp.choices[0].message.content or ""
            if content.strip():
                return content.strip()
        except Exception as exc:
            logger.warning("Hybrid synthesis failed on model %s: %s", model, exc)

    return _call_groq_web_search(query, history=chat_history, client=groq_client)
