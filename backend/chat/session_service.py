"""
session_service.py - Session management, transcripts, exports, and context summaries.
"""
import html
import io
import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, Response, status
from sqlalchemy.orm import Session
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
except ImportError:
    letter = None
    getSampleStyleSheet = None
    ParagraphStyle = None
    colors = None
    SimpleDocTemplate = None
    Paragraph = None
    Spacer = None
    HRFlowable = None


from backend.database.models import User, ChatSession, ChatMessage
from backend.chat.schemas import (
    SessionResponse,
    SessionItemResponse,
    MessageItemResponse,
    Citation,
    MessageResponse,
)
from backend.chat.llm_service import (
    DEFAULT_GROQ_MODEL,
    classify_language,
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


def create_chat_session(
    clerk_user_id: str,
    db: Session,
) -> SessionResponse:
    """
    Creates a new conversation session record in SQLite.
    """
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        user = User(clerk_user_id=clerk_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    session = ChatSession(
        clerk_user_id=clerk_user_id,
        title="New Chat",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        session_id=session.id,
        id=session.id,
        title=session.title,
        pinned=bool(getattr(session, "pinned", False)),
        created_at=session.created_at,
    )


def update_chat_session(
    session_id: int,
    clerk_user_id: str,
    title: str,
    db: Session,
) -> SessionItemResponse:
    """
    Updates the title of a chat session.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this session."
        )

    session.title = title
    db.commit()
    db.refresh(session)

    return SessionItemResponse(
        id=session.id,
        session_id=session.id,
        title=session.title,
        pinned=bool(getattr(session, "pinned", False)),
        created_at=session.created_at,
    )


def list_user_sessions(
    clerk_user_id: str,
    db: Session,
) -> List[SessionItemResponse]:
    """
    Retrieves all chat sessions for the authenticated user.
    """
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.clerk_user_id == clerk_user_id)
        .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        .all()
    )

    return [
        SessionItemResponse(
            id=s.id,
            session_id=s.id,
            title=s.title,
            pinned=bool(getattr(s, "pinned", False)),
            created_at=s.created_at,
        )
        for s in sessions
    ]


def get_session_messages(
    session_id: int,
    clerk_user_id: str,
    db: Session,
) -> List[MessageItemResponse]:
    """
    Fetches the full message transcript for a session.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this session."
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )

    results = []
    for msg in messages:
        citations = None
        if msg.citations:
            try:
                raw_citations = json.loads(msg.citations)
                citations = [Citation(**c) for c in raw_citations]
            except Exception as parse_err:
                logger.warning("Could not parse citations for message %s: %s", msg.id, parse_err)
                citations = []
        persisted_source = getattr(msg, "source", None)
        if not persisted_source or persisted_source in ("document", "general_knowledge"):
            persisted_source = "rag" if citations else "llm_api"

        results.append(
            MessageItemResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                citations=citations,
                is_fallback=msg.is_fallback,
                source=persisted_source,
                response_language=getattr(msg, "response_language", None) or classify_language(msg.content),
                created_at=msg.created_at,
            )
        )
    return results


def delete_chat_session(
    session_id: int,
    clerk_user_id: str,
    db: Session,
) -> MessageResponse:
    """
    Deletes the session and all associated messages.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this session."
        )

    db.delete(session)
    db.commit()

    return MessageResponse(message="Session and its messages deleted successfully")


def pin_chat_session(
    session_id: int,
    clerk_user_id: str,
    pinned: bool,
    db: Session,
) -> SessionItemResponse:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this session."
        )
    session.pinned = pinned
    db.commit()
    db.refresh(session)
    return SessionItemResponse(
        id=session.id,
        session_id=session.id,
        title=session.title,
        pinned=bool(session.pinned),
        created_at=session.created_at,
    )


def duplicate_chat_session(
    session_id: int,
    clerk_user_id: str,
    db: Session,
) -> SessionResponse:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to duplicate this session."
        )

    new_session = ChatSession(
        clerk_user_id=clerk_user_id,
        title=f"{session.title} (Copy)",
        pinned=False,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    existing_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    for m in existing_msgs:
        copied_msg = ChatMessage(
            session_id=new_session.id,
            role=m.role,
            content=m.content,
            citations=m.citations,
            is_fallback=m.is_fallback,
            response_language=m.response_language,
            created_at=m.created_at,
        )
        db.add(copied_msg)
    if existing_msgs:
        db.commit()

    return SessionResponse(
        session_id=new_session.id,
        id=new_session.id,
        title=new_session.title,
        pinned=bool(new_session.pinned),
        created_at=new_session.created_at,
    )


def generate_chat_context_summary(messages: List[ChatMessage], session_title: str) -> str:
    """
    Generates a dense, compressed context summary of the conversation.
    This enables a user to download it and provide it to a fresh chat session to continue
    seamlessly without repeating the entire conversation.
    """
    if not messages:
        return "No messages in this chat session to summarize."

    conversation_dialogue = []
    for msg in messages:
        role = "User" if msg.role == "user" else "OmniRAG Assistant"
        conversation_dialogue.append(f"{role}: {msg.content.strip()}")

    dialogue_str = "\n\n".join(conversation_dialogue)
    if len(dialogue_str) > 12000:
        dialogue_str = dialogue_str[:12000] + "\n...[truncated for brevity]..."

    system_prompt = (
        "You are an expert conversational AI context synthesizer. "
        "Your task is to produce a high-density, compressed context brief of the provided chat session. "
        "The purpose of this output is for the user to download it and paste it into a brand new chat "
        "to continue the discussion seamlessly without losing background, context, decisions, or progress.\n\n"
        "Organize the brief clearly with these sections:\n"
        "### 1. Conversation Goal & Topic\n"
        "(1-2 sentences on what the user was achieving or inquiring about)\n\n"
        "### 2. Key Background & Established Context\n"
        "(Bullet points of core facts, constraints, document references, or technical context established)\n\n"
        "### 3. Decisions, Solutions & Insights\n"
        "(Bullet points of solutions provided, answers confirmed, and key conclusions reached)\n\n"
        "### 4. Continuation Status & Next Steps\n"
        "(Current state of the conversation and a concise prompt to paste into a new chat to continue seamlessly)\n\n"
        "Keep it concise, objective, and dense with information. Do NOT include greetings or meta-commentary."
    )

    try:
        groq_client = _get_active_groq_client()
        response = groq_client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Session Title: {session_title}\n\nTranscript:\n{dialogue_str}"},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        content = response.choices[0].message.content.strip()
        if content:
            return content
    except Exception as exc:
        logger.warning("Groq context summary failed (%s). Falling back to heuristic summary.", exc)

    # Deterministic heuristic fallback if Groq is unavailable, unconfigured, or rate-limited
    user_queries = [m.content.strip() for m in messages if m.role == "user"]
    asst_replies = [m.content.strip() for m in messages if m.role == "assistant"]

    heuristic_lines = [
        "### 1. Conversation Goal & Topic",
        f"Discussion on: {session_title}.",
        "",
        "### 2. Key Background & Established Context",
        f"- Total exchanges: {len(messages)} messages recorded in session.",
    ]
    if user_queries:
        heuristic_lines.append(f"- Initial topic requested: {user_queries[0][:200]}")

    heuristic_lines.extend([
        "",
        "### 3. Decisions, Solutions & Insights",
    ])
    for i, a in enumerate(asst_replies[:6], 1):
        clean_snippet = a.replace("\n", " ")[:160]
        heuristic_lines.append(f"- Point {i}: {clean_snippet}...")

    last_q = user_queries[-1] if user_queries else "N/A"
    heuristic_lines.extend([
        "",
        "### 4. Continuation Status & Next Steps",
        f"- Last user inquiry: \"{last_q[:160]}\"",
        "- Prompt to continue in new chat: \"Continue our previous discussion using the context above. We were discussing the points and solutions outlined here.\""
    ])
    return "\n".join(heuristic_lines)


def export_chat_session(
    session_id: int,
    clerk_user_id: str,
    format: str,
    mode: str = "full",
    db: Session = None,
) -> Response:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export this session."
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )

    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', session.title.strip())[:40] or "chat"
    header_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if mode in ("context", "summary"):
        context_text = generate_chat_context_summary(messages, session.title)

        if format == "txt":
            lines = [
                "=" * 60,
                "OmniRAG AI - Compressed Chat Context (For Continuation)",
                f"Session: {session.title}",
                f"Exported: {header_time}",
                "Purpose: Paste this context into a new chat to continue seamlessly.",
                "=" * 60,
                "",
                context_text,
            ]
            txt_body = "\n".join(lines)
            return Response(
                content=txt_body.encode("utf-8"),
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{safe_title}_context.txt"'},
            )

        elif format == "pdf":
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=48,
                leftMargin=48,
                topMargin=48,
                bottomMargin=48,
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'ContextTitle',
                parent=styles['Heading1'],
                fontSize=18,
                leading=22,
                textColor=colors.HexColor('#312e81'),
                spaceAfter=4,
            )
            sub_style = ParagraphStyle(
                'ContextSub',
                parent=styles['Normal'],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor('#64748b'),
                spaceAfter=6,
            )
            banner_style = ParagraphStyle(
                'ContextBanner',
                parent=styles['Normal'],
                fontSize=9,
                leading=13,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#0284c7'),
                spaceAfter=10,
            )
            heading_style = ParagraphStyle(
                'ContextHeading',
                parent=styles['Normal'],
                fontSize=11,
                leading=15,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#4338ca'),
                spaceBefore=10,
                spaceAfter=4,
            )
            body_style = ParagraphStyle(
                'ContextBody',
                parent=styles['Normal'],
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor('#1e293b'),
                spaceAfter=6,
            )

            story = [
                Paragraph(f"<b>OmniRAG AI:</b> Compressed Chat Context", title_style),
                Paragraph(f"Session: <b>{html.escape(session.title)}</b> • Exported on {header_time}", sub_style),
                Paragraph("<b>Purpose:</b> Condensed high-signal summary designed to paste into a new chat to continue seamlessly.", banner_style),
                HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#cbd5e1'), spaceAfter=12),
            ]

            for block in context_text.split("\n\n"):
                block_clean = block.strip()
                if not block_clean:
                    continue
                if block_clean.startswith("#"):
                    heading_text = block_clean.lstrip("#").strip()
                    story.append(Paragraph(html.escape(heading_text), heading_style))
                else:
                    block_escaped = html.escape(block_clean).replace("\n", "<br/>")
                    block_escaped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', block_escaped)
                    story.append(Paragraph(block_escaped, body_style))
                    story.append(Spacer(1, 4))

            doc.build(story)
            buffer.seek(0)
            pdf_bytes = buffer.getvalue()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{safe_title}_context.pdf"'},
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Supported: 'txt' or 'pdf'")

    # mode == "full" (full transcript)
    if format == "txt":
        lines = [
            "OmniRAG AI - Chat Session Transcript",
            f"Title: {session.title}",
            f"Exported: {header_time}",
            "=" * 60,
            "",
        ]
        for msg in messages:
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if msg.created_at else "N/A"
            role_display = "User" if msg.role == "user" else "OmniRAG Assistant"
            lines.append(f"[{ts}] {role_display}:")
            lines.append(f"{msg.content}")
            lines.append("")
        txt_body = "\n".join(lines)
        return Response(
            content=txt_body.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.txt"'},
        )

    elif format == "pdf":
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=48,
            leftMargin=48,
            topMargin=48,
            bottomMargin=48,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'SessionTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#312e81'),
            spaceAfter=4,
        )
        sub_style = ParagraphStyle(
            'SessionSub',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=12,
        )
        user_header_style = ParagraphStyle(
            'UserH',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#4338ca'),
            spaceBefore=8,
            spaceAfter=3,
        )
        assistant_header_style = ParagraphStyle(
            'AsstH',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#7c3aed'),
            spaceBefore=8,
            spaceAfter=3,
        )
        msg_body_style = ParagraphStyle(
            'MsgText',
            parent=styles['Normal'],
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=6,
        )

        story = [
            Paragraph(f"<b>OmniRAG AI:</b> {html.escape(session.title)}", title_style),
            Paragraph(f"Exported on {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}", sub_style),
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#cbd5e1'), spaceAfter=12),
        ]

        if not messages:
            story.append(Paragraph("<i>No messages in this chat session.</i>", sub_style))

        for msg in messages:
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M UTC") if msg.created_at else ""
            if msg.role == "user":
                story.append(Paragraph(f"User • {ts}", user_header_style))
            else:
                story.append(Paragraph(f"OmniRAG Assistant • {ts}", assistant_header_style))
            content_escaped = html.escape(msg.content).replace("\n", "<br/>")
            story.append(Paragraph(content_escaped, msg_body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'},
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Supported: 'txt' or 'pdf'")
