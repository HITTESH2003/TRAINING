"""
Module 6: Summarization — Streamlit frontend.

Ask a question, retrieve chunks from Module 4's Postgres database, and
summarize them with Qwen3-0.6B. Every retrieval and generation parameter
this module is built to teach about is a control here, not a hidden
constant -- top_k, embedding dimension, thinking mode, sampling
parameters, max_new_tokens -- and the actual assembled prompt is always
shown, not hidden behind the summary.

Run:
  "../1. OCR/.venv/bin/python" -m streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from rag import config, llm, prompting, retrieval

st.set_page_config(page_title="Module 6: Retrieval + Summarization", page_icon="📚", layout="wide")


@st.cache_resource
def get_connection():
    conn = retrieval.connect()
    retrieval.require_chunks_table(conn)
    return conn


st.title("📚 Retrieval + Summarization")
st.caption(
    "Module 6 — retrieves real chunks from Module 4's Postgres/pgvector database, "
    "then summarizes them with Qwen3-0.6B. Every parameter below is a real control, not a fixed default."
)

with st.sidebar:
    st.header("Retrieval parameters")
    top_k = st.slider("top_k -- how many chunks to retrieve", min_value=1, max_value=18, value=config.DEFAULT_TOP_K)
    dim = st.select_slider("Embedding dimension", options=[768, 512, 256, 128, 64], value=config.DEFAULT_DIM)
    doc_filter = st.selectbox("Restrict to one document", options=["(all documents)", "federal_register_proclamation", "nasa_iss_factsheet", "synthetic_sample"])

    st.header("Model config")
    enable_thinking = st.toggle("enable_thinking", value=False, help="Qwen3 can emit a <think>...</think> reasoning block before answering. Sampling parameters differ by design between the two modes (see README).")
    max_new_tokens = st.slider("max_new_tokens -- answer length cap", min_value=64, max_value=1024, value=config.DEFAULT_MAX_NEW_TOKENS, step=64)

    preset = config.GENERATION_PRESETS[enable_thinking]
    st.caption(f"Qwen3's own recommended sampling for this mode: temperature={preset['temperature']}, top_p={preset['top_p']}, top_k={preset['top_k']}")
    temperature = st.slider("temperature", min_value=0.0, max_value=1.5, value=preset["temperature"], step=0.05)

question = st.text_input("Question", value="What does this collection of documents cover?")
run = st.button("Retrieve + Summarize", type="primary")

if run and question.strip():
    conn = get_connection()
    doc_name = None if doc_filter == "(all documents)" else doc_filter

    with st.spinner("Embedding query + searching Postgres..."):
        chunks = retrieval.retrieve(conn, question, top_k=top_k, dim=dim, doc_name=doc_name)

    docs_represented = sorted({c["doc_name"] for c in chunks})
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"Retrieved {len(chunks)} chunk(s)")
        st.caption(f"Documents represented: {', '.join(docs_represented) if docs_represented else '(none)'}")
        for i, c in enumerate(chunks, start=1):
            with st.expander(f"[{i}] {c['doc_name']} -- distance {c['distance']:.3f}"):
                if c.get("section_path"):
                    st.caption(c["section_path"])
                st.text(c["chunk_text"])

    messages = prompting.build_messages(question, chunks)
    prompt_tokens = llm.count_prompt_tokens(messages, enable_thinking=enable_thinking)

    with col2:
        st.subheader("Prompt sent to the model")
        st.caption(f"{prompt_tokens} tokens  ·  {round(100 * prompt_tokens / config.MAX_CONTEXT_TOKENS, 2)}% of the {config.MAX_CONTEXT_TOKENS}-token context window")
        with st.expander("Show the exact assembled prompt", expanded=False):
            st.code(messages[1]["content"], language="text")

    with st.spinner(f"Generating (enable_thinking={enable_thinking})..."):
        result = llm.generate(
            messages,
            enable_thinking=enable_thinking,
            max_new_tokens=max_new_tokens,
            generation_overrides={"temperature": temperature},
        )

    st.subheader("Summary")
    st.write(result["answer"])
    if result["thinking"]:
        with st.expander("Model's thinking trace"):
            st.text(result["thinking"])

    st.caption(
        f"generation_time_s={result['generation_time_s']}  ·  "
        f"output_tokens={result['output_token_count']}  ·  "
        f"params={result['generation_params']}"
    )
elif run:
    st.warning("Enter a question first.")
