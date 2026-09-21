from __future__ import annotations

def build_steps_from_chunks(chunks: list[dict], final_error: str | None = None) -> list[dict]:
    """
    Build steps[] from LangGraph stream(stream_mode="updates") chunks.
    Works for both chat graph and scan graph.
    """
    steps: list[dict] = []
    n = 1

    def add(name: str, status: str, detail: str | None = None) -> None:
        nonlocal n
        steps.append({"id": str(n), "name": name, "status": status, "detail": detail})
        n += 1

    for chunk in chunks:
        for node_name, output in chunk.items():
            if node_name == "rewrite_question":
                rewritten = output.get("rewritten")
                if rewritten:
                    detail = rewritten.rewritten or rewritten.original or None
                    add("rewrite_question", "done", detail)
            
            elif node_name == "supervisor":
                routing = output.get("routing")
                if routing:
                    route = str(getattr(routing.route, "value", routing.route))
                    reason = f" — {routing.reason}" if routing.reason else ""
                    agents = list(routing.agents_to_call or [])
                    add("supervisor", "done", f"{route}: {agents}{reason}")

            elif node_name == "workers":
                price = output.get("price")
                news = output.get("news")
                eval_result = output.get("eval_result")
                
                if price is not None:
                    status = "error" if price.error else "done"
                    err = f" err={price.error}" if price.error else ""
                    add("price_agent", status, f"{price.symbol} close={price.latest_close} chg={price.change_pct}{err}")
                
                if news is not None:
                    status = "error" if news.error else "done"
                    err = f" err={news.error}" if news.error else ""
                    add("news_agent", status, f"items={len(news.items or [])}{err}")
                
                if eval_result is not None:
                    add("eval_agent", "done", str(eval_result.severity))

            elif node_name == "answer_composer":
                compose = output.get("compose")
                if compose:
                    ans = compose.answer or ""
                    detail = ans[:200] if ans else None
                    if getattr(compose, "guardrail_violations", None):
                        detail = f"guardrail={compose.guardrail_violations!r}; {detail or ''}".strip()
                    add("answer_composer", "done", detail)

            elif node_name == "fetch":
                price = output.get("price")
                news = output.get("news")
                
                if price is not None:
                    status = "error" if price.error else "done"
                    err = f" err={price.error}" if price.error else ""
                    add("price_agent", status, f"{price.symbol} close={price.latest_close} chg={price.change_pct}{err}")
                
                if news is not None:
                    status = "error" if news.error else "done"
                    err = f" err={news.error}" if news.error else ""
                    add("news_agent", status, f"items={len(news.items or [])}{err}")

            elif node_name == "event_classifier":
                routing = output.get("routing")
                if routing:
                    route = str(getattr(routing.route, "value", routing.route))
                    reason = f" — {routing.reason}" if routing.reason else ""
                    add("event_classifier", "done", f"{route}{reason}")

            elif node_name == "eval_agent":
                severity = output.get("severity")
                if severity:
                    add("eval_agent", "done", str(severity))

            elif node_name == "synthesis_agent":
                alert = output.get("alert")
                if alert:
                    add("synthesis_agent", "done", "alert composed")

            elif node_name == "gate2":
                pending = output.get("gate2_pending")
                if pending:
                    add("confidence_gate", "done", "gate2_pending=True")

            elif node_name in ("gate1_auto", "gate1_pending"):
                action = output.get("gate1_action")
                if action:
                    add("confidence_gate", "done", f"action={action}")

    if final_error:
        add("scan" if "fetch" in [list(c.keys())[0] for c in chunks] else "chat", "error", final_error)

    return steps
