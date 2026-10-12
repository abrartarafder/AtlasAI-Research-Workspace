"""Atlas — a Streamlit research workspace."""

import html
import os
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv

from research import ResearchSettings, export_pdf, friendly_error, run_research

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Atlas · Research workspace", page_icon="✳", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(f"<style>{(ROOT / 'assets/style.css').read_text()}</style>", unsafe_allow_html=True)


def markup(content: str):
    st.markdown(content, unsafe_allow_html=True)


def initialize():
    defaults = {"messages": [], "composer": "", "pending_prompt": None,
                "failed_prompt": None, "failure": None, "api_key_input": "",
                "model": os.getenv("OPENAI_MODEL", "gpt-4o"), "depth": "Quick brief",
                "web_search": True, "calculator": True}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def new_research():
    st.session_state.update(messages=[], composer="", pending_prompt=None,
                            failure=None, failed_prompt=None)


def set_example(question: str):
    st.session_state.composer = question


def queue_question(question: str):
    st.session_state.pending_prompt = question


def activity_label(event: dict) -> str:
    data = event["output"]
    if event["status"] == "error":
        return data.get("error", "Tool could not finish.")
    if event["tool"] == "search_tool":
        return f"Searched: {data.get('query', '')} · {len(data.get('results', []))} sources found"
    return f"Calculated: {data.get('expression', '')} = {data.get('result', '')}"


def show_activity(events: list[dict]):
    for event in events:
        st.markdown(f"{'✓' if event['status'] == 'complete' else '⚠'} {activity_label(event)}")


def source_cards(sources: list[dict]):
    if not sources:
        st.caption("No web sources were cited in this answer.")
        return
    columns = st.columns(2, gap="small")
    for index, source in enumerate(sources):
        with columns[index % 2]:
            url = source["url"]
            title = html.escape(" ".join(source.get("title", url).split()))
            domain = html.escape(urlparse(url).hostname or url)
            preview = " ".join(source.get("snippet", "").split())
            snippet = html.escape(preview[:180].rstrip() + ("…" if len(preview) > 180 else ""))
            # HTML avoids Markdown splitting a card when source text contains blank lines.
            st.html(f'<a class="source-card" href="{html.escape(url, quote=True)}" target="_blank" '
                    f'rel="noopener noreferrer"><span class="source-domain">{domain} <span>↗</span></span>'
                    f'<strong>{title}</strong><span class="source-snippet">{snippet}</span></a>')


def show_assistant(message: dict, index: int, is_latest: bool):
    payload = message["payload"]
    result = payload.get("result", {})
    with st.chat_message("assistant", avatar="✳"):
        markup('<div class="answer-label">ATLAS RESEARCH BRIEF</div>')
        st.markdown(f"### {result.get('topic', 'Research brief')}")
        st.markdown(message["content"])
        findings = result.get("key_findings", [])
        if findings:
            with st.container(border=True):
                markup('<div class="eyebrow">KEY TAKEAWAYS</div>')
                for finding in findings:
                    st.markdown(f"- {finding}")
        tabs = st.tabs([f"Sources · {len(payload.get('source_details', []))}", "Research activity"])
        with tabs[0]:
            source_cards(payload.get("source_details", []))
        with tabs[1]:
            show_activity(payload.get("activity", []))
            st.caption(f"Completed in {payload.get('elapsed', 0):.1f}s")
        st.caption("Search previews may be incomplete. Open the sources to check the evidence.")
        if is_latest:
            questions = result.get("follow_up_questions", [])
            if questions:
                markup('<div class="eyebrow followup-label">KEEP EXPLORING</div>')
                for number, question in enumerate(questions[:3]):
                    st.button(question, key=f"followup_{index}_{number}",
                              on_click=queue_question, args=(question,), use_container_width=True)


def show_landing():
    markup('''<section class="welcome">
        <div class="welcome-kicker"><span class="tiny-star">✳</span> A LITTLE CURIOSITY GOES A LONG WAY</div>
        <h1>Good questions.<br><span>Clearer answers.</span></h1>
        <p>Your research partner for the rabbit holes worth exploring.<br>
        Search the web, connect the dots, and turn curiosity into clarity.</p>
    </section>''')
    with st.container(border=True, key="question_box"):
        st.text_area("What are you curious about?", key="composer", height=115,
                     placeholder="Ask a question, explore a topic, or compare a few ideas…",
                     label_visibility="collapsed", max_chars=6000)
        controls, action = st.columns([3, 1.35], vertical_alignment="center")
        with controls:
            st.segmented_control("Research depth", ["Quick brief", "Deep research"],
                                 key="depth", label_visibility="collapsed")
        with action:
            if st.button("Begin research  →", type="primary", use_container_width=True,
                         disabled=not st.session_state.composer.strip()):
                st.session_state.pending_prompt = st.session_state.composer
    markup('<div class="composer-hint">A focused brief or a deeper dive. You choose the pace.</div>')
    markup('<div class="eyebrow inspiration-label">NEED A STARTING POINT?</div>')
    examples = [
        ("⌘", "Technology", "What's next for AI agents?", "Research current trends in AI agents, their practical uses, and their limitations."),
        ("↗", "Business", "Find the signal in the market", "Compare the business models of subscription software and usage-based software, including their trade-offs."),
        ("◎", "Science", "Follow the energy transition", "Compare solar and wind energy: costs, reliability, and recent technological progress."),
    ]
    for column, (icon, category, title, question) in zip(st.columns(3, gap="medium"), examples):
        with column:
            with st.container(border=True):
                markup(f'<div class="example-icon">{icon}</div><div class="example-category">{category}</div>')
                st.button(f"{title}  ↗", key=f"example_{category}", use_container_width=True,
                          on_click=set_example, args=(question,))
    markup('''<div class="workflow-strip">
        <div><span>01</span><strong>Ask a question</strong><small>Give your curiosity a direction</small></div>
        <div><span>02</span><strong>Explore the evidence</strong><small>Web sources and accurate calculations</small></div>
        <div><span>03</span><strong>Bring it together</strong><small>Useful findings, with context</small></div>
    </div>''')


initialize()
messages = st.session_state.messages

with st.sidebar:
    markup('<div class="brand"><span class="brand-symbol">✳</span> atlas<span class="brand-dot">.</span></div>'
           '<div class="brand-caption">A workspace for curious minds</div>')
    st.button("＋  New research", key="new_research", type="primary", use_container_width=True, on_click=new_research)
    st.divider()
    markup('<div class="eyebrow recent-label">THIS CONVERSATION</div>')
    if messages:
        st.caption(f"{len(messages) // 2} questions explored")
    else:
        markup('<div class="empty-history">A fresh page.<br>Your next discovery starts here.</div>')
    st.caption("Ask follow-ups to keep exploring the same topic.")
    with st.expander("Settings", icon=":material/tune:"):
        st.text_input("OpenAI API key", type="password", key="api_key_input",
                      placeholder="Use your key from .env, or enter one", help="Kept only in this browser session; never saved with conversations.")
        st.text_input("Model", key="model")
        st.toggle("Web search", key="web_search")
        st.toggle("Calculator", key="calculator")
        st.caption("Memory lasts for this browser session. Refreshing the page or starting new research clears it.")
    markup('<div class="sidebar-note"><span>✳</span><strong>Stay curious.</strong>'
           '<p>From the first question<br>to your next perspective.</p></div>')
    st.caption("ATLAS / YOUR RESEARCH COMPANION")

api_key = st.session_state.api_key_input.strip() or os.getenv("OPENAI_API_KEY", "")
top_left, top_right = st.columns([3, 2], vertical_alignment="center")
with top_left:
    markup('<div class="workspace-title">Workspace <span>/</span> <strong>Research</strong></div>')
with top_right:
    markup('<div class="workspace-status"><span class="status-dot"></span>'
           f'{"Ready to explore" if api_key else "Add an API key in Settings"}</div>')
st.divider()

if not api_key:
    st.info("Add your OpenAI API key in Settings to start research. You can explore the workspace first.")
if not messages:
    show_landing()
else:
    heading, download = st.columns([3, 1], vertical_alignment="center")
    with heading:
        markup('<div class="eyebrow">THE EXPLORATION CONTINUES</div>')
        st.markdown("## Your research")
    with download:
        title = messages[0]["content"][:80]
        st.download_button("Download PDF", export_pdf(messages, title),
                           file_name="atlas-research.pdf", mime="application/pdf", use_container_width=True)
    for index, message in enumerate(messages):
        if message["role"] == "user":
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(message["content"])
        else:
            show_assistant(message, index, is_latest=index == len(messages) - 1)
    st.segmented_control("Research depth", ["Quick brief", "Deep research"], key="depth")
    prompt = st.chat_input("Ask a follow-up. Atlas remembers the conversation.", max_chars=6000)
    if prompt:
        st.session_state.pending_prompt = prompt

if st.session_state.failure:
    st.error(st.session_state.failure)
    if st.button("Retry research", key="retry"):
        st.session_state.pending_prompt = st.session_state.failed_prompt

question = st.session_state.pending_prompt
if question:
    st.session_state.pending_prompt = None
    settings = ResearchSettings(model=st.session_state.model,
                                depth=st.session_state.depth or "Quick brief",
                                web_search=st.session_state.web_search,
                                calculator=st.session_state.calculator)
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(question)
    with st.status("Exploring your question…", expanded=True) as status:
        try:
            run = run_research(question, messages, settings, api_key,
                               on_activity=lambda event: show_activity([event]))
            messages.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": run["result"]["summary"], "payload": run},
            ])
            st.session_state.failure = None
            st.session_state.failed_prompt = None
            status.update(label="Research complete", state="complete", expanded=False)
        except Exception as exc:
            st.session_state.failure = friendly_error(exc)
            st.session_state.failed_prompt = question
            status.update(label="Research needs another try", state="error", expanded=False)
    st.rerun()
