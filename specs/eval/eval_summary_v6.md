=== Eval report ===
Tổng: 20/20 passed (100%)
Theo slice:
  - lookup: 2/2 passed (100%)
  - news: 2/2 passed (100%)
  - indicator: 2/2 passed (100%)
  - comparison: 2/2 passed (100%)
  - portfolio: 2/2 passed (100%)
  - watchlist: 2/2 passed (100%)
  - chart: 2/2 passed (100%)
  - out_of_scope: 2/2 passed (100%)
  - injection: 2/2 passed (100%)
  - disclaimer: 2/2 passed (100%)
  - diagram: 0/0 passed (n/a)
Failures: (none)

=== Observations & Metrics ===
- Total Tokens: 19,259 tokens (Prompt: 17,592, Completion: 1,667)
- Total Cost: $0.0036 USD (~ 92 VND)
- Latency: Average TTFT 2.86s, Average End-to-end 4.31s
- Compliance Gates:
  - Rule Pass Rate: 100.0% (20/20)
  - Prompt Injection Blocked: 100.0% (2/2)
  - Out-of-scope Refused: 100.0% (2/2)
- Execution Trace: Ghi nhận 100% lộ trình Agent cho 20 cases (Chi tiết tại `specs/eval/eval_observations_v6.md`)