"""Streamlit UI: upload a persona PDF and chat starts automatically."""
from __future__ import annotations

import hashlib
import os
import re
import uuid

import streamlit as st

from agent import BookChat
from personas import DEFAULT, PERSONAS
from rag import extract_pdf_text

st.set_page_config(
    page_title="Bring Books to Life",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎭 Bring Books to Life")
st.caption(
    "Upload a persona PDF to start chatting automatically. Add a separate knowledge PDF/TXT "
    "if the character should answer from a book or other source document."
)


def infer_persona_name(filename: str) -> str:
    """Turn filenames like Sherlock_Holmes_Persona.pdf into a readable character name."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\b(persona|profile|character|about me|about)\b", " ", stem, flags=re.I)
    stem = re.sub(r"\s+", " ", stem).strip(" -_")
    return stem.title() if stem else "Book Character"


def read_upload(uploaded) -> str:
    raw = uploaded.getvalue()
    if uploaded.name.lower().endswith(".pdf"):
        return extract_pdf_text(raw)
    text = raw.decode("utf-8-sig", errors="replace").strip()
    if not text:
        raise ValueError(f"{uploaded.name} contains no readable text.")
    return text


with st.sidebar:
    st.header("1. Upload persona PDF")
    persona_file = st.file_uploader(
        "Persona profile (required)",
        type=["pdf", "txt"],
        key="persona_upload",
        help="This file defines the character's identity, personality, background, and speaking style.",
    )
    st.header("2. Optional knowledge source")
    knowledge_file = st.file_uploader(
        "Book / reference document (optional)",
        type=["pdf", "txt"],
        key="knowledge_upload",
        help="Upload the story or reference document the persona should use for factual answers. If omitted, the persona file is also used as the knowledge source.",
    )
    st.divider()
    st.caption("Recommended: use a persona PDF for character instructions and a separate book PDF for story facts.")
    reset = st.button("Reset conversation", use_container_width=True, disabled="chat" not in st.session_state)
    if reset:
        st.session_state.pop("chat", None)
        st.session_state.pop("history", None)
        st.session_state.pop("chat_signature", None)
        st.rerun()

if not persona_file:
    st.info("👈 Upload a persona PDF in the sidebar. The chat will open automatically after the document is processed.")
    st.markdown("### How it works\n1. Upload a persona PDF such as `Sherlock_Holmes_Persona.pdf`.\n2. The app reads the character profile and derives the character name from the filename.\n3. The chat initializes automatically—no Start Chat button is required.\n4. Optionally upload a separate book/reference PDF for better grounded answers.")
    st.stop()

# File hashes plus filenames form a stable signature. The agent and embeddings are rebuilt
# only when the selected uploads change, not on every Streamlit rerun caused by chat input.
persona_bytes = persona_file.getvalue()
knowledge_bytes = knowledge_file.getvalue() if knowledge_file else b""
signature = hashlib.sha256(
    persona_file.name.encode("utf-8") + b"\0" + persona_bytes + b"\0" +
    (knowledge_file.name.encode("utf-8") if knowledge_file else b"") + b"\0" + knowledge_bytes
).hexdigest()

if st.session_state.get("chat_signature") != signature:
    try:
        with st.spinner("Reading the persona and preparing the chat…"):
            persona_text = read_upload(persona_file)
            if knowledge_file:
                source_text = read_upload(knowledge_file)
                source_name = knowledge_file.name
            else:
                source_text = persona_text
                source_name = persona_file.name

            # Filename is a useful default, while the full PDF text is passed to the
            # system prompt so the model can follow the persona profile's instructions.
            persona_name = infer_persona_name(persona_file.name)
            base_voice = PERSONAS[DEFAULT].voice
            persona_voice = (
                f"Follow the uploaded persona profile closely. Use its stated identity, "
                f"background, personality, tone, and response rules. If the profile does "
                f"not specify a detail, use a natural, consistent voice. {base_voice}"
            )
            new_chat = BookChat(
                persona_key=DEFAULT,
                source_text=source_text,
                thread_id=str(uuid.uuid4()),
                persona_name=persona_name,
                persona_voice=persona_voice,
                persona_context=persona_text[:18000],
            )
            st.session_state.chat = new_chat
            st.session_state.history = []
            st.session_state.source_name = source_name
            st.session_state.persona_filename = persona_file.name
            st.session_state.chat_signature = signature
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Could not prepare the persona chat: {exc}")
        st.caption("Check your dependencies and GROQ_API_KEY in the .env file, then try uploading the file again.")
        st.stop()

chat = st.session_state.chat
st.success(f"Persona ready: {chat.persona.name}")
st.caption(f"Persona profile: **{st.session_state.persona_filename}** · Knowledge source: **{st.session_state.source_name}**")

with st.expander("Persona profile loaded by the app", expanded=False):
    st.write("The following text was extracted from your persona PDF and provided to the model as character guidance.")
    st.text((persona_text if 'persona_text' in locals() else read_upload(persona_file))[:5000])

st.subheader(f"Chat with {chat.persona.name}")
for role, message in st.session_state.history:
    with st.chat_message(role):
        st.markdown(message)

prompt = st.chat_input(f"Message {chat.persona.name}…")
if prompt:
    st.session_state.history.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(f"{chat.persona.name} is thinking…"):
            try:
                reply = chat.say(prompt)
            except Exception as exc:
                reply = (
                    "I couldn't complete that response just now. Please try again. "
                    f"(Technical detail: {exc})"
                )
        st.markdown(reply)
    st.session_state.history.append(("assistant", reply))
