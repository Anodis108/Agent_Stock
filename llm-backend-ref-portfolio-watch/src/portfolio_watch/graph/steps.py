from __future__ import annotations

from typing import Any


def build_steps_from_chunks(
    chunks: list[dict], final_error: str | None = None
) -> list[dict]:
    """Build steps[] from LangGraph stream(stream_mode="updates") chunks.

    Works for both chat graph and scan graph.
    """
    steps: list[dict] = []
    n = 1
    last_rewritten = None
    last_symbol = None

    def add(
        name: str,
        status: str,
        detail: str | None = None,
        input_data: Any = None,
        output_data: Any = None,
    ) -> None:
        nonlocal n
        step: dict[str, Any] = {"id": str(n), "name": name, "status": status}
        if detail is not None:
            step["detail"] = detail
        if input_data is not None:
            step["input"] = input_data
        if output_data is not None:
            step["output"] = output_data
        steps.append(step)
        n += 1

    for chunk in chunks:
        for node_name, output in chunk.items():
            if node_name == "rewrite_question":
                rewritten = output.get("rewritten")
                if rewritten:
                    last_rewritten = rewritten
                    last_symbol = rewritten.symbol
                    detail = rewritten.rewritten or rewritten.original or None
                    in_val = {"question": rewritten.original or ""}
                    out_val = {
                        "rewritten": rewritten.rewritten or "",
                        "symbol": rewritten.symbol,
                        "symbols": list(rewritten.symbols or []),
                    }
                    add(
                        "rewrite_question",
                        "done",
                        detail,
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "supervisor":
                routing = output.get("routing")
                if routing:
                    route = str(getattr(routing.route, "value", routing.route))
                    reason = f" — {routing.reason}" if routing.reason else ""
                    agents = list(routing.agents_to_call or [])
                    in_val = {
                        "question": getattr(last_rewritten, "rewritten", "")
                        or getattr(last_rewritten, "original", "")
                        or ""
                    }
                    out_val = {
                        "route": route,
                        "agents": agents,
                        "reason": routing.reason or "",
                    }
                    add(
                        "supervisor",
                        "done",
                        f"{route}: {agents}{reason}",
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "diagram_agent":
                diagram_res = output.get("diagram_result")
                if diagram_res:
                    add(
                        "diagram_agent",
                        "done",
                        "diagram rendered",
                        input_data={"symbol": last_symbol or ""},
                        output_data={
                            "diagram_pending": getattr(diagram_res, "diagram_pending", True),
                            "mermaid": getattr(diagram_res, "mermaid", None),
                            "graph_json": getattr(diagram_res, "graph_json", None),
                        }
                    )

            elif node_name == "workers":
                price = output.get("price")
                news = output.get("news")
                prices = output.get("prices") or ([price] if price is not None else [])
                news_list = output.get("news_list") or ([news] if news is not None else [])
                eval_result = output.get("eval_result")

                for p in prices:
                    if p is not None:
                        status = "error" if p.error else "done"
                        err = f" err={p.error}" if p.error else ""
                        in_val = {"symbol": p.symbol}
                        out_val = {
                            "symbol": p.symbol,
                            "latest_close": p.latest_close,
                            "change_pct": p.change_pct,
                            "error": p.error,
                        }
                        add(
                            "price_agent",
                            status,
                            f"{p.symbol} close={p.latest_close} chg={p.change_pct}{err}",
                            input_data=in_val,
                            output_data=out_val,
                        )

                for n_item in news_list:
                    if n_item is not None:
                        status = "error" if n_item.error else "done"
                        err = f" err={n_item.error}" if n_item.error else ""
                        n_sym = getattr(n_item, "symbol", "") or (last_symbol or "")
                        in_val = {"symbol": n_sym}
                        out_val = {
                            "symbol": n_sym,
                            "items_count": len(n_item.items or []),
                            "error": n_item.error,
                        }
                        add(
                            "news_agent",
                            status,
                            f"items={len(n_item.items or [])}{err}",
                            input_data=in_val,
                            output_data=out_val,
                        )

                if eval_result is not None:
                    ev_sym = (
                        getattr(eval_result, "symbol", "")
                        or (prices[0].symbol if prices else "")
                        or (last_symbol or "")
                    )
                    in_val = {"symbol": ev_sym}
                    out_val = {
                        "severity": str(eval_result.severity),
                        "confidence": getattr(eval_result.severity, "confidence", None),
                    }
                    add(
                        "eval_agent",
                        "done",
                        str(eval_result.severity),
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "answer_composer":
                compose = output.get("compose")
                if compose:
                    ans = compose.answer or ""
                    detail = ans[:200] if ans else None
                    if getattr(compose, "guardrail_violations", None):
                        detail = f"guardrail={compose.guardrail_violations!r}; {detail or ''}".strip()
                    syms = (
                        [p.symbol for p in (output.get("prices") or []) if p]
                        or ([last_symbol] if last_symbol else [])
                    )
                    in_val = {"symbols": syms}
                    out_val = {
                        "answer": ans[:300] if ans else "",
                        "guardrail_violations": getattr(compose, "guardrail_violations", None),
                    }
                    add(
                        "answer_composer",
                        "done",
                        detail,
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "fetch":
                price = output.get("price")
                news = output.get("news")

                if price is not None:
                    status = "error" if price.error else "done"
                    err = f" err={price.error}" if price.error else ""
                    in_val = {"symbol": price.symbol}
                    out_val = {
                        "symbol": price.symbol,
                        "latest_close": price.latest_close,
                        "change_pct": price.change_pct,
                        "error": price.error,
                    }
                    add(
                        "price_agent",
                        status,
                        f"{price.symbol} close={price.latest_close} chg={price.change_pct}{err}",
                        input_data=in_val,
                        output_data=out_val,
                    )

                if news is not None:
                    status = "error" if news.error else "done"
                    err = f" err={news.error}" if news.error else ""
                    in_val = {"symbol": getattr(news, "symbol", "") or (price.symbol if price else "")}
                    out_val = {
                        "symbol": getattr(news, "symbol", ""),
                        "items_count": len(news.items or []),
                        "error": news.error,
                    }
                    add(
                        "news_agent",
                        status,
                        f"items={len(news.items or [])}{err}",
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "event_classifier":
                routing = output.get("routing")
                if routing:
                    route = str(getattr(routing.route, "value", routing.route))
                    reason = f" — {routing.reason}" if routing.reason else ""
                    in_val = {"symbol": output.get("symbol") or ""}
                    out_val = {
                        "route": route,
                        "reason": routing.reason or "",
                    }
                    add(
                        "event_classifier",
                        "done",
                        f"{route}{reason}",
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "eval_agent":
                severity = output.get("severity")
                if severity:
                    in_val = {"symbol": output.get("symbol") or ""}
                    out_val = {"severity": str(severity)}
                    add(
                        "eval_agent",
                        "done",
                        str(severity),
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "synthesis_agent":
                alert = output.get("alert")
                if alert:
                    in_val = {"symbol": getattr(alert, "symbol", "")}
                    out_val = {
                        "alert_id": getattr(alert, "id", None),
                        "title": getattr(alert, "title", ""),
                        "status": str(getattr(alert, "status", "")),
                    }
                    add(
                        "synthesis_agent",
                        "done",
                        "alert composed",
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name == "gate2":
                pending = output.get("gate2_pending")
                if pending:
                    in_val = {"gate": "gate2"}
                    out_val = {"gate2_pending": True}
                    add(
                        "confidence_gate",
                        "done",
                        "gate2_pending=True",
                        input_data=in_val,
                        output_data=out_val,
                    )

            elif node_name in ("gate1_auto", "gate1_pending"):
                action = output.get("gate1_action")
                if action:
                    in_val = {"gate": "gate1"}
                    out_val = {"action": str(action)}
                    add(
                        "confidence_gate",
                        "done",
                        f"action={action}",
                        input_data=in_val,
                        output_data=out_val,
                    )

    if final_error:
        is_scan = any("fetch" in c for c in chunks if isinstance(c, dict))
        add(
            "scan" if is_scan else "chat",
            "error",
            final_error,
            input_data={"error": final_error},
            output_data={"error": final_error},
        )

    return steps

