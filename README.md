# ACP Python Coding Agent POC

Agent Client Protocol(ACP)을 이용해 Python 클라이언트에서 coding agent를 실행하고, 목표 텍스트를 전달한 뒤 개발 산출물을 작업 디렉터리에 생성하는 POC입니다.

지원 agent:

- `claude-code`: `@agentclientprotocol/claude-agent-acp`
- `codex`: `@zed-industries/codex-acp`
- `opencode`: `opencode-ai acp`
- `pi`: `pi-acp`

에이전트별 자세한 ACP 정보와 주의사항은 [doc/agent-notes.md](doc/agent-notes.md)를 참고하세요.
Pi agent의 tool 출력 노이즈 처리 배경은 [doc/pi-tool-output-noise.md](doc/pi-tool-output-noise.md)를 참고하세요.
프로그램 동작 방식의 Mermaid graph 정리는 [doc/program-flow.md](doc/program-flow.md)를 참고하세요.

기본 agent는 `claude-code`입니다.

기본 목표:

```text
todo rest api 를 nodejs 로 작성해주세요. 데이터는 json 파일로 저장해주세요
```

기본 작업 디렉터리:

```text
~/tmp/todo-api-acp-test
```

## 준비 사항

- Python 3.12 이상
- `uv`
- Node.js 및 `npx`
- 선택한 agent의 인증이 완료된 환경
  - `claude-code`: Claude 사용 인증
  - `codex`: Codex 사용 인증
  - `opencode`: OpenCode provider 설정 및 인증
  - `pi`: Pi coding agent 설치 및 provider 설정

이 POC는 기본적으로 Claude Code ACP agent를 `npx`로 실행합니다.

```bash
npx -y @agentclientprotocol/claude-agent-acp
```

## 설치

저장소 루트에서 의존성을 동기화합니다.

```bash
uv sync
```

## 실행

기본 목표와 기본 작업 디렉터리로 실행합니다.

```bash
uv run python main.py
```

위 명령은 기본값인 `--agent claude-code`로 실행됩니다.

Codex agent로 실행하려면:

```bash
uv run python main.py --agent codex
```

OpenCode agent로 실행하려면:

```bash
uv run python main.py --agent opencode
```

Pi coding agent로 실행하려면:

```bash
uv run python main.py --agent pi
```

Codex agent가 큰 ACP 메시지를 보내는 경우를 대비해, 스크립트는 기본적으로 한 ACP JSON 메시지당 50MiB까지 읽도록 설정합니다.

실행하면 다음 흐름으로 동작합니다.

1. `~/tmp/todo-api-acp-test` 디렉터리를 생성합니다.
2. 선택한 ACP agent 프로세스를 실행합니다.
3. ACP `initialize`, `session/new`, `session/prompt` 요청을 보냅니다.
4. agent의 응답, plan, tool call, permission 요청을 콘솔에 출력합니다.
5. 작업 종료 후 생성된 파일 목록을 출력합니다.

콘솔 출력에서 agent와 주고받은 내용은 파란색으로 표시하고, POC 스크립트가 직접 출력하는 진행 로그는 기본 색상으로 표시합니다.

## 목표 또는 작업 디렉터리 변경

```bash
uv run python main.py \
  --goal "express 로 todo rest api 를 만들고 json 파일에 저장해주세요" \
  --cwd ~/tmp/my-acp-test
```

## Agent 선택 및 명령 변경

기본 agent는 Claude Code입니다.

```bash
uv run python main.py --agent claude-code
```

Codex agent를 사용하려면:

```bash
uv run python main.py --agent codex
```

OpenCode agent를 사용하려면:

```bash
uv run python main.py --agent opencode
```

Pi coding agent를 사용하려면:

```bash
uv run python main.py --agent pi
```

`claude-agent-acp`가 전역 설치되어 있다면 `npx` 대신 직접 실행할 수 있습니다.

```bash
uv run python main.py --agent claude-code --agent-command claude-agent-acp
```

특정 버전을 지정할 수도 있습니다.

```bash
uv run python main.py \
  --agent claude-code \
  --agent-command "npx -y @agentclientprotocol/claude-agent-acp@0.28.0"
```

Codex ACP agent 명령을 직접 지정하려면:

```bash
uv run python main.py \
  --agent codex \
  --agent-command "npx -y @zed-industries/codex-acp@0.11.1"
```

OpenCode ACP 명령을 직접 지정하려면:

```bash
uv run python main.py \
  --agent opencode \
  --agent-command "opencode acp"
```

Pi ACP adapter 명령을 직접 지정하려면:

```bash
uv run python main.py \
  --agent pi \
  --agent-command "npx -y pi-acp@0.0.25"
```

## Agent별 ACP 정보 및 주의사항

### `claude-code`

- 기본 실행 명령: `npx -y @agentclientprotocol/claude-agent-acp`
- 확인한 패키지 버전: `@agentclientprotocol/claude-agent-acp@0.28.0`
- ACP adapter가 Claude Agent SDK를 사용해 Claude Code 기능을 ACP로 노출합니다.
- context mention, 이미지, tool call, permission request, edit review, TODO list, interactive/background terminal, slash command, client MCP server 등을 지원합니다.
- Claude 인증이 완료되어 있어야 합니다.
- 이 POC는 permission 요청이 오면 기본적으로 `allow_once` 또는 `allow_always`를 자동 선택합니다. 실제 코드베이스에 적용할 때는 자동 허용 정책을 신중히 조정해야 합니다.

### `codex`

- 기본 실행 명령: `npx -y @zed-industries/codex-acp`
- 확인한 패키지 버전: `@zed-industries/codex-acp@0.11.1`
- Codex를 ACP-compatible coding agent로 실행하는 adapter입니다.
- Codex 인증이 완료되어 있어야 합니다.
- 큰 tool/update payload가 한 줄짜리 ACP JSON-RPC 메시지로 전송될 수 있습니다. `ValueError: Separator is not found, and chunk exceed the limit`가 발생하면 `--stdio-buffer-limit-mb`를 키워 실행합니다.
- 예:

```bash
uv run python main.py --agent codex --stdio-buffer-limit-mb 200
```

### `opencode`

- 기본 실행 명령: `npx -y opencode-ai acp`
- 확인한 패키지 버전: `opencode-ai@1.4.6`
- `opencode-ai` 패키지는 `opencode` 바이너리를 제공하며, ACP 모드는 `opencode acp` 명령으로 실행합니다.
- 전역 설치된 `opencode`를 사용하려면 `--agent-command "opencode acp"`로 덮어씁니다.
- OpenCode의 provider/API key 설정이 먼저 완료되어 있어야 합니다.
- OpenCode 버전과 provider 설정에 따라 최초 실행 시 interactive 설정이 필요할 수 있습니다. 이 POC는 agent subprocess의 stdio를 ACP JSON-RPC 통신에 사용하므로, 인증이나 설정은 사전에 터미널에서 완료하는 편이 안전합니다.
- 일부 OpenCode ACP 버전은 `session/close`를 구현하지 않아 `"Method not found": session/close`를 반환할 수 있습니다. 이 POC는 작업 완료 후 close가 미지원이면 경고만 출력하고 정상 종료를 계속합니다.

### `pi`

- 기본 실행 명령: `npx -y pi-acp`
- 확인한 adapter 버전: `pi-acp@0.0.25`
- 확인한 Pi CLI 패키지 버전: `@mariozechner/pi-coding-agent@0.67.3`
- `pi-acp`는 ACP JSON-RPC 2.0 over stdio를 받아 내부적으로 `pi --mode rpc`를 실행하는 bridge adapter입니다.
- `pi-acp` 자체는 `npx`로 실행할 수 있지만, adapter가 실행할 `pi` 바이너리는 별도로 설치되어 `PATH`에서 접근 가능해야 합니다.

```bash
npm install -g @mariozechner/pi-coding-agent
```

- Pi의 model provider/API key 설정은 별도로 완료해야 합니다.
- `pi-acp` README 기준으로 MVP 성격의 adapter이며 일부 ACP 기능은 미구현이거나 제한됩니다.
- 알려진 제한:
  - ACP filesystem delegation(`fs/*`)과 ACP terminal delegation(`terminal/*`)을 사용하지 않습니다. Pi가 직접 로컬 파일 읽기/쓰기와 명령 실행을 수행합니다.
  - ACP params의 MCP server 정보는 세션 상태에 저장되지만 Pi로 직접 연결되지는 않습니다.
  - assistant streaming은 별도 thought stream이 아니라 `agent_message_chunk`로 전달됩니다.
  - Zed 중심으로 개발되어 다른 ACP client에서는 호환성 차이가 있을 수 있습니다.

## 사용자 Skill 및 MCP 동작 범위

ACP agent로 실행할 때 사용자 skill, slash command, MCP server가 동작하는지는 크게 두 가지에 따라 달라집니다.

1. 선택한 coding agent 또는 ACP adapter가 자체 사용자 설정을 읽는지
2. ACP client가 `session/new` 요청에서 MCP server 목록을 전달했을 때 adapter가 이를 실제 agent에 연결하는지

현재 POC는 세션 생성 시 MCP server를 전달하지 않습니다.

```python
session = await agent.new_session(cwd=str(workspace), mcp_servers=[])
```

따라서 이 POC에서 MCP/skill 동작 여부는 기본적으로 각 agent가 자체 설정을 읽는 방식에 의존합니다.

| Agent | 기존 사용자 skill/command | 기존 agent 설정 | ACP client가 넘긴 MCP |
| --- | --- | --- | --- |
| `claude-code` | 가능성 높음 | 가능성 높음 | adapter는 client MCP server를 지원하지만 현재 POC는 미전달 |
| `codex` | 구현 의존 | 가능성 있음 | 현재 POC는 미전달 |
| `opencode` | 구현 의존 | 가능성 있음 | 현재 POC는 미전달 |
| `pi` | 가능성 높음 | 가능성 높음 | 제한적, `pi-acp` README 기준 직접 연결 안 됨 |

### `claude-code`

- 사용자 slash command, Claude Code 설정, 인증, 일부 로컬 환경은 Claude ACP adapter가 Claude Agent SDK/Claude Code 쪽 설정을 사용하므로 동작할 가능성이 높습니다.
- `@agentclientprotocol/claude-agent-acp` README 기준으로 client MCP server도 지원합니다.
- 다만 이 POC는 `mcp_servers=[]`로 세션을 만들기 때문에 ACP client에서 MCP 서버 목록을 주입하는 흐름은 아직 사용하지 않습니다.
- Claude Code 자체에 이미 설정된 MCP가 로딩되는지는 Claude Agent SDK/adapter의 설정 로딩 방식에 의존하므로 실제 환경에서 확인이 필요합니다.

### `codex`

- Codex ACP adapter가 Codex 설정과 인증을 읽습니다.
- Codex에 이미 등록된 MCP, skill, 지침이 있다면 adapter가 그것을 사용하는지 여부는 `@zed-industries/codex-acp` 구현에 달려 있습니다.
- 이 POC에서는 MCP를 전달하지 않으므로 client-provided MCP는 동작하지 않습니다.

### `opencode`

- OpenCode 자체 provider 설정과 OpenCode 설정은 사용할 수 있습니다.
- OpenCode에 skill, plugin, MCP 개념이 설정되어 있다면 `opencode acp`가 평소 CLI 실행과 동일하게 설정을 읽는지 확인해야 합니다.
- 이 POC에서는 MCP 서버를 ACP `session/new`로 전달하지 않습니다.

### `pi`

- `pi-acp` README 기준으로 skills는 Pi가 직접 로드하며 ACP 세션에서도 사용 가능합니다.
- 파일 기반 slash command도 지원합니다.
- MCP는 제한이 있습니다. `pi-acp`는 ACP params의 MCP server 정보를 세션 상태에 저장하지만 Pi로 직접 연결하지 않는다고 명시되어 있습니다.
- 즉, Pi의 자체 skill은 사용할 가능성이 높지만 ACP client에서 전달하는 MCP는 기대하면 안 됩니다.

MCP 전달까지 검증하려면 이 POC에 `--mcp-server` 같은 옵션을 추가하고 `agent.new_session(..., mcp_servers=[...])`에 값을 넣어야 합니다. 다만 agent별로 이를 실제로 사용하는지는 별도 테스트가 필요합니다.

## Permission 동작

기본값은 agent가 요청하는 permission option 중 `allow_once` 또는 `allow_always`를 자동 선택합니다.

```bash
uv run python main.py
```

자동 허용을 끄려면 아래 옵션을 사용합니다. 현재 스크립트는 interactive 선택 UI를 구현하지 않았으므로, 허용 옵션이 필요한 작업에서는 실패할 수 있습니다.

```bash
uv run python main.py --no-auto-allow
```

## 문제 해결

아래 에러가 발생하면 agent가 보낸 ACP JSON 메시지 한 줄이 현재 stdio buffer limit보다 크다는 뜻입니다.

```text
ValueError: Separator is not found, and chunk exceed the limit
```

기본값은 50MiB입니다. 더 크게 조정하려면:

```bash
uv run python main.py --agent codex --stdio-buffer-limit-mb 200
```

## 산출물 확인

실행이 끝나면 콘솔의 `[poc] artifacts:` 아래에 생성된 파일 목록이 표시됩니다.

직접 확인하려면:

```bash
find ~/tmp/todo-api-acp-test -maxdepth 3 -type f -print
```

생성된 Node.js API를 실행하는 방법은 agent가 만든 `package.json` 또는 README가 있다면 그 내용을 따릅니다. 일반적으로는 작업 디렉터리에서 다음 흐름으로 확인합니다.

```bash
cd ~/tmp/todo-api-acp-test
npm install
npm start
```

## 참고

- Python ACP SDK: `agent-client-protocol==0.9.0`
- Claude ACP agent: `@agentclientprotocol/claude-agent-acp`
- Codex ACP agent: `@zed-industries/codex-acp`
- 스크립트 엔트리포인트: `main.py`
