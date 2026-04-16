# 에이전트별 ACP 주의사항

이 문서는 `main.py`에서 선택 가능한 ACP coding agent별 실행 방식, 전제조건, 알려진 주의사항을 정리합니다.

현재 지원 agent:

- `claude-code`
- `codex`
- `opencode`
- `pi`

## 공통 동작

POC는 Python ACP client로 agent subprocess를 실행하고, ACP JSON-RPC 2.0 over stdio로 통신합니다.

기본 실행:

```bash
uv run python main.py
```

agent 선택:

```bash
uv run python main.py --agent claude-code
uv run python main.py --agent codex
uv run python main.py --agent opencode
uv run python main.py --agent pi
```

직접 agent 명령을 지정하려면:

```bash
uv run python main.py \
  --agent codex \
  --agent-command "npx -y @zed-industries/codex-acp@0.11.1"
```

현재 POC는 세션 생성 시 MCP server를 전달하지 않습니다.

```python
session = await agent.new_session(cwd=str(workspace), mcp_servers=[])
```

따라서 사용자 skill, slash command, MCP 동작 여부는 기본적으로 각 agent 또는 adapter가 자체 사용자 설정을 어떻게 읽는지에 달려 있습니다.

## `claude-code`

기본 명령:

```bash
npx -y @agentclientprotocol/claude-agent-acp
```

확인한 패키지 버전:

```text
@agentclientprotocol/claude-agent-acp@0.28.0
```

특징:

- Claude Agent SDK 기반 ACP adapter입니다.
- Claude Code 기능을 ACP-compatible agent로 노출합니다.
- context mention, 이미지, tool call, permission request, edit review, TODO list, interactive/background terminal, slash command, client MCP server 등을 지원합니다.

주의사항:

- Claude 인증이 완료되어 있어야 합니다.
- 이 POC는 permission 요청이 오면 기본적으로 `allow_once` 또는 `allow_always`를 자동 선택합니다.
- 실제 코드베이스나 중요한 작업에 적용할 때는 자동 허용 정책을 신중히 조정해야 합니다.
- 이 POC는 `mcp_servers=[]`로 세션을 생성하므로 ACP client에서 MCP server 목록을 주입하는 흐름은 아직 사용하지 않습니다.
- Claude Code 자체에 이미 설정된 MCP가 로딩되는지는 Claude Agent SDK/adapter의 설정 로딩 방식에 의존하므로 실제 환경에서 확인이 필요합니다.

## `codex`

기본 명령:

```bash
npx -y @zed-industries/codex-acp
```

확인한 패키지 버전:

```text
@zed-industries/codex-acp@0.11.1
```

특징:

- Codex를 ACP-compatible coding agent로 실행하는 adapter입니다.
- Codex 인증과 설정을 사용합니다.

주의사항:

- Codex 인증이 완료되어 있어야 합니다.
- Codex에 이미 등록된 MCP, skill, 지침이 있다면 adapter가 그것을 사용하는지 여부는 `@zed-industries/codex-acp` 구현에 달려 있습니다.
- 이 POC에서는 MCP를 전달하지 않으므로 client-provided MCP는 동작하지 않습니다.
- 큰 tool/update payload가 한 줄짜리 ACP JSON-RPC 메시지로 전송될 수 있습니다.
- 아래 에러가 발생하면 stdio buffer limit을 키워 실행합니다.

```text
ValueError: Separator is not found, and chunk exceed the limit
```

예:

```bash
uv run python main.py --agent codex --stdio-buffer-limit-mb 200
```

## `opencode`

기본 명령:

```bash
npx -y opencode-ai acp
```

확인한 패키지 버전:

```text
opencode-ai@1.4.6
```

특징:

- `opencode-ai` 패키지는 `opencode` 바이너리를 제공합니다.
- ACP 모드는 `opencode acp` 명령으로 실행합니다.
- 전역 설치된 `opencode`를 사용하려면 아래처럼 직접 명령을 지정할 수 있습니다.

```bash
uv run python main.py \
  --agent opencode \
  --agent-command "opencode acp"
```

주의사항:

- OpenCode provider/API key 설정이 먼저 완료되어 있어야 합니다.
- OpenCode 버전과 provider 설정에 따라 최초 실행 시 interactive 설정이 필요할 수 있습니다.
- 이 POC는 agent subprocess의 stdio를 ACP JSON-RPC 통신에 사용하므로, 인증이나 설정은 사전에 터미널에서 완료하는 편이 안전합니다.
- 일부 OpenCode ACP 버전은 `session/close`를 구현하지 않아 `"Method not found": session/close`를 반환할 수 있습니다.
- 이 POC는 작업 완료 후 `session/close`가 미지원이면 경고만 출력하고 정상 종료를 계속합니다.
- OpenCode에 skill, plugin, MCP 개념이 설정되어 있다면 `opencode acp`가 평소 CLI 실행과 동일하게 설정을 읽는지 실제 환경에서 확인해야 합니다.

## `pi`

기본 명령:

```bash
npx -y pi-acp
```

확인한 adapter 버전:

```text
pi-acp@0.0.25
```

확인한 Pi CLI 패키지 버전:

```text
@mariozechner/pi-coding-agent@0.67.3
```

특징:

- `pi-acp`는 ACP JSON-RPC 2.0 over stdio를 받아 내부적으로 `pi --mode rpc`를 실행하는 bridge adapter입니다.
- Pi가 직접 skill을 로드하며 ACP 세션에서도 사용할 수 있습니다.
- 파일 기반 slash command도 지원합니다.

전제조건:

`pi-acp` 자체는 `npx`로 실행할 수 있지만, adapter가 실행할 `pi` 바이너리는 별도로 설치되어 `PATH`에서 접근 가능해야 합니다.

```bash
npm install -g @mariozechner/pi-coding-agent
```

주의사항:

- Pi의 model provider/API key 설정은 별도로 완료해야 합니다.
- `pi-acp` README 기준으로 MVP 성격의 adapter이며 일부 ACP 기능은 미구현이거나 제한됩니다.
- ACP filesystem delegation(`fs/*`)과 ACP terminal delegation(`terminal/*`)을 사용하지 않습니다. Pi가 직접 로컬 파일 읽기/쓰기와 명령 실행을 수행합니다.
- ACP params의 MCP server 정보는 세션 상태에 저장되지만 Pi로 직접 연결되지는 않습니다.
- assistant streaming은 별도 thought stream이 아니라 `agent_message_chunk`로 전달됩니다.
- Zed 중심으로 개발되어 다른 ACP client에서는 호환성 차이가 있을 수 있습니다.

## 사용자 Skill 및 MCP 정리

| Agent | 기존 사용자 skill/command | 기존 agent 설정 | ACP client가 넘긴 MCP |
| --- | --- | --- | --- |
| `claude-code` | 가능성 높음 | 가능성 높음 | adapter는 client MCP server를 지원하지만 현재 POC는 미전달 |
| `codex` | 구현 의존 | 가능성 있음 | 현재 POC는 미전달 |
| `opencode` | 구현 의존 | 가능성 있음 | 현재 POC는 미전달 |
| `pi` | 가능성 높음 | 가능성 높음 | 제한적, `pi-acp` README 기준 직접 연결 안 됨 |

MCP 전달까지 검증하려면 이 POC에 `--mcp-server` 같은 옵션을 추가하고 `agent.new_session(..., mcp_servers=[...])`에 값을 넣어야 합니다. 다만 agent별로 이를 실제로 사용하는지는 별도 테스트가 필요합니다.
