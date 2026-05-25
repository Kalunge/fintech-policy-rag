"""Agentic pipeline: a LangChain tool-calling agent that combines RAG over the
policy corpus with calls to the banking tools.

The agent decides at each step whether to:
- search the policies (acts like RAG)
- call a banking tool (operational data)
- combine results and answer
- give up if it can't make progress

Returns the same outer shape as RAGPipeline.answer() so the FastAPI layer
treats both pipelines uniformly. Adds a tool_calls list so the UI can
render what the agent did.
"""
from __future__ import annotations

import json
import time
from typing import Any

# LangChain 1.x reorganised: the classic AgentExecutor + create_tool_calling_agent
# moved into langchain_classic. We use the classic API for stability; migrating
# to the new langchain.agents.create_agent API is a separate task.
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool

from rag.generation import get_llm
from rag.guardrails import enforce_length, extract_citation_indices
from rag.retrieval import Retriever
from tools import banking
from tools.errors import ToolError


MAX_ITERATIONS = 4

AGENT_SYSTEM_PROMPT = """You are the ThaBytePay Policy and Operations Assistant.

You answer employee questions about company policies and (when needed) about
specific agents, terminals, and transactions. You have access to two kinds of
tools:

1. search_policies(query): retrieves relevant excerpts from the twelve
   internal policy documents. Use this for any question about rules,
   procedures, limits, definitions, or anything that isn't a specific
   live data lookup. The results come back as numbered [Source N] blocks
   that you MUST cite in your answer.

2. Banking tools: check_agent_balance, lookup_transaction, terminal_status,
   agent_compliance_scorecard, initiate_mock_deposit. Use these only when
   the user asks about a SPECIFIC agent, terminal, or transaction by ID.
   Do not invent IDs. If the user hasn't given one, either ask them to
   provide it or answer the general policy question without a tool call.

Rules you MUST follow:

- If the question can be answered from policies alone, use search_policies
  and cite the sources you used.
- If the question is about a specific agent / terminal / transaction with an
  ID, call the relevant banking tool.
- If the question combines both (e.g., "can agent AG-001 process a 200,000
  KES transaction per policy?"), use BOTH a banking tool and search_policies.
- Quote specific numbers, timeframes, and IDs exactly.
- If neither the policy search nor the tool can answer the question, say
  exactly: "I can only answer questions about ThaBytePay policies and
  operational data. The provided context does not cover this topic."
- Keep your answer concise — under 220 words.
- Cite every claim that came from a policy chunk using the [Source N]
  format. Tool results don't need bracket citations; just summarise them
  clearly and accurately.
"""


REFUSAL_TEMPLATE = (
    "I can only answer questions about ThaBytePay policies and operational data. "
    "The provided context does not cover this topic."
)


def _ms_since(t0: float) -> float:
    return round((time.time() - t0) * 1000, 1)


class AgenticPipeline:
    """Single-call agent that may search policies and call banking tools."""

    def __init__(self) -> None:
        self.retriever = Retriever()
        # disable_streaming=True is required for Groq + tool-calling.
        self.llm = get_llm(temperature=0.1, max_tokens=800, disable_streaming=True)

    def _build_tools(
        self,
        sources: list[dict[str, Any]],
        full_chunks: list[dict[str, Any]],
        retrieve_ms_accum: list[float],
        tool_calls: list[dict[str, Any]],
    ) -> list[StructuredTool]:
        """Build the tool list with closures over per-request state.

        Each call to search_policies appends to sources, snippets, and the
        retrieve_ms accumulator. Each banking tool call appends to tool_calls.
        Everything lives on the closure so we don't need a global state.
        """
        retriever = self.retriever

        def search_policies(query: str) -> str:
            """Search ThaBytePay's twelve company policy documents and return the
            most relevant excerpts. Use this for any policy, rules, procedure,
            limit, definition, or anything that isn't a specific operational
            lookup. The results come back as numbered [Source N] blocks that
            you must cite in your final answer.

            Args:
                query: a natural-language description of what you're looking for.
                       Be specific — 'agent tier limits' is better than 'agents'.
            """
            t_start = time.time()
            results = retriever.retrieve(query, k=5)
            retrieve_ms_accum.append((time.time() - t_start) * 1000)

            formatted: list[str] = []
            for doc, _score in results:
                idx = len(sources) + 1
                meta = doc.metadata or {}
                sources.append(
                    {
                        "source_idx": idx,
                        "doc_id": meta.get("doc_id", ""),
                        "doc_title": meta.get("doc_title", ""),
                        "section": meta.get("section", ""),
                        "chunk_id": meta.get("chunk_id", ""),
                    }
                )
                full_chunks.append(
                    {"source_idx": idx, "text": (doc.page_content or "").strip()}
                )
                header = f"[Source {idx}] {meta.get('doc_title', '?')}"
                if meta.get("doc_id"):
                    header += f" ({meta['doc_id']})"
                if meta.get("section"):
                    header += f" — {meta['section']}"
                formatted.append(f"{header}\n{(doc.page_content or '').strip()}\n")

            tool_calls.append(
                {
                    "tool": "search_policies",
                    "args": {"query": query},
                    "summary": f"Returned {len(results)} chunks (now {len(sources)} total).",
                }
            )
            return "\n".join(formatted)

        # Per-tool wrappers with explicit signatures so LangChain can introspect
        # arguments correctly. Each wrapper closes over tool_calls to record
        # what the agent did, and converts ToolError into a JSON string the LLM
        # can read and react to.

        def _record(name: str, args: dict, summary: str, result: Any) -> None:
            tool_calls.append({"tool": name, "args": args, "summary": summary, "result": result})

        def check_agent_balance_tool(agent_id: str) -> str:
            try:
                result = banking.check_agent_balance(agent_id)
                _record("check_agent_balance", {"agent_id": agent_id}, "ok", result)
                return json.dumps(result)
            except ToolError as exc:
                err = exc.as_dict()
                _record("check_agent_balance", {"agent_id": agent_id}, f"error: {exc.code}", err)
                return json.dumps(err)

        def lookup_transaction_tool(reference: str) -> str:
            try:
                result = banking.lookup_transaction(reference)
                _record("lookup_transaction", {"reference": reference}, "ok", result)
                return json.dumps(result)
            except ToolError as exc:
                err = exc.as_dict()
                _record("lookup_transaction", {"reference": reference}, f"error: {exc.code}", err)
                return json.dumps(err)

        def terminal_status_tool(terminal_id: str) -> str:
            try:
                result = banking.terminal_status(terminal_id)
                _record("terminal_status", {"terminal_id": terminal_id}, "ok", result)
                return json.dumps(result)
            except ToolError as exc:
                err = exc.as_dict()
                _record("terminal_status", {"terminal_id": terminal_id}, f"error: {exc.code}", err)
                return json.dumps(err)

        def agent_compliance_scorecard_tool(agent_id: str) -> str:
            try:
                result = banking.agent_compliance_scorecard(agent_id)
                _record("agent_compliance_scorecard", {"agent_id": agent_id}, "ok", result)
                return json.dumps(result)
            except ToolError as exc:
                err = exc.as_dict()
                _record("agent_compliance_scorecard", {"agent_id": agent_id}, f"error: {exc.code}", err)
                return json.dumps(err)

        def initiate_mock_deposit_tool(
            agent_id: str, customer_msisdn: str, amount_kes: int
        ) -> str:
            args = {"agent_id": agent_id, "customer_msisdn": customer_msisdn, "amount_kes": amount_kes}
            try:
                result = banking.initiate_mock_deposit(agent_id, customer_msisdn, amount_kes)
                _record("initiate_mock_deposit", args, "ok", result)
                return json.dumps(result)
            except ToolError as exc:
                err = exc.as_dict()
                _record("initiate_mock_deposit", args, f"error: {exc.code}", err)
                return json.dumps(err)

        return [
            StructuredTool.from_function(
                name="search_policies",
                description=search_policies.__doc__,
                func=search_policies,
            ),
            StructuredTool.from_function(
                name="check_agent_balance",
                description=banking.check_agent_balance.__doc__,
                func=check_agent_balance_tool,
            ),
            StructuredTool.from_function(
                name="lookup_transaction",
                description=banking.lookup_transaction.__doc__,
                func=lookup_transaction_tool,
            ),
            StructuredTool.from_function(
                name="terminal_status",
                description=banking.terminal_status.__doc__,
                func=terminal_status_tool,
            ),
            StructuredTool.from_function(
                name="agent_compliance_scorecard",
                description=banking.agent_compliance_scorecard.__doc__,
                func=agent_compliance_scorecard_tool,
            ),
            StructuredTool.from_function(
                name="initiate_mock_deposit",
                description=banking.initiate_mock_deposit.__doc__,
                func=initiate_mock_deposit_tool,
            ),
        ]

    def answer(self, question: str) -> dict[str, Any]:
        t_start = time.time()

        sources: list[dict[str, Any]] = []
        full_chunks: list[dict[str, Any]] = []
        tool_calls: list[dict[str, Any]] = []
        retrieve_ms_accum: list[float] = []

        tools = self._build_tools(sources, full_chunks, retrieve_ms_accum, tool_calls)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", AGENT_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=MAX_ITERATIONS,
            return_intermediate_steps=False,
            handle_parsing_errors=True,
            verbose=False,
        )

        t_generate = time.time()
        try:
            result = executor.invoke({"input": question})
            answer_text = enforce_length(result.get("output", "").strip())
        except Exception as exc:
            # Known Groq + Llama 3.3 quirk: the model sometimes emits tool calls
            # in Llama's native <function=name{args}</function> syntax instead of
            # the OpenAI-style JSON Groq expects, and Groq rejects the request
            # as 'tool_use_failed'. Fall back to the regular RAG pipeline so the
            # user still gets an answer.
            if "tool_use_failed" in str(exc) or "Failed to call a function" in str(exc):
                tool_calls.append(
                    {
                        "tool": "_fallback",
                        "args": {"question": question},
                        "summary": "tool-call format error from Groq; using RAG-only fallback.",
                    }
                )
                from rag.pipeline import RAGPipeline

                fallback = RAGPipeline()
                fb_result = fallback.answer(question)
                # Adopt the fallback's answer + sources directly
                answer_text = fb_result["answer"]
                # Reset and copy the RAG citations into our sources list
                sources.clear()
                full_chunks.clear()
                for c, sn in zip(fb_result.get("citations", []), fb_result.get("snippets", [])):
                    sources.append(c)
                    full_chunks.append({"source_idx": c["source_idx"], "text": sn["snippet"]})
            else:
                answer_text = (
                    "I ran into a problem processing that question. "
                    f"Please try rephrasing it. (Internal: {type(exc).__name__})"
                )

        generate_ms = (time.time() - t_generate) * 1000

        # Build citations + snippets from the sources the agent actually retrieved
        cited_indices = set(extract_citation_indices(answer_text))
        citations: list[dict[str, Any]] = []
        snippets: list[dict[str, Any]] = []
        chunks_by_idx = {fc["source_idx"]: fc["text"] for fc in full_chunks}

        for source in sources:
            idx = source["source_idx"]
            if idx in cited_indices:
                citations.append(source)
                text = chunks_by_idx.get(idx, "")
                snippet = text[:320]
                if len(text) > 320:
                    snippet = snippet.rstrip() + "..."
                snippets.append({"source_idx": idx, "snippet": snippet})

        out_of_corpus = REFUSAL_TEMPLATE.lower() in answer_text.lower()

        return {
            "answer": answer_text,
            "citations": citations,
            "snippets": snippets,
            "tool_calls": tool_calls,
            "out_of_corpus": out_of_corpus,
            "retrieve_ms": round(sum(retrieve_ms_accum), 1),
            "generate_ms": round(generate_ms, 1),
            "total_ms": _ms_since(t_start),
            "iterations": len(tool_calls),
        }
