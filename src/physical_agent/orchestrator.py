from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import Settings
from .editor import execute_edit
from .openai_compat import OpenAICompatClient
from .planner import plan_edit
from .router import select_route
from .verifier import verify_edit


@dataclass
class AgentRun:
    run_dir: str
    instruction: str
    source_image: str
    final_image: str | None = None
    accepted: bool = False
    calls: dict[str, int] = field(default_factory=lambda: {"planner": 0, "editor": 0, "verifier": 0})
    iterations: list[dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: float = 0.0


def run_agent(settings: Settings, source_image: Path, instruction: str, output_root: Path) -> AgentRun:
    started = time.time()
    run_dir = output_root / time.strftime("run_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=False)
    client = OpenAICompatClient(settings)
    state = AgentRun(run_dir=str(run_dir), instruction=instruction, source_image=str(source_image))
    current_image = source_image
    previous_failure: str | None = None

    for step in range(settings.max_retries + 1):
        step_dir = run_dir / f"step_{step:02d}"
        step_dir.mkdir(parents=True, exist_ok=True)

        plan = plan_edit(client, settings.planner_model, current_image, instruction, previous_failure)
        state.calls["planner"] += 1
        route = select_route(plan)
        write_json(step_dir / "plan.json", {"plan": plan, "route": route})

        edit_prompt = str(plan.get("edit_prompt") or instruction)
        candidate_path = step_dir / "candidate.png"
        execute_edit(client, settings.image_edit_model, current_image, edit_prompt, candidate_path)
        state.calls["editor"] += 1

        verification = verify_edit(
            client,
            settings.verifier_model,
            source_image,
            candidate_path,
            instruction,
            plan,
        )
        state.calls["verifier"] += 1
        write_json(step_dir / "verify.json", verification)

        step_record = {
            "step": step,
            "input_image": str(current_image),
            "candidate_image": str(candidate_path),
            "plan_path": str(step_dir / "plan.json"),
            "verify_path": str(step_dir / "verify.json"),
            "route": route,
            "accepted": bool(verification.get("pass")),
        }
        state.iterations.append(step_record)
        if verification.get("pass"):
            state.accepted = True
            state.final_image = str(candidate_path)
            break
        previous_failure = str(verification.get("repair_instruction") or verification.get("issues") or "Improve the failed edit.")
        current_image = candidate_path

    if state.final_image is None and state.iterations:
        state.final_image = state.iterations[-1]["candidate_image"]
    state.elapsed_seconds = round(time.time() - started, 3)
    write_json(run_dir / "run_state.json", asdict(state))
    return state


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
