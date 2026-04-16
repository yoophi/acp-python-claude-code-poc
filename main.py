from __future__ import annotations

import argparse
import asyncio
import os
import shlex
import signal
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acp import PROTOCOL_VERSION, spawn_agent_process, text_block
from acp.schema import (
    AllowedOutcome,
    ClientCapabilities,
    CreateTerminalResponse,
    FileSystemCapabilities,
    Implementation,
    KillTerminalResponse,
    PermissionOption,
    ReadTextFileResponse,
    ReleaseTerminalResponse,
    RequestPermissionResponse,
    TerminalExitStatus,
    TerminalOutputResponse,
    ToolCallUpdate,
    WaitForTerminalExitResponse,
    WriteTextFileResponse,
)


DEFAULT_GOAL = "todo rest api 를 nodejs 로 작성해주세요. 데이터는 json 파일로 저장해주세요"
DEFAULT_WORKDIR = "~/tmp/todo-api-acp-test"
DEFAULT_AGENT = "claude-code"
DEFAULT_STDIO_BUFFER_LIMIT_MB = 50
AGENT_COMMANDS = {
    "claude-code": "npx -y @agentclientprotocol/claude-agent-acp",
    "codex": "npx -y @zed-industries/codex-acp",
}
BLUE = "\033[34m"
RESET = "\033[0m"


def agent_print(text: str, *, end: str = "\n") -> None:
    print(f"{BLUE}{text}{RESET}", end=end, flush=True)


@dataclass
class TerminalState:
    process: asyncio.subprocess.Process
    output_limit: int
    output: bytearray = field(default_factory=bytearray)
    reader_task: asyncio.Task[None] | None = None


class PocClient:
    def __init__(self, workspace: Path, *, auto_allow: bool) -> None:
        self.workspace = workspace.resolve()
        self.auto_allow = auto_allow
        self.terminals: dict[str, TerminalState] = {}

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        del session_id, kwargs
        agent_print(f"\n[permission] {tool_call.title}")
        if tool_call.raw_input is not None:
            agent_print(f"[permission.input] {tool_call.raw_input}")
        for index, option in enumerate(options, start=1):
            agent_print(f"  {index}. {option.name} ({option.kind}, id={option.option_id})")

        selected = self._select_permission_option(options)
        if selected is None:
            raise RuntimeError("No allow permission option was offered by the agent.")
        agent_print(f"[permission.selected] {selected.name}")
        return RequestPermissionResponse(outcome=AllowedOutcome(outcome="selected", option_id=selected.option_id))

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        del session_id, kwargs
        kind = getattr(update, "session_update", type(update).__name__)
        if kind == "agent_message_chunk":
            text = getattr(getattr(update, "content", None), "text", None)
            if text:
                agent_print(text, end="")
                return
        if kind == "agent_thought_chunk":
            text = getattr(getattr(update, "content", None), "text", None)
            if text:
                agent_print(f"\n[thought] {text}")
                return
        if kind == "plan":
            agent_print("\n[plan]")
            for entry in update.entries:
                agent_print(f"- {entry.status}: {entry.content}")
            return
        if kind in {"tool_call", "tool_call_update"}:
            status = f" {update.status}" if getattr(update, "status", None) else ""
            agent_print(f"\n[tool]{status} {update.title}")
            if getattr(update, "locations", None):
                for location in update.locations:
                    agent_print(f"  path: {location.path}")
            return
        if kind == "usage_update":
            agent_print(f"\n[usage] context {update.used}/{update.size}")
            return
        agent_print(f"\n[{kind}]")

    async def read_text_file(
        self,
        path: str,
        session_id: str,
        limit: int | None = None,
        line: int | None = None,
        **kwargs: Any,
    ) -> ReadTextFileResponse:
        del session_id, kwargs
        target = self._resolve_inside_workspace(path)
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        start = max((line or 1) - 1, 0)
        selected = lines[start : start + limit] if limit is not None else lines[start:]
        return ReadTextFileResponse(content="".join(selected))

    async def write_text_file(
        self,
        content: str,
        path: str,
        session_id: str,
        **kwargs: Any,
    ) -> WriteTextFileResponse:
        del session_id, kwargs
        target = self._resolve_inside_workspace(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"\n[fs.write] {target}")
        return WriteTextFileResponse()

    async def create_terminal(
        self,
        command: str,
        session_id: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: list[Any] | None = None,
        output_byte_limit: int | None = None,
        **kwargs: Any,
    ) -> CreateTerminalResponse:
        del session_id, kwargs
        working_dir = self._resolve_inside_workspace(cwd) if cwd else self.workspace
        command_env = os.environ.copy()
        for item in env or []:
            command_env[item.name] = item.value

        argv = [command, *(args or [])]
        terminal_id = str(uuid.uuid4())
        print(f"\n[terminal.create] {terminal_id}: {shlex.join(argv)} (cwd={working_dir})")
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=working_dir,
            env=command_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        state = TerminalState(process=process, output_limit=output_byte_limit or 256_000)
        state.reader_task = asyncio.create_task(self._capture_terminal_output(state))
        self.terminals[terminal_id] = state
        return CreateTerminalResponse(terminal_id=terminal_id)

    async def terminal_output(self, session_id: str, terminal_id: str, **kwargs: Any) -> TerminalOutputResponse:
        del session_id, kwargs
        state = self.terminals[terminal_id]
        return TerminalOutputResponse(
            output=self._terminal_text(state),
            truncated=len(state.output) >= state.output_limit,
            exit_status=self._terminal_exit_status(state),
        )

    async def wait_for_terminal_exit(
        self,
        session_id: str,
        terminal_id: str,
        **kwargs: Any,
    ) -> WaitForTerminalExitResponse:
        del session_id, kwargs
        state = self.terminals[terminal_id]
        await state.process.wait()
        if state.reader_task:
            await state.reader_task
        print(f"\n[terminal.exit] {terminal_id}: {state.process.returncode}")
        return WaitForTerminalExitResponse(exit_code=state.process.returncode)

    async def kill_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> KillTerminalResponse:
        del session_id, kwargs
        state = self.terminals[terminal_id]
        if state.process.returncode is None:
            state.process.send_signal(signal.SIGTERM)
        return KillTerminalResponse()

    async def release_terminal(
        self,
        session_id: str,
        terminal_id: str,
        **kwargs: Any,
    ) -> ReleaseTerminalResponse:
        del session_id, kwargs
        self.terminals.pop(terminal_id, None)
        return ReleaseTerminalResponse()

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        agent_print(f"\n[ext.method] {method}: {params}")
        return {}

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        agent_print(f"\n[ext.notification] {method}: {params}")

    def on_connect(self, conn: Any) -> None:
        del conn

    def _select_permission_option(self, options: list[PermissionOption]) -> PermissionOption | None:
        if self.auto_allow:
            for kind in ("allow_once", "allow_always"):
                for option in options:
                    if option.kind == kind:
                        return option
        return next((option for option in options if option.kind.startswith("allow")), None)

    def _resolve_inside_workspace(self, path: str | Path) -> Path:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = self.workspace / target
        resolved = target.resolve()
        if resolved != self.workspace and self.workspace not in resolved.parents:
            raise PermissionError(f"Path escapes workspace: {resolved}")
        return resolved

    async def _capture_terminal_output(self, state: TerminalState) -> None:
        assert state.process.stdout is not None
        while True:
            chunk = await state.process.stdout.read(4096)
            if not chunk:
                return
            state.output.extend(chunk)
            if len(state.output) > state.output_limit:
                del state.output[: len(state.output) - state.output_limit]

    def _terminal_text(self, state: TerminalState) -> str:
        return state.output.decode("utf-8", errors="replace")

    def _terminal_exit_status(self, state: TerminalState) -> TerminalExitStatus | None:
        if state.process.returncode is None:
            return None
        if state.process.returncode < 0:
            return TerminalExitStatus(signal=str(-state.process.returncode))
        return TerminalExitStatus(exit_code=state.process.returncode)


async def run_poc(args: argparse.Namespace) -> int:
    workspace = Path(args.cwd).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    client = PocClient(workspace, auto_allow=args.auto_allow)
    agent_command = args.agent_command or AGENT_COMMANDS[args.agent]
    agent_argv = shlex.split(agent_command)
    if not agent_argv:
        raise ValueError("--agent-command cannot be empty")

    print(f"[poc] workspace: {workspace}")
    print(f"[poc] selected agent: {args.agent}")
    print(f"[poc] agent: {shlex.join(agent_argv)}")
    print(f"[poc] stdio buffer limit: {args.stdio_buffer_limit_mb} MiB")
    print("[poc] goal:")
    agent_print(args.goal)

    async with spawn_agent_process(
        client,
        agent_argv[0],
        *agent_argv[1:],
        cwd=workspace,
        transport_kwargs={"limit": args.stdio_buffer_limit_mb * 1024 * 1024},
    ) as (agent, process):
        init = await agent.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(
                fs=FileSystemCapabilities(read_text_file=True, write_text_file=True),
                terminal=True,
            ),
            client_info=Implementation(name="python-acp-agent-poc", title="Python ACP Agent POC", version="0.1.0"),
        )
        print(f"[poc] initialized agent: {init.agent_info.name} {init.agent_info.version}")

        session = await agent.new_session(cwd=str(workspace), mcp_servers=[])
        print(f"[poc] session: {session.session_id}")

        response = await agent.prompt([text_block(args.goal)], session_id=session.session_id)
        print(f"\n[poc] stop_reason: {response.stop_reason}")

        await agent.close_session(session.session_id)
        if process.returncode is not None and process.returncode != 0:
            print(f"[poc] agent process exited with {process.returncode}", file=sys.stderr)
            return process.returncode

    print("\n[poc] artifacts:")
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            print(f"- {path.relative_to(workspace)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an ACP coding agent and print the development result.")
    parser.add_argument("--goal", default=DEFAULT_GOAL, help="Goal text to send to the selected ACP agent.")
    parser.add_argument("--cwd", default=DEFAULT_WORKDIR, help="Workspace directory for generated artifacts.")
    parser.add_argument(
        "--agent",
        choices=sorted(AGENT_COMMANDS),
        default=DEFAULT_AGENT,
        help="ACP agent to run. Defaults to claude-code.",
    )
    parser.add_argument(
        "--agent-command",
        default=None,
        help="Override ACP agent command. If omitted, the command is selected from --agent.",
    )
    parser.add_argument(
        "--stdio-buffer-limit-mb",
        type=int,
        default=DEFAULT_STDIO_BUFFER_LIMIT_MB,
        help="Maximum size, in MiB, for one newline-delimited ACP JSON message from the agent.",
    )
    parser.add_argument(
        "--no-auto-allow",
        dest="auto_allow",
        action="store_false",
        help="Do not automatically select allow_once/allow_always permission options.",
    )
    parser.set_defaults(auto_allow=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_poc(args)))


if __name__ == "__main__":
    main()
