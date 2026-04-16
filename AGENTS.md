# Repository Instructions

이 저장소는 Python ACP client로 여러 coding agent를 실행하는 POC입니다. 작업 시 아래 사항을 지켜주세요.

## 기본 실행 및 검증

- Python 실행은 `uv`를 사용합니다.
- 기본 실행 명령:

```bash
uv run python main.py
```

- 변경 후 최소 검증:

```bash
uv run python -m py_compile main.py
uv run python main.py --help
```

- 실제 agent 실행은 로컬 인증과 provider 설정에 의존하므로, 자동 테스트처럼 항상 성공한다고 가정하지 마세요.

## 지원 Agent

`main.py`의 `AGENT_COMMANDS`가 현재 지원 agent 목록의 기준입니다.

- `claude-code`: `npx -y @agentclientprotocol/claude-agent-acp`
- `codex`: `npx -y @zed-industries/codex-acp`
- `opencode`: `npx -y opencode-ai acp`
- `pi`: `npx -y pi-acp`

기본 agent는 `claude-code`입니다.

agent별 자세한 ACP 정보와 주의사항은 `doc/agent-notes.md`를 먼저 확인하세요.

## ACP 및 MCP 주의사항

- 현재 POC는 `agent.new_session(cwd=str(workspace), mcp_servers=[])`로 세션을 생성합니다.
- 즉, ACP client가 MCP server 목록을 agent에 전달하는 흐름은 아직 구현되어 있지 않습니다.
- 사용자 skill, slash command, MCP 동작 여부는 각 agent 또는 adapter가 자체 사용자 설정을 읽는 방식에 의존합니다.
- MCP 전달 기능을 추가할 때는 agent별 구현 차이를 문서화하고, `doc/agent-notes.md`도 함께 갱신하세요.

## Agent별 구현 주의사항

- `claude-code`
  - permission 요청이 올 수 있습니다.
  - 현재 POC는 `allow_once` 또는 `allow_always`를 자동 선택합니다.
  - 자동 허용 정책을 바꿀 때는 보안 영향을 README와 문서에 반영하세요.

- `codex`
  - 큰 ACP JSON-RPC 메시지를 한 줄로 보낼 수 있습니다.
  - `ValueError: Separator is not found, and chunk exceed the limit`가 발생하면 `--stdio-buffer-limit-mb` 값을 키워야 합니다.
  - 기본 stdio buffer limit은 `50 MiB`입니다.

- `opencode`
  - 일부 버전은 `session/close`를 구현하지 않아 JSON-RPC `Method not found`를 반환할 수 있습니다.
  - 현재 POC는 `session/close`의 `-32601` 에러만 경고로 처리하고 종료를 계속합니다.
  - 다른 `RequestError`까지 무시하지 마세요.

- `pi`
  - `pi-acp`는 내부적으로 `pi --mode rpc`를 실행합니다.
  - `pi-acp`는 `npx`로 실행할 수 있지만 `pi` CLI는 별도로 설치되어 `PATH`에 있어야 합니다.
  - `pi-acp` README 기준으로 ACP filesystem/terminal delegation과 MCP 연결에는 제한이 있습니다.

## 문서 유지보수

- 실행 방법이나 옵션이 바뀌면 `README.md`를 함께 갱신하세요.
- agent별 지원 여부, 패키지 버전, 제한사항이 바뀌면 `doc/agent-notes.md`를 함께 갱신하세요.
- README에는 빠른 사용법을 유지하고, 긴 설명은 `doc/agent-notes.md`로 분리하는 방향을 선호합니다.

## Git 주의사항

- 사용자의 기존 변경사항을 되돌리지 마세요.
- 커밋 전에는 `git status --short`로 변경 파일을 확인하세요.
- 현재 원격 저장소는 `origin`이며 `main` 브랜치가 `origin/main`을 추적합니다.
