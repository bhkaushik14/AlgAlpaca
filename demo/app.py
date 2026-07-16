"""Local research interface for the final QLoRA adapter."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import gradio as gr

from codellama_algebra.demo_service import (
    DemoBusyError,
    DemoInputError,
    DemoPipeline,
    get_real_generator,
)

ADAPTER_ENV = "CODELLAMA_ALGEBRA_ADAPTER_PATH"
LAUNCH_CONFIG = {
    "server_name": "127.0.0.1",
    "share": False,
    "show_api": False,
    "enable_monitoring": False,
    "mcp_server": False,
    "strict_cors": True,
}
WARNING = (
    "Generated programs may be incorrect. Successful execution does not guarantee mathematical "
    "correctness. Execution occurs in a restricted local research sandbox that is not suitable "
    "for public multi-user hosting."
)


def _outputs(result):
    return (
        result.pipeline_status,
        result.extracted_code,
        result.stdout,
        result.stderr,
        result.wrapper_status,
        result.syntax_status,
        result.policy_status,
        result.execution_status,
        result.observable_status,
        result.parsed_output,
        result.raw_response,
    )


def build_app(generator: Callable | None = None, adapter_path: Path | None = None) -> gr.Blocks:
    pipeline = DemoPipeline(generator) if generator is not None else None

    def handle(problem: str):
        nonlocal pipeline
        try:
            if pipeline is None:
                configured = adapter_path or (
                    Path(os.environ[ADAPTER_ENV]) if os.environ.get(ADAPTER_ENV) else None
                )
                if configured is None:
                    raise RuntimeError(
                        f"Set {ADAPTER_ENV} or pass --adapter-path before starting the demo."
                    )
                pipeline = DemoPipeline(get_real_generator(configured))
            return _outputs(pipeline.run(problem))
        except (DemoInputError, DemoBusyError, RuntimeError, ValueError) as exc:
            message = (
                str(exc)
                if not isinstance(exc, RuntimeError)
                else "Local model service unavailable. Check the configured local adapter and base cache."
            )
            return (
                message,
                "",
                "",
                "",
                "not run",
                "not run",
                "not run",
                "not run",
                "not_run",
                "",
                "",
            )

    with gr.Blocks(
        title="CodeLlama Algebra-to-Code — Local Research Demo",
        analytics_enabled=False,
        delete_cache=(60, 60),
    ) as app:
        gr.Markdown("# CodeLlama Algebra-to-Code\nLocal final-adapter research demonstration")
        gr.Markdown(f"> **Safety warning:** {WARNING}")
        problem = gr.Textbox(
            label="Algebra problem",
            lines=5,
            max_lines=10,
            placeholder="Solve 7x - 9 = 40 for x.",
        )
        with gr.Row():
            submit = gr.Button("Generate and run", variant="primary")
            clear = gr.ClearButton()
        status = gr.Textbox(label="Pipeline status", interactive=False)
        code = gr.Code(label="Exact extracted Python", language="python", interactive=False)
        with gr.Row():
            stdout = gr.Textbox(label="Bounded stdout", interactive=False)
            stderr = gr.Textbox(label="Bounded sanitized stderr", interactive=False)
        with gr.Row():
            wrapper = gr.Textbox(label="Wrapper / extraction", interactive=False)
            syntax = gr.Textbox(label="Syntax", interactive=False)
            policy = gr.Textbox(label="Static policy", interactive=False)
            execution = gr.Textbox(label="Execution", interactive=False)
        observable = gr.Textbox(label="Observable program output status", interactive=False)
        parsed = gr.Textbox(label="Parsed output (not a verified solution)", interactive=False)
        with gr.Accordion("Advanced: raw model response", open=False):
            raw = gr.Textbox(label="Exact raw response", lines=10, interactive=False)
        gr.Examples(
            examples=[
                ["Find t if 11t + 8 = 85."],
                ["Factor z^2 - 13z + 36."],
                ["Solve u + v = 15 and 2u - v = 6."],
            ],
            inputs=problem,
        )
        outputs = [
            status,
            code,
            stdout,
            stderr,
            wrapper,
            syntax,
            policy,
            execution,
            observable,
            parsed,
            raw,
        ]
        submit.click(handle, inputs=problem, outputs=outputs, api_name=False, concurrency_limit=1)
        clear.add([problem, *outputs])
    app.queue(api_open=False, max_size=1, default_concurrency_limit=1)
    return app


def launch_app(app: gr.Blocks, **overrides):
    config = {**LAUNCH_CONFIG, **overrides}
    return app.launch(**config)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-path", type=Path)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    launch_app(build_app(adapter_path=args.adapter_path), server_port=args.port)


if __name__ == "__main__":
    main()
