# ACP Python Coding Agent POC

Agent Client Protocol(ACP)을 이용해 Python 클라이언트에서 coding agent를 실행하고, 목표 텍스트를 전달한 뒤 개발 산출물을 작업 디렉터리에 생성하는 POC입니다.

지원 agent:

- `claude-code`: `@agentclientprotocol/claude-agent-acp`
- `codex`: `@zed-industries/codex-acp`

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
