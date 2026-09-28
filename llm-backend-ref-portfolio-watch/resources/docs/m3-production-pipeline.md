# M3 Production Pipeline

Sơ đồ Mermaid minh họa vòng đời CI/CD và Human-in-the-Loop (HITL) cho Portfolio Watch M3.

```mermaid
flowchart TD
    %% Định nghĩa các node
    Developer["👩‍💻 Developer"]
    PromptRegistry["📝 Prompt Registry\n(resources/prompts/)"]
    GithubPR["🐙 GitHub PR\n(eval-gate.yml)"]
    EvalGate{"⚖️ Eval Gate\n(backend.eval)"}
    Cache[".eval_cache"]
    Deploy["🚀 Deploy\n(Docker/ngrok)"]
    SmokeTest["💨 Smoke Test\n(deploy/smoke.py)"]
    Monitor["📊 Monitor\n(Langfuse/tracing)"]
    HITL["🧑‍⚖️ HITL Feedback\n(hitl_feedback.json)"]
    HitlToGolden["⚙️ hitl_to_golden_draft.py"]
    GoldenDraft["📂 Golden Draft\n(resources/eval/drafts/)"]

    %% Luồng đi
    Developer -->|Update Prompts| PromptRegistry
    PromptRegistry --> GithubPR
    GithubPR -->|Run eval subset| EvalGate
    EvalGate <-->|Hit/Miss| Cache
    EvalGate -->|Fail| Developer
    EvalGate -->|Pass (Merge)| Deploy
    Deploy -->|Verify| SmokeTest
    SmokeTest --> Monitor
    Monitor -->|Collect user ratings| HITL
    HITL -->|Thumbs down (<= 2)| HitlToGolden
    HitlToGolden -->|Generate draft cases| GoldenDraft
    GoldenDraft -->|Review & Add to v5_baseline| Developer
```
