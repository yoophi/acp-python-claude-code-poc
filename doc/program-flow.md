# Program Flow

이 문서는 `main.py`의 동작 방식을 Mermaid graph로 정리합니다.

POC의 핵심 목적은 Python ACP client가 coding agent ACP adapter를 subprocess로 실행하고, 목표 텍스트를 ACP `session/prompt`로 전달한 뒤, agent의 응답과 개발 산출물을 확인하는 것입니다.

## 전체 구조

```mermaid
flowchart TD
    User["User runs\nuv run python main.py"] --> CLI["argparse\nparse CLI options"]
    CLI --> Defaults["Apply defaults\nagent=claude-code\ngoal=todo REST API\ncwd=~/tmp/todo-api-acp-test"]
    Defaults --> Workspace["Create/resolve workspace directory"]
    Workspace --> Client["Create PocClient\nworkspace + auto_allow"]
    Client --> AgentSelect["Resolve agent command\nAGENT_COMMANDS or --agent-command"]
    AgentSelect --> Spawn["spawn_agent_process\nACP adapter subprocess over stdio"]
    Spawn --> Init["agent.initialize\nprotocol version + client capabilities"]
    Init --> NewSession["agent.new_session\ncwd + mcp_servers=[]"]
    NewSession --> Prompt["agent.prompt\nsend goal text block"]
    Prompt --> Updates["Receive callbacks\nsession_update / permissions / fs / terminal"]
    Updates --> PromptDone["PromptResponse\nstop_reason"]
    PromptDone --> Close["agent.close_session"]
    Close --> CloseSupported{"session/close\nsupported?"}
    CloseSupported -->|"yes"| Artifacts["List generated artifact files"]
    CloseSupported -->|"no: RequestError -32601"| CloseWarn["Print warning\ncontinue shutdown"]
    CloseWarn --> Artifacts
    Artifacts --> Exit["Exit with status 0\nunless agent process failed"]
```

## CLI Option Flow

```mermaid
flowchart LR
    Args["CLI arguments"] --> Goal["--goal\nDefault Korean todo API request"]
    Args --> Cwd["--cwd\nDefault ~/tmp/todo-api-acp-test"]
    Args --> Agent["--agent\nclaude-code | codex | opencode | pi"]
    Args --> AgentCommand["--agent-command\nOverride command"]
    Args --> Buffer["--stdio-buffer-limit-mb\nDefault 50"]
    Args --> AutoAllow["--no-auto-allow\nDisable automatic allow"]

    Agent --> Commands["AGENT_COMMANDS map"]
    AgentCommand --> Resolve{"agent-command\nprovided?"}
    Commands --> Resolve
    Resolve -->|"yes"| UseOverride["Use --agent-command"]
    Resolve -->|"no"| UseDefault["Use command from AGENT_COMMANDS"]

    UseOverride --> Shlex["shlex.split command"]
    UseDefault --> Shlex
    Shlex --> Spawn["Spawn ACP adapter subprocess"]
```

현재 agent 기본 명령:

| Agent | Command |
| --- | --- |
| `claude-code` | `npx -y @agentclientprotocol/claude-agent-acp` |
| `codex` | `npx -y @zed-industries/codex-acp` |
| `opencode` | `npx -y opencode-ai acp` |
| `pi` | `npx -y pi-acp` |

## ACP Sequence

```mermaid
sequenceDiagram
    actor User
    participant Script as main.py
    participant Client as PocClient
    participant ACP as ACP SDK Connection
    participant Agent as ACP Agent Subprocess
    participant Workspace as Workspace Files

    User->>Script: uv run python main.py --agent ...
    Script->>Script: Parse args and create workspace
    Script->>Client: PocClient(workspace, auto_allow)
    Script->>ACP: spawn_agent_process(Client, command, cwd, limit)
    ACP->>Agent: Start subprocess using stdio

    Script->>Agent: initialize(protocolVersion, capabilities)
    Agent-->>Script: InitializeResponse(agentInfo)

    Script->>Agent: session/new(cwd, mcpServers=[])
    Agent-->>Script: NewSessionResponse(sessionId)

    Script->>Agent: session/prompt(goal text)

    loop During agent work
        Agent-->>Client: session/update
        Client-->>User: Print agent message, thought, plan, tool, usage
        Agent-->>Client: request_permission(options, toolCall)
        Client-->>Agent: selected allow option
        Agent-->>Client: fs/read_text_file or fs/write_text_file
        Client-->>Workspace: Read or write path inside workspace
        Agent-->>Client: terminal/create, output, wait, kill, release
        Client-->>Workspace: Run command in workspace
    end

    Agent-->>Script: PromptResponse(stopReason)
    Script->>Agent: session/close(sessionId)
    alt session/close supported
        Agent-->>Script: CloseSessionResponse
    else Method not found
        Agent-->>Script: RequestError -32601
        Script-->>User: Print warning and continue
    end
    Script->>Workspace: rglob files
    Script-->>User: Print artifact list
```

## `PocClient` Callback Router

`PocClient` implements the client-side ACP callbacks that an agent may call while processing a prompt.

```mermaid
flowchart TD
    AgentEvent["ACP agent request/notification"] --> Method{"Callback method"}

    Method -->|"request_permission"| Permission["Print permission request\nselect allow_once/allow_always"]
    Permission --> PermissionResponse["Return RequestPermissionResponse"]

    Method -->|"session_update"| UpdateKind{"session_update kind"}
    UpdateKind -->|"agent_message_chunk"| Msg["Print text in blue\nstreaming, no extra newline"]
    UpdateKind -->|"agent_thought_chunk"| Thought["Print thought text in blue\nstreaming, no extra newline"]
    UpdateKind -->|"plan"| Plan["Print plan entries"]
    UpdateKind -->|"tool_call / tool_call_update"| Tool["Normalize and dedupe tool output"]
    UpdateKind -->|"usage_update"| Usage["Print context usage"]
    UpdateKind -->|"other"| Other["Print update kind"]

    Method -->|"read_text_file"| Read["Resolve path inside workspace\nread UTF-8 text"]
    Read --> ReadResponse["Return ReadTextFileResponse"]

    Method -->|"write_text_file"| Write["Resolve path inside workspace\ncreate parent dirs\nwrite UTF-8 text"]
    Write --> WriteResponse["Return WriteTextFileResponse"]

    Method -->|"terminal/create"| TerminalCreate["Run subprocess in workspace\ncapture stdout+stderr"]
    TerminalCreate --> TerminalId["Return terminal_id"]

    Method -->|"terminal/output"| TerminalOutput["Return captured output\nplus exit status if done"]
    Method -->|"terminal/wait_for_exit"| TerminalWait["Wait process\nreturn exit code"]
    Method -->|"terminal/kill"| TerminalKill["SIGTERM process if running"]
    Method -->|"terminal/release"| TerminalRelease["Drop terminal state"]
```

## Tool Update Output Policy

The tool update output policy exists mainly to keep `pi-acp` output readable.

```mermaid
flowchart TD
    ToolUpdate["tool_call or tool_call_update"] --> Extract["Extract status, title, tool_call_id, locations"]
    Extract --> CleanTitle["Clean title\nNone or 'None' -> empty"]
    CleanTitle --> PendingNoTitle{"status is pending\nand no title\nand tool_call_id?"}

    PendingNoTitle -->|"yes"| CachePath["Cache latest locations\nby tool_call_id"]
    CachePath --> Skip["Skip printing"]

    PendingNoTitle -->|"no"| HasLocations{"locations present?"}
    HasLocations -->|"no + tool_call_id"| RestorePath["Restore cached pending locations"]
    HasLocations -->|"yes"| Signature
    RestorePath --> Signature["Build signature\nstatus + label + locations"]

    Signature --> Completed{"status completed\nor failed?"}
    Completed -->|"yes"| ClearCache["Remove pending path cache"]
    Completed -->|"no"| Dedupe
    ClearCache --> Dedupe{"Same as last printed\nsignature?"}

    Dedupe -->|"yes"| Skip2["Skip duplicate"]
    Dedupe -->|"no"| Print["Print [tool] line\nand locations"]
```

This avoids output such as:

```text
[tool] pending None
[tool] pending None
```

It also hides incremental path fragments like:

```text
src/in
src/infrastructure
src/infrastructure/persistence/JsonTodoRepository.js
```

and waits for a meaningful state transition before printing.

## Filesystem Safety

All ACP filesystem callbacks are constrained to the configured workspace.

```mermaid
flowchart TD
    PathInput["Agent-provided path"] --> Expand["Expand ~"]
    Expand --> Absolute{"Absolute path?"}
    Absolute -->|"no"| Join["Join with workspace"]
    Absolute -->|"yes"| Resolve
    Join --> Resolve["Path.resolve()"]
    Resolve --> Inside{"Inside workspace?"}
    Inside -->|"yes"| Allow["Allow read/write"]
    Inside -->|"no"| Deny["Raise PermissionError"]
```

This prevents an agent from using the POC filesystem callbacks to read or write outside the selected workspace.

## Terminal Handling

```mermaid
stateDiagram-v2
    [*] --> Created: terminal/create
    Created --> Running: subprocess starts
    Running --> Capturing: background reader captures stdout/stderr
    Capturing --> Running: terminal/output returns current buffer
    Running --> Exited: process exits
    Running --> Terminated: terminal/kill sends SIGTERM
    Terminated --> Exited
    Exited --> Released: terminal/release
    Released --> [*]
```

Terminal output is held in memory with a per-terminal byte limit. If the buffer grows beyond the limit, the oldest bytes are dropped.

## Error Handling

```mermaid
flowchart TD
    PromptDone["PromptResponse received"] --> Close["Call session/close"]
    Close --> Result{"Result"}
    Result -->|"success"| Continue["Continue"]
    Result -->|"RequestError code -32601"| Warn["Print session/close unsupported warning"]
    Result -->|"other RequestError"| Raise["Re-raise error"]
    Warn --> Continue
    Continue --> ProcessCode{"Agent process returncode set\nand non-zero?"}
    ProcessCode -->|"yes"| ReturnCode["Return agent process code"]
    ProcessCode -->|"no"| Artifacts["Print artifact list"]
```

The `session/close` fallback exists because some ACP adapters, notably some OpenCode ACP versions, may not implement `session/close`.

## Color Policy

```mermaid
flowchart LR
    Output["Console output"] --> FromAgent{"From agent / ACP callback?"}
    FromAgent -->|"yes"| Blue["Print blue\nANSI 34"]
    FromAgent -->|"no"| Default["Print default color"]
```

Agent messages, thoughts, plans, tool updates, permission requests, extension notifications, and extension method calls are printed in blue. POC control logs such as `[poc] workspace`, terminal lifecycle logs, filesystem write logs, and artifact lists use the default terminal color.
