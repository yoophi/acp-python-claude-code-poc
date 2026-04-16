# Pi ACP Tool Output Noise

이 문서는 `--agent pi` 실행 중 관찰된 tool update 출력 노이즈와 이를 완화하기 위해 POC에 반영한 처리 방식을 정리합니다.

## 증상 1: title 없는 tool update가 반복 출력됨

`pi-acp` 실행 중 아래와 같은 로그가 반복적으로 출력되는 경우가 있었습니다.

```text
[tool] pending None

[tool] pending None

[tool] pending None
```

path가 함께 오는 경우에도 같은 정보가 여러 번 반복됐습니다.

```text
[tool] pending None
  path: /Users/yoophi/tmp/my-acp-test-pi/README.md

[tool] pending None
  path: /Users/yoophi/tmp/my-acp-test-pi/README.md

[tool] in_progress None
  path: /Users/yoophi/tmp/my-acp-test-pi/README.md
```

## 증상 2: path가 점진적으로 늘어나며 반복 출력됨

같은 `tool_call_id`에 대해 path 문자열이 완성되기 전 중간 상태가 계속 출력되는 경우도 있었습니다.

```text
[tool] pending id=call_xxx
  path: /Users/yoophi/tmp/my-acp-test-pi/src/in

[tool] pending id=call_xxx
  path: /Users/yoophi/tmp/my-acp-test-pi/src/infrastructure

[tool] pending id=call_xxx
  path: /Users/yoophi/tmp/my-acp-test-pi/src/infrastructure/persistence/JsonTodoRepository.js

[tool] in_progress id=call_xxx
  path: /Users/yoophi/tmp/my-acp-test-pi/src/infrastructure/persistence/JsonTodoRepository.js

[tool] completed id=call_xxx
```

## 원인

ACP `tool_call` / `tool_call_update` 이벤트는 agent adapter가 자유롭게 여러 번 보낼 수 있습니다. `pi-acp`는 일부 tool 정보를 한 번에 완성해서 보내기보다 다음과 같이 증분 업데이트 형태로 보내는 경우가 있습니다.

- `title`이 없거나 `None`에 해당하는 값으로 전달됨
- 같은 `status`와 같은 path가 반복 전달됨
- 같은 `tool_call_id`에서 `pending` 상태로 path가 점진적으로 완성됨
- `completed` 상태에서는 path가 생략되는 경우가 있음

기존 POC는 모든 tool update를 그대로 출력했기 때문에, 사용자에게 의미 있는 상태 변화보다 중간 이벤트가 과도하게 노출됐습니다.

## 해결 방법

`main.py`의 `PocClient.session_update()`에서 tool update 출력 정책을 조정했습니다.

### 1. `None` title 숨김

`title`이 실제 `None`이거나 문자열 `"None"`이면 빈 문자열로 정규화합니다.

```python
def _clean_tool_title(self, title: Any) -> str:
    if title is None:
        return ""
    text = str(title).strip()
    return "" if text.lower() == "none" else text
```

이로 인해 아래처럼 출력되지 않습니다.

```text
[tool] pending None
```

대신 title이 없으면 가능한 경우 `tool_call_id`를 label로 사용합니다.

```text
[tool] in_progress id=call_xxx
```

### 2. 완전히 같은 tool update 중복 제거

최근 출력한 tool update의 `(status, label, locations)` 조합을 저장하고, 동일한 조합이 다시 오면 출력하지 않습니다.

```python
self._last_tool_signature: tuple[str, str, tuple[str, ...]] | None = None
```

이로 인해 같은 path와 같은 status의 반복 출력이 줄어듭니다.

### 3. title 없는 `pending` path 증분 업데이트 숨김

`status == "pending"`이고 title이 없으며 `tool_call_id`가 있는 경우, 해당 이벤트는 출력하지 않고 마지막 path만 저장합니다.

```python
if status == "pending" and not title and tool_call_id:
    self._pending_tool_locations[tool_call_id] = locations
    return
```

이로 인해 path가 `/src/in`, `/src/infrastructure`, `/src/infrastructure/persistence/...`처럼 점진적으로 늘어나는 중간 로그가 사용자에게 노출되지 않습니다.

### 4. 상태 변화 시 마지막 path 보완

`in_progress`, `completed`, `failed` 같은 후속 상태에서 locations가 비어 있으면, 같은 `tool_call_id`의 마지막 pending path를 가져와 출력합니다.

```python
if not locations and tool_call_id:
    locations = self._pending_tool_locations.get(tool_call_id, locations)
```

이렇게 하면 `completed` 이벤트가 path를 생략하더라도 사용자에게 마지막으로 확인된 대상 파일을 보여줄 수 있습니다.

### 5. 완료/실패 시 pending path 캐시 정리

tool call이 끝난 상태에서는 해당 `tool_call_id`의 pending path 캐시를 제거합니다.

```python
if status in {"completed", "failed"} and tool_call_id:
    self._pending_tool_locations.pop(tool_call_id, None)
```

## 결과

기존에는 아래처럼 중간 pending 로그가 많이 출력됐습니다.

```text
[tool] pending id=call_xxx
  path: .../src/in

[tool] pending id=call_xxx
  path: .../src/infrastructure

[tool] pending id=call_xxx
  path: .../src/infrastructure/persistence/JsonTodoRepository.js
```

변경 후에는 title 없는 pending 증분 로그를 숨기고, 의미 있는 상태 변화 위주로 출력합니다.

```text
[tool] in_progress id=call_xxx
  path: .../src/infrastructure/persistence/JsonTodoRepository.js

[tool] completed id=call_xxx
  path: .../src/infrastructure/persistence/JsonTodoRepository.js
```

## 남은 한계

- title이 있는 `pending` 이벤트는 숨기지 않습니다. title이 있다면 사용자에게 의미 있는 tool 시작 정보일 가능성이 있기 때문입니다.
- 같은 `tool_call_id`라도 agent가 실제로 다른 path를 대상으로 의미 있는 pending 이벤트를 여러 번 보내는 경우, 현재 정책은 title 없는 pending 이벤트를 숨깁니다.
- 더 정교한 UI가 필요하면 tool update를 실시간으로 줄 단위 출력하지 말고, `tool_call_id`별 상태 테이블을 갱신하는 방식이 더 적합합니다.
