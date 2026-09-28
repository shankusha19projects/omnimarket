"""AI Financial Research Advisor and Research Command Center orchestration."""
from __future__ import annotations

import json
import time
from typing import Any

from backend import db
from backend.agents.registry import research_agent
from backend.ai.providers import active_provider
from backend.research import context as cx
from backend.services import universe
from backend.utils.http import ProviderError
from backend.utils.logging_setup import get_logger

log = get_logger("research")

SYSTEM_PROMPT = """You are the research analyst inside OmniMarket Intelligence Terminal — an interdisciplinary financial research analyst
(equities, macro, accounting, corporate finance, valuation, fixed income, commodities, FX, crypto, real estate, monetary policy,
banking, derivatives concepts, portfolio analytics, financial history, market structure).

Grounding rules (non-negotiable):
- The ONLY market data you may state as fact is what appears in the CONTEXT JSON supplied with the question. Quote its numbers exactly
  and attribute them (e.g. "per SEC XBRL, FY2025 revenue was …", "quote via yahoo, delayed ~15 min, retrieved 14:32 UTC").
- If a figure is not in the context, say it is unavailable. Never invent prices, earnings, estimates, analyst targets, dates or citations.
- Flag stale data (cache_status "stale" or old retrieval times) and data gaps listed in `data_gaps`.
- Clearly separate FACTS (from context) from INTERPRETATION (your analysis). Use hedged language for interpretation.
- Never express certainty about future prices. No buy/sell/hold calls; present evidence, competing explanations and scenarios.
- Where evidence is mixed, say so explicitly (e.g. "three drivers coincide with the move, but the data do not establish a single cause").
- Analyze relationships (revenue ↔ margins ↔ operating leverage ↔ cash conversion ↔ capex ↔ FCF ↔ dilution ↔ debt ↔ valuation ↔ rates/cycle),
  not shallow statements.
- Cite sources using the URLs / provider names in the context. End with a "Data Sources" section listing them with retrieval times.
Format: GitHub-flavored markdown with the section headings requested below. Be dense and specific; tables are welcome."""

ASSET_FORMAT = """Structure the answer with these numbered sections:
1. Executive Summary 2. Current Market Situation 3. Business Fundamentals 4. Earnings and Cash Flow 5. Valuation 6. Technical Context
7. Macro Context 8. Recent Developments 9. Catalysts 10. Risks 11. Bull Scenario 12. Base Scenario 13. Bear Scenario
14. Metrics to Watch 15. Data Sources
For each scenario state assumptions explicitly and do not assign certainty."""

MOVE_FORMAT = """Structure the answer with these numbered sections:
1. What happened 2. Most relevant observable drivers 3. Dollar impact 4. Rates impact 5. Inflation expectations
6. Geopolitical developments 7. Technical context 8. Alternative explanations 9. Sources"""

GENERAL_FORMAT = """Answer directly and analytically. Use headings where helpful and finish with a 'Data Sources' section."""

DISCLAIMER = ("Research and analytical information only. Market data may be delayed or incomplete. This application does not execute trades "
              "and is not a substitute for personalized professional financial, tax, or legal advice.")


def _intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("why did", "why is", "why are", "what moved", "what's moving", "move today", "rally", "sell-off", "selloff", "drop", "surge", "plunge", "happening in")):
        return "move"
    if any(w in t for w in ("analyze", "analyse", "analysis", "deep dive", "research", "valuation of", "outlook for", "thesis")):
        return "asset"
    return "general"


async def build_context(message: str, use_web: bool) -> dict[str, Any]:
    ent = await cx.detect_entities(message)
    intent = _intent(message)
    ctx: dict[str, Any] = {"question": message, "intent": intent, "generated_at": cx._ts(time.time()), "entities": ent["symbols"]}
    if ent["symbols"]:
        primary = ent["symbols"][0]
        ctx["primary_asset"] = cx.compact_for_llm(await cx.asset_context(primary, deep=intent != "move"))
        for other in ent["symbols"][1:3]:
            try:
                o = await cx.asset_context(other, deep=False)
                ctx.setdefault("related_assets", []).append(cx.compact_for_llm(o))
            except ProviderError:
                pass
    else:
        ctx["market"] = await cx.market_context()
    if ent["themes"]:
        ctx["themes"] = [{"name": t["name"], "constituents": t["symbols"]} for t in ent["themes"]]
    agent = research_agent(prefer_web=use_web)
    if use_web or intent == "move":
        topic = message if not ent["symbols"] else f"{universe.resolve(ent['symbols'][0]).name} {ent['symbols'][0]}"
        try:
            res = await (agent.investigate_market_move(topic) if intent == "move" else agent.collect_recent_news(topic, days=10))
            ctx["web_research"] = {"agent": res.agent, "evidence": [e.to_dict() for e in res.evidence[:12]], "errors": res.errors, "notes": res.notes}
        except Exception as exc:  # agents are optional; never break the advisor
            ctx["web_research"] = {"agent": agent.name, "errors": [str(exc)]}
    return ctx


def offline_answer(ctx: dict[str, Any]) -> str:
    """Deterministic, data-only brief used when no AI provider is configured."""
    lines = ["> **Offline analyst mode** — no AI provider is configured, so this is a structured data brief assembled directly from sources "
             "(no language-model interpretation). Configure Anthropic, OpenAI or Ollama under **Settings → AI** for full analysis.", ""]
    p = ctx.get("primary_asset")
    if p:
        a, q = p["asset"], p["quote"]
        lines += [f"## {a.get('name')} ({a.get('symbol')})", ""]
        if q.get("price") is not None:
            lines.append(f"- **Last:** {q['price']:,.4g} {q.get('currency') or ''} ({(q.get('change_pct') or 0):+.2f}%) — {q.get('source')}")
        perf = p.get("performance") or {}
        if perf:
            lines.append("- **Performance:** " + ", ".join(f"{k.replace('perf_', '').upper()} {v:+.1f}%" for k, v in perf.items() if v is not None))
        t = p.get("technicals") or {}
        if t:
            lines.append(f"- **Technicals:** RSI(14) {t.get('rsi14') or 0:.1f}; 20d realized vol {t.get('realized_vol_20d') or 0:.1f}%; drawdown from 1Y high {t.get('current_drawdown') or 0:.1f}%")
        f = p.get("fundamentals") or {}
        if f:
            pick = [("pe", "P/E", "x"), ("forward_pe", "Fwd P/E", "x"), ("ev_ebitda", "EV/EBITDA", "x"), ("gross_margin", "Gross margin", "%"),
                    ("operating_margin", "Op. margin", "%"), ("revenue_growth", "Revenue growth", "%"), ("roic", "ROIC", "%"), ("net_debt", "Net debt", "$")]
            parts = []
            for k, lbl, kind in pick:
                v = (f.get(k) or {}).get("value")
                if v is None:
                    continue
                parts.append(f"{lbl} {v * 100:.1f}%" if kind == "%" else f"{lbl} {v:.1f}×" if kind == "x" else f"{lbl} ${v / 1e9:,.1f}B")
            lines.append("- **Fundamentals (SEC-computed where available):** " + "; ".join(parts))
        if p.get("annual_statements"):
            lines += ["", "| FY end | Revenue | Op. income | Net income | FCF |", "|---|---|---|---|---|"]
            for r in p["annual_statements"][:4]:
                fmt = lambda v: f"${v / 1e9:,.2f}B" if isinstance(v, (int, float)) else "n/a"  # noqa: E731
                lines.append(f"| {r.get('period_end')} | {fmt(r.get('revenue'))} | {fmt(r.get('operating_income'))} | {fmt(r.get('net_income'))} | {fmt(r.get('free_cash_flow'))} |")
        if p.get("news"):
            lines += ["", "### Recent headlines"] + [f"- [{n['title']}]({n['url']}) — {n['publisher']}, {n.get('published')}" for n in p["news"][:6]]
        if p.get("recent_filings"):
            lines += ["", "### Recent SEC filings"] + [f"- [{x['form']} · {x['filed']}]({x['url']})" + (f" — {x['description']}" if x.get("description") else "") for x in p["recent_filings"][:5]]
        if p.get("data_gaps"):
            lines += ["", "**Data gaps:** " + "; ".join(p["data_gaps"])]
    elif ctx.get("market"):
        m = ctx["market"]
        lines += ["## Market snapshot", "", "| Instrument | Last | Change |", "|---|---|---|"]
        for s, q in m["snapshot"].items():
            if q.get("price") is not None:
                lines.append(f"| {q.get('name') or s} | {q['price']:,.4g} | {(q.get('change_pct') or 0):+.2f}% |")
        if m.get("top_developments"):
            lines += ["", "### Potential market-moving developments"] + [f"- {d['headline']} ({', '.join(d['publishers'][:3])})" for d in m["top_developments"]]
    wr = ctx.get("web_research")
    if wr and wr.get("evidence"):
        lines += ["", f"### Web research ({wr['agent']})"] + [f"- [{e['title']}]({e['url']})" + (f" — {e['publisher']}" if e.get("publisher") else "") for e in wr["evidence"][:8]]
    return "\n".join(lines)


async def chat(message: str, history: list[dict[str, str]], conversation: str | None, use_web: bool) -> dict[str, Any]:
    started = time.time()
    ctx = await build_context(message, use_web)
    fmt = {"asset": ASSET_FORMAT, "move": MOVE_FORMAT}.get(ctx["intent"], GENERAL_FORMAT)
    provider = active_provider()
    sources = _sources(ctx)
    if provider is None:
        answer, meta = offline_answer(ctx), {"provider": "offline", "model": "rule-based"}
    else:
        user = f"QUESTION:\n{message}\n\nRESPONSE FORMAT:\n{fmt}\n\nCONTEXT JSON (authoritative; retrieved {ctx['generated_at']}):\n{cx.to_prompt_json(ctx)}"
        msgs = [m for m in history[-8:] if m.get("content")] + [{"role": "user", "content": user}]
        try:
            res = await provider.complete(SYSTEM_PROMPT, msgs)
            answer, meta = res.text, {"provider": res.provider, "model": res.model, "usage": res.usage, "note": res.note}
        except ProviderError as exc:
            log.warning(f"advisor provider error: {exc.message}")
            answer = f"> ⚠ AI provider error: {exc.message}. Showing the offline data brief instead.\n\n" + offline_answer(ctx)
            meta = {"provider": "offline", "model": "rule-based", "error": exc.message}
    conv = conversation or f"c{int(started)}"
    db.execute("INSERT INTO advisor_messages (conversation, role, content, meta, created_at) VALUES (?,?,?,?,?)", (conv, "user", message, "{}", started))
    db.execute("INSERT INTO advisor_messages (conversation, role, content, meta, created_at) VALUES (?,?,?,?,?)",
               (conv, "assistant", answer, json.dumps({**meta, "sources": sources}), time.time()))
    log.info(f"advisor intent={ctx['intent']} entities={ctx.get('entities')} provider={meta.get('provider')} {time.time() - started:.1f}s")
    return {"answer": answer, "conversation": conv, "intent": ctx["intent"], "entities": ctx.get("entities"), "sources": sources,
            "meta": meta, "elapsed": round(time.time() - started, 1), "disclaimer": DISCLAIMER}


def _sources(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    p = ctx.get("primary_asset") or {}
    if p.get("quote", {}).get("source"):
        out.append({"label": f"Quote — {p['quote']['source']}", "url": None})
    if p.get("statements_source"):
        out.append({"label": p["statements_source"], "url": None})
    for f in (p.get("recent_filings") or [])[:5]:
        out.append({"label": f"SEC {f['form']} filed {f['filed']}", "url": f["url"]})
    for n in (p.get("news") or [])[:6]:
        out.append({"label": f"{n['publisher']}: {n['title']}", "url": n["url"]})
    for e in ((ctx.get("web_research") or {}).get("evidence") or [])[:8]:
        out.append({"label": f"{e.get('publisher') or 'web'}: {e['title']}", "url": e["url"]})
    if ctx.get("market"):
        out.append({"label": "Market snapshot — Yahoo-compatible quotes; U.S. Treasury yield curve; NY Fed EFFR", "url": None})
    return out


def conversations() -> list[dict[str, Any]]:
    return db.query("""SELECT conversation, MIN(created_at) AS started, MAX(created_at) AS updated,
                       (SELECT content FROM advisor_messages m2 WHERE m2.conversation = m.conversation AND role='user' ORDER BY id LIMIT 1) AS title
                       FROM advisor_messages m GROUP BY conversation ORDER BY updated DESC LIMIT 30""")


def conversation(conv: str) -> list[dict[str, Any]]:
    rows = db.query("SELECT role, content, meta, created_at FROM advisor_messages WHERE conversation = ? ORDER BY id", (conv,))
    for r in rows:
        r["meta"] = json.loads(r["meta"] or "{}")
    return rows


# ---- Research Command Center ------------------------------------------------------------
async def research(query: str, use_web: bool, synthesize: bool) -> dict[str, Any]:
    started = time.time()
    ent = await cx.detect_entities(query)
    workspace: dict[str, Any] = {"query": query, "entities": ent["symbols"], "themes": [t["name"] for t in ent["themes"]],
                                 "sectors": [s[0] for s in ent["sectors"]], "sections": []}
    if ent["symbols"]:
        primary = ent["symbols"][0]
        a = universe.resolve(primary)
        workspace["primary"] = {"symbol": a.yahoo, "name": a.name, "asset_class": a.asset_class}
        if a.asset_class == "equity":
            workspace["report"] = await cx.analysis_report(primary)
        ctx = await cx.asset_context(primary, deep=a.asset_class == "equity")
        workspace["compact"] = cx.compact_for_llm(ctx)
    if ent["themes"]:
        from backend.services import markets
        th = await markets.themes()
        workspace["theme_rows"] = [r for r in th["rows"] if r["id"] in {t["id"] for t in ent["themes"]}]
    if ent["sectors"]:
        from backend.services import markets
        sec = await markets.sectors()
        workspace["sector_rows"] = [r for r in sec["rows"] if r["sector"] in {s[0] for s in ent["sectors"]}]
    from backend.services import macro
    workspace["macro"] = await macro.macro_snapshot()
    agent = research_agent(prefer_web=use_web)
    try:
        res = await agent.search(query, news=True, days=21, limit=10)
        workspace["web"] = res.to_dict()
        if agent.name == "tinyfish" and res.evidence:
            pages = await agent.fetch_pages([e.url for e in res.evidence[:3]], purpose=f"Research: {query}")
            workspace["web_pages"] = pages.to_dict()
    except Exception as exc:
        workspace["web"] = {"agent": agent.name, "errors": [str(exc)], "evidence": []}
    try:
        from backend.providers.registry import sec as sec_provider
        workspace["filings_search"] = await sec_provider.full_text_search(query if len(query) < 80 else " ".join(query.split()[:6]), limit=8)
    except ProviderError as exc:
        workspace["filings_search_error"] = exc.message
    provider = active_provider()
    if synthesize and provider:
        ctx_for_llm = {k: workspace.get(k) for k in ("query", "entities", "themes", "sectors", "compact", "theme_rows", "sector_rows", "macro")}
        ctx_for_llm["web_evidence"] = [{"title": e["title"], "url": e["url"], "snippet": (e.get("snippet") or "")[:600], "publisher": e.get("publisher"), "published": e.get("published")}
                                       for e in (workspace.get("web") or {}).get("evidence", [])]
        ctx_for_llm["filings"] = workspace.get("filings_search")
        prompt = (f"Produce a structured research brief for: {query}\n\nAnswer: What changed? Why might it matter? What financial evidence supports it? "
                  f"What data contradicts it? What could invalidate the thesis? What should be monitored next?\nEnd with 'Data Sources'.\n\n"
                  f"CONTEXT JSON:\n{cx.to_prompt_json(ctx_for_llm)}")
        try:
            r = await provider.complete(SYSTEM_PROMPT, [{"role": "user", "content": prompt}])
            workspace["synthesis"] = {"text": r.text, "provider": r.provider, "model": r.model}
        except ProviderError as exc:
            workspace["synthesis"] = {"error": exc.message}
    elif synthesize:
        workspace["synthesis"] = {"text": None, "provider": None, "note": "No AI provider configured — the workspace shows sourced data only."}
    workspace["elapsed"] = round(time.time() - started, 1)
    db.execute("INSERT INTO research_reports (query, kind, payload, created_at) VALUES (?,?,?,?)",
               (query, "workspace", json.dumps({k: workspace.get(k) for k in ("query", "entities", "synthesis")}, default=str), time.time()))
    return workspace


def recent_research() -> list[dict[str, Any]]:
    return db.query("SELECT id, query, created_at FROM research_reports ORDER BY id DESC LIMIT 20")


async def summarize_filing(url: str, form: str, company: str) -> dict[str, Any]:
    """AI summary of an SEC filing, always referencing the original document."""
    if not url.startswith("https://www.sec.gov/"):
        raise ValueError("Only sec.gov filing URLs can be summarized.")
    from backend.config import env
    from backend.utils import http
    text = await http.get_text("sec", url, headers={"User-Agent": env("SEC_USER_AGENT") or "OmniMarket admin@localhost"}, timeout=45)
    import re as _re
    plain = _re.sub(r"<[^>]+>", " ", text)
    plain = _re.sub(r"&nbsp;|&#160;", " ", plain)
    plain = _re.sub(r"\s+", " ", plain)[:120000]
    provider = active_provider()
    if not provider:
        return {"summary": None, "source_url": url, "note": "Configure an AI provider to summarize filings. The original document is linked.",
                "excerpt": plain[:1500]}
    prompt = (f"Summarize this SEC {form} filing from {company}. Focus on material information: results, guidance, risks, transactions, governance, "
              f"and anything unusual. Quote figures exactly as filed and reference section names. Do not add information that is not in the text.\n\n"
              f"SOURCE: {url}\n\nFILING TEXT (truncated):\n{plain}")
    r = await provider.complete(SYSTEM_PROMPT, [{"role": "user", "content": prompt}], max_tokens=8000)
    return {"summary": r.text, "source_url": url, "provider": r.provider, "model": r.model}
