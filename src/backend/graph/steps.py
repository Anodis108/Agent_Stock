from __future__ import annotations

from typing import Any


def build_steps_from_chunks(
    chunks: list[dict],
    final_error: str | None = None,
    timings: dict[str, float] | None = None,
) -> list[dict]:
    """Build steps[] from LangGraph stream(stream_mode="updates") chunks.

    Works for both chat graph and scan graph with execution timing.
    """
    steps: list[dict] = []
    n = 1
    last_rewritten = None
    last_symbol = None
    node_timings = timings or {}

    def add(
        name: str,
        status: str,
        detail: str | None = None,
        input_data: Any = None,
        output_data: Any = None,
        duration_s: float | None = None,
        static_info: Any = None,
    ) -> None:
        nonlocal n
        step: dict[str, Any] = {"id": str(n), "name": name, "status": status}
        if duration_s is not None:
            step["duration_s"] = round(float(duration_s), 3)
            step["duration_ms"] = int(round(float(duration_s) * 1000))
        if detail is not None:
            step["detail"] = detail
        if input_data is not None:
            step["input"] = input_data
        if static_info is not None:
            step["static_info"] = static_info
        if output_data is not None:
            step["output"] = output_data
        steps.append(step)
        n += 1

    try:
        from backend.infra.llm.prompt_registry import registry
        _reg = registry()
    except Exception:
        _reg = None

    def _get_reg_prompt(name: str, fallback_desc: str) -> str:
        if _reg:
            try:
                p_obj = _reg.get(name, "production")
                return f"[{p_obj.name} v{p_obj.version} - Model: {p_obj.model}]\n\n{p_obj.template}"
            except Exception:
                pass
        return fallback_desc

    info_guardrail_rule = "[Rule Engine] Regex & Zero-Tolerance Policy: Chặn Prompt Injection, Out-of-scope, Cổ phiếu quốc tế."
    info_guardrail_refusal = "[Safety Fallback Engine] Phản hồi từ chối chuẩn mực khi câu hỏi vi phạm chính sách an toàn hoặc nằm ngoài phạm vi chứng khoán VN."
    info_price_agent = "[Tool Worker] Vnstock API: Truy xuất dữ liệu thời gian thực (giá khớp lệnh, giá đóng cửa close, % biến động và lịch sử giá kỹ thuật)."
    info_chart_agent = "[Visualization Worker] Chart Generator: Tạo biểu đồ nến kỹ thuật (candlestick) hoặc đường giá xu hướng lịch sử 10-30 phiên từ dữ liệu Vnstock."
    info_gate = "[Human-in-the-Loop & Confidence Gate] Đánh giá ngưỡng tin cậy (Threshold >= 0.70) để tự động duyệt phát cảnh báo hoặc chuyển vào hàng đợi phê duyệt."

    for chunk in chunks:
        for node_name, output in chunk.items():
            if node_name == "pre_rewrite_guardrail":
                res = output.get("guardrail_result")
                is_safe = getattr(res, "is_safe", True) if res else True
                category = getattr(res, "category", "safe") if res else "safe"
                reason = getattr(res, "reason", "") if res else ""
                status_str = "done" if is_safe else "blocked"
                add(
                    "pre_rewrite_guardrail",
                    status_str,
                    f"{category}: {reason}",
                    input_data={"question": output.get("question", "")},
                    output_data={"is_safe": is_safe, "category": category, "reason": reason},
                    duration_s=node_timings.get("pre_rewrite_guardrail"),
                    static_info=info_guardrail_rule,
                )

            elif node_name == "guardrail_refusal":
                add(
                    "guardrail_refusal",
                    "done",
                    output.get("answer", ""),
                    output_data={"answer": output.get("answer", "")},
                    duration_s=node_timings.get("guardrail_refusal"),
                    static_info=info_guardrail_refusal,
                )

            elif node_name == "rewrite_question":
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
                    rw_prompt = _get_reg_prompt(
                        "rewrite_question",
                        "[Prompt] Chuẩn hóa câu hỏi, coreference resolution, trích xuất mã cổ phiếu và phân rã ý định.",
                    )
                    add(
                        "rewrite_question",
                        "done",
                        detail,
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=node_timings.get("rewrite_question"),
                        static_info=rw_prompt,
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
                    sv_prompt = _get_reg_prompt(
                        "supervisor_routing",
                        "[Prompt] Phân tích câu hỏi người dùng và điều phối các worker agents (price, news, chart, eval, diagram).",
                    )
                    add(
                        "supervisor",
                        "done",
                        f"{route}: {agents}{reason}",
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=node_timings.get("supervisor"),
                        static_info=sv_prompt,
                    )

            elif node_name == "diagram_agent":
                diagram_res = output.get("diagram_result")
                if diagram_res:
                    diag_prompt = _get_reg_prompt(
                        "diagram_plan",
                        "[Diagram Engine] Lên kế hoạch và tạo mã Mermaid biểu diễn luồng quan hệ doanh nghiệp hoặc dữ liệu.",
                    )
                    add(
                        "diagram_agent",
                        "done",
                        "diagram rendered",
                        input_data={"symbol": last_symbol or ""},
                        output_data={
                            "diagram_pending": getattr(diagram_res, "diagram_pending", True),
                            "mermaid": getattr(diagram_res, "mermaid", None),
                            "graph_json": getattr(diagram_res, "graph_json", None),
                        },
                        duration_s=node_timings.get("diagram_agent"),
                        static_info=diag_prompt,
                    )

            elif node_name == "workers":
                price = output.get("price")
                news = output.get("news")
                prices = output.get("prices") or ([price] if price is not None else [])
                news_list = output.get("news_list") or ([news] if news is not None else [])
                eval_result = output.get("eval_result")
                w_dur = node_timings.get("workers")

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
                            duration_s=w_dur,
                            static_info=info_price_agent,
                        )

                news_prompt = _get_reg_prompt(
                    "news_agent_react",
                    "[Tool Worker] Vnstock News API / ReAct: Thu thập tin tức doanh nghiệp, sự kiện tài chính, công bố thông tin gần nhất.",
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
                            duration_s=w_dur,
                            static_info=news_prompt,
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
                    eval_prompt = _get_reg_prompt(
                        "eval_severity",
                        "[Risk Engine] Đánh giá mức độ nghiêm trọng (high/medium/low/none) của tin tức và biến động giá đối với doanh nghiệp.",
                    )
                    add(
                        "eval_agent",
                        "done",
                        str(eval_result.severity),
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=w_dur,
                        static_info=eval_prompt,
                    )

                chart_res = output.get("chart_result")
                if chart_res is not None:
                    c_status = "done" if getattr(chart_res, "success", True) else "error"
                    c_url = getattr(chart_res, "url", None)
                    c_err = getattr(chart_res, "error", None)
                    c_detail = c_url or (f"err={c_err}" if c_err else "chart generated")
                    c_syms = getattr(chart_res, "symbols", None) or (
                        [p.symbol for p in prices if p and p.symbol]
                        or ([last_symbol] if last_symbol else [])
                    )
                    add(
                        "chart_agent",
                        c_status,
                        c_detail,
                        input_data={"symbols": c_syms},
                        output_data={
                            "success": getattr(chart_res, "success", True),
                            "url": c_url,
                            "chart_type": getattr(chart_res, "chart_type", "price_history"),
                            "error": c_err,
                        },
                        duration_s=w_dur,
                        static_info=info_chart_agent,
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
                    comp_prompt = _get_reg_prompt(
                        "answer_compose",
                        "[Prompt] Tổng hợp câu trả lời dựa trên facts thu thập từ các worker, tuân thủ guardrail tài chính.",
                    )
                    add(
                        "answer_composer",
                        "done",
                        detail,
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=node_timings.get("answer_composer"),
                        static_info=comp_prompt,
                    )

            elif node_name == "fetch":
                price = output.get("price")
                news = output.get("news")
                f_dur = node_timings.get("fetch")

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
                        duration_s=f_dur,
                        static_info=info_price_agent,
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
                    news_prompt = _get_reg_prompt(
                        "news_agent_react",
                        "[Tool Worker] Vnstock News API / ReAct: Thu thập tin tức doanh nghiệp, sự kiện tài chính, công bố thông tin gần nhất.",
                    )
                    add(
                        "news_agent",
                        status,
                        f"items={len(news.items or [])}{err}",
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=f_dur,
                        static_info=news_prompt,
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
                    event_prompt = _get_reg_prompt(
                        "event_classification",
                        "[Event Classifier] Phân loại sự kiện định lượng / định tính từ dữ liệu quét biến động thị trường.",
                    )
                    add(
                        "event_classifier",
                        "done",
                        f"{route}{reason}",
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=node_timings.get("event_classifier"),
                        static_info=event_prompt,
                    )

            elif node_name == "eval_agent":
                severity = output.get("severity")
                if severity:
                    in_val = {"symbol": output.get("symbol") or ""}
                    out_val = {"severity": str(severity)}
                    eval_prompt = _get_reg_prompt(
                        "eval_severity",
                        "[Risk Engine] Đánh giá mức độ nghiêm trọng (high/medium/low/none) của tin tức và biến động giá đối với doanh nghiệp.",
                    )
                    add(
                        "eval_agent",
                        "done",
                        str(severity),
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=node_timings.get("eval_agent"),
                        static_info=eval_prompt,
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
                    synth_prompt = _get_reg_prompt(
                        "synthesis_alert",
                        "[Synthesis Engine] Tổng hợp thông tin từ Price/News/Eval để soạn thảo cảnh báo danh mục đầu tư.",
                    )
                    add(
                        "synthesis_agent",
                        "done",
                        "alert composed",
                        input_data=in_val,
                        output_data=out_val,
                        duration_s=node_timings.get("synthesis_agent"),
                        static_info=synth_prompt,
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
                        duration_s=node_timings.get("gate2"),
                        static_info=info_gate,
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
                        duration_s=node_timings.get(node_name),
                        static_info=info_gate,
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

