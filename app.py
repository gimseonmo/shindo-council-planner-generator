from __future__ import annotations

import io
import errno
import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from xml.sax.saxutils import escape


# 여기에 Gemini API 키 3개를 넣으면 됩니다.
# 예: GEMINI_API_KEYS = ["AIza...", "AIza...", "AIza..."]
# Vercel에 올릴 때는 코드에 직접 넣지 말고 환경 변수
# GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3를 사용하세요.
GEMINI_API_KEYS = [
    "",
    "",
    "",
]

# 필요하면 최신 Gemini 모델명으로 바꿔도 됩니다.
MODEL_NAME = "gemini-2.5-flash"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
PORT_RETRY_COUNT = 20


FORM_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>행사 기획서 생성기</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1d2433;
      --muted: #5c667a;
      --line: #d9dee8;
      --paper: #fbfbf8;
      --panel: #ffffff;
      --accent: #1f7a68;
      --accent-strong: #125347;
      --warn: #a3561a;
      --soft: #eef4f1;
      --blue: #2d5f9a;
      --rose: #a64263;
      font-family: "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(90deg, rgba(31, 122, 104, .08) 1px, transparent 1px),
        linear-gradient(rgba(45, 95, 154, .06) 1px, transparent 1px),
        var(--paper);
      background-size: 32px 32px;
      color: var(--ink);
    }

    .shell {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0;
    }

    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
      border-bottom: 2px solid var(--ink);
      padding-bottom: 14px;
    }

    h1 {
      margin: 0;
      font-size: clamp(26px, 4vw, 44px);
      line-height: 1.05;
      letter-spacing: 0;
    }

    .badge {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--muted);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 13px;
      white-space: nowrap;
    }

    main {
      display: grid;
      grid-template-columns: minmax(280px, 390px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }

    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 24px rgba(21, 31, 47, .08);
    }

    .form-area, .result-area { padding: 18px; }

    label {
      display: block;
      font-weight: 700;
      font-size: 14px;
      margin-bottom: 8px;
    }

    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      font: inherit;
      color: var(--ink);
      background: #fff;
      outline: none;
    }

    input:focus, textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(31, 122, 104, .14);
    }

    textarea {
      min-height: 174px;
      resize: vertical;
      line-height: 1.55;
    }

    .field { margin-bottom: 16px; }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    button {
      border: 1px solid transparent;
      border-radius: 6px;
      min-height: 42px;
      padding: 0 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform .12s ease, background .12s ease;
    }

    button:hover { transform: translateY(-1px); }
    button:disabled { cursor: wait; opacity: .65; transform: none; }

    .primary {
      background: var(--accent);
      color: #fff;
    }

    .primary:hover { background: var(--accent-strong); }

    .secondary {
      background: #fff;
      border-color: var(--line);
      color: var(--ink);
    }

    .secondary:hover { background: var(--soft); }

    .status {
      min-height: 22px;
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .status.error { color: var(--rose); }
    .status.ok { color: var(--accent-strong); }

    .result-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    h2 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }

    .tools {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: end;
    }

    #output {
      width: 100%;
      min-height: 560px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 18px;
      background: #fffdf8;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      line-height: 1.72;
      font-size: 15px;
      resize: vertical;
    }

    .placeholder {
      color: var(--muted);
    }

    #output:not(.placeholder) {
      color: var(--ink);
    }

    @media (max-width: 840px) {
      .shell { width: min(100vw - 20px, 680px); padding: 16px 0; }
      header { align-items: start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      #output { min-height: 420px; }
      .result-head { align-items: start; flex-direction: column; }
      .tools { justify-content: start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <h1>행사 기획서 생성기</h1>
      <div class="badge">Gemini API 키 __CONFIGURED_KEYS__/3개 설정됨</div>
    </header>

    <main>
      <section class="form-area" aria-label="입력">
        <form id="planForm">
          <div class="field">
            <label for="eventName">행사 이름</label>
            <input id="eventName" name="eventName" maxlength="80" required placeholder="예: 등굣길 응원 이벤트">
          </div>
          <div class="field">
            <label for="eventIntro">행사 소개</label>
            <textarea id="eventIntro" name="eventIntro" required placeholder="행사의 대상, 분위기, 진행 방식, 원하는 목적 등을 최대한 자세하게 적어주세요."></textarea>
          </div>
          <div class="actions">
            <button class="primary" id="generateBtn" type="submit">기획서 작성</button>
            <button class="secondary" id="clearBtn" type="button">초기화</button>
          </div>
          <p id="status" class="status"></p>
        </form>
      </section>

      <section class="result-area" aria-label="결과">
        <div class="result-head">
          <h2>생성 결과</h2>
          <div class="tools">
            <button class="secondary" id="copyBtn" type="button">복사</button>
            <button class="secondary" id="txtBtn" type="button">TXT 저장</button>
            <button class="secondary" id="docxBtn" type="button">DOCX 저장</button>
          </div>
        </div>
        <textarea id="output" class="placeholder" spellcheck="false" placeholder="기획서가 여기에 표시됩니다. 생성 후 이곳에서 바로 수정할 수 있습니다."></textarea>
      </section>
    </main>
  </div>

  <script>
    const form = document.getElementById("planForm");
    const statusEl = document.getElementById("status");
    const outputEl = document.getElementById("output");
    const generateBtn = document.getElementById("generateBtn");
    const clearBtn = document.getElementById("clearBtn");
    const copyBtn = document.getElementById("copyBtn");
    const txtBtn = document.getElementById("txtBtn");
    const docxBtn = document.getElementById("docxBtn");

    let lastName = "행사_기획서";

    function setStatus(message, type = "") {
      statusEl.textContent = message;
      statusEl.className = `status ${type}`.trim();
    }

    function setOutput(text) {
      outputEl.value = text || "";
      outputEl.classList.toggle("placeholder", !outputEl.value.trim());
    }

    function getOutputText() {
      return outputEl.value.trim();
    }

    outputEl.addEventListener("input", () => {
      outputEl.classList.toggle("placeholder", !outputEl.value.trim());
    });

    function safeFilename(name, ext) {
      const cleaned = (name || "행사_기획서").replace(/[\\\\/:*?"<>|]/g, "").trim();
      return `${cleaned || "행사_기획서"}.${ext}`;
    }

    function downloadBlob(blob, filename) {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(link.href);
      link.remove();
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const eventName = document.getElementById("eventName").value.trim();
      const eventIntro = document.getElementById("eventIntro").value.trim();

      if (!eventName || !eventIntro) {
        setStatus("행사 이름과 소개를 입력해주세요.", "error");
        return;
      }

      lastName = `${eventName}_기획서`;
      generateBtn.disabled = true;
      setStatus("작성 중입니다...");

      try {
        const response = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ eventName, eventIntro })
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "기획서 생성에 실패했습니다.");
        }
        setOutput(data.plan);
        setStatus(`완료되었습니다. 사용한 키: ${data.keySlot}번`, "ok");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        generateBtn.disabled = false;
      }
    });

    clearBtn.addEventListener("click", () => {
      form.reset();
      setOutput("");
      setStatus("");
    });

    copyBtn.addEventListener("click", async () => {
      const currentText = getOutputText();
      if (!currentText) return setStatus("복사할 기획서가 없습니다.", "error");
      await navigator.clipboard.writeText(currentText);
      setStatus("복사되었습니다.", "ok");
    });

    txtBtn.addEventListener("click", () => {
      const currentText = getOutputText();
      if (!currentText) return setStatus("저장할 기획서가 없습니다.", "error");
      downloadBlob(new Blob([currentText], { type: "text/plain;charset=utf-8" }), safeFilename(lastName, "txt"));
    });

    docxBtn.addEventListener("click", async () => {
      const currentText = getOutputText();
      if (!currentText) return setStatus("저장할 기획서가 없습니다.", "error");
      setStatus("DOCX를 준비 중입니다...");
      try {
        const response = await fetch("/api/docx", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: lastName, plan: currentText })
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "DOCX 저장에 실패했습니다.");
        }
        const blob = await response.blob();
        downloadBlob(blob, safeFilename(lastName, "docx"));
        setStatus("DOCX가 저장되었습니다.", "ok");
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  </script>
</body>
</html>
"""


SYSTEM_INSTRUCTION = """
너는 한국 고등학교 학생회 행사 기획서를 작성하는 보조자다.
사용자가 제공한 행사 이름과 행사 소개만 바탕으로, 아래 양식에 맞춰 자연스럽고 실무적으로 작성한다.

반드시 지킬 규칙:
- '활동 기간' 항목은 제목만 쓰고, 그 아래에는 아무 내용도 쓰지 않는다.
- '필요 예산' 항목도 제목만 쓰고, 그 아래에는 아무 내용도 쓰지 않는다.
- 예산, 가격, 구매 링크, 물품표, 물품 목록은 쓰지 않는다.
- Markdown 제목 기호(#)를 쓰지 않는다.
- 출력은 바로 제출 가능한 한국어 문서 형식으로만 작성한다.
- 학생회/부서 문맥에 맞춰 목적, 계획, 기대 효과를 구체적으로 작성한다.

양식:
2026 <행사 이름>

    • 활동 명칭
<행사 이름>

    • 활동 기간

    • 활동 목적
...

    • 필요 예산

    • 활동 계획
1. ...
2. ...
3. ...
4. ...
5. ...

    • 기대 효과
* ...
* ...
* ...
* ...

예시의 문체:
시험 이후 지친 학생들이 자신의 감정을 자연스럽게 표현하고 서로의 상태를 공감할 수 있는 참여형 활동을 통해 심리적 안정감과 긍정적인 분위기를 형성하고자 한다.
참여형 행사 운영을 통해 등교 시간 분위기를 밝고 활기차게 조성할 수 있다.
""".strip()


class KeyState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_index = 0

    def ordered_keys(self, keys: list[str]) -> list[tuple[int, str]]:
        with self._lock:
            start = self._start_index % len(keys)
        indexed = list(enumerate(keys))
        return indexed[start:] + indexed[:start]

    def mark_success(self, index: int) -> None:
        with self._lock:
            self._start_index = index

    def mark_failed(self, index: int, total: int) -> None:
        with self._lock:
            self._start_index = (index + 1) % total


KEY_STATE = KeyState()


def configured_keys() -> list[str]:
    keys = [key.strip() for key in GEMINI_API_KEYS if key.strip()]
    env_keys = [
        os.environ.get("GEMINI_API_KEY_1", "").strip(),
        os.environ.get("GEMINI_API_KEY_2", "").strip(),
        os.environ.get("GEMINI_API_KEY_3", "").strip(),
        os.environ.get("GEMINI_API_KEY", "").strip(),
    ]
    for key in env_keys:
        if key and key not in keys:
            keys.append(key)
    return keys


def build_prompt(event_name: str, event_intro: str) -> str:
    return f"""
행사 이름: {event_name}
행사 소개:
{event_intro}

위 내용을 바탕으로 기획서를 작성해줘.
다시 강조하지만 '활동 기간'과 '필요 예산'은 제목만 쓰고 내용은 비워둔다.
""".strip()


def call_gemini(event_name: str, event_intro: str) -> tuple[str, int]:
    keys = configured_keys()
    if not keys:
        raise RuntimeError("Gemini API 키를 설정해주세요. 로컬은 app.py의 GEMINI_API_KEYS, Vercel은 환경 변수 GEMINI_API_KEY_1~3을 사용합니다.")

    prompt = build_prompt(event_name, event_intro)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.65,
            "topP": 0.9,
            "maxOutputTokens": 2200,
        },
    }

    errors: list[str] = []
    for index, api_key in KEY_STATE.ordered_keys(keys):
        try:
            text = request_gemini(api_key, payload)
            KEY_STATE.mark_success(index)
            return clean_plan(text, event_name), index + 1
        except Exception as exc:
            KEY_STATE.mark_failed(index, len(keys))
            errors.append(f"{index + 1}번 키: {exc}")

    raise RuntimeError("모든 Gemini API 키로 생성에 실패했습니다. " + " / ".join(errors))


def request_gemini(api_key: str, payload: dict[str, Any]) -> str:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(MODEL_NAME)}:generateContent"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {short_error(detail)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"네트워크 오류: {exc.reason}") from exc

    candidates = data.get("candidates") or []
    parts = []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            if "text" in part:
                parts.append(part["text"])

    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("빈 응답을 받았습니다.")
    return text


def short_error(detail: str) -> str:
    try:
        parsed = json.loads(detail)
        message = parsed.get("error", {}).get("message")
        if message:
            return message[:240]
    except json.JSONDecodeError:
        pass
    return detail[:240]


def clean_plan(text: str, event_name: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"```(?:\w+)?", "", text).replace("```", "").strip()
    text = normalize_plan_sections(text)
    if "활동 명칭" not in text:
        text = f"2026 <{event_name}>\n\n    • 활동 명칭\n<{event_name}>\n\n{text}"
    return text.strip()


def normalize_plan_sections(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    skipping = False
    section_pattern = re.compile(r"^\s*(?:[-*•]\s*)?(활동\s*명칭|활동\s*기간|활동\s*목적|필요\s*예산|활동\s*계획|기대\s*효과)\s*(?:[:：].*)?$")

    for line in lines:
        match = section_pattern.match(line.strip())
        if match:
            section = re.sub(r"\s+", "", match.group(1))
            skipping = section in {"활동기간", "필요예산"}
            if section == "활동기간":
                result.append("    • 활동 기간")
                result.append("")
                continue
            if section == "필요예산":
                result.append("    • 필요 예산")
                result.append("")
                continue
            skipping = False
        if not skipping:
            result.append(line)

    cleaned = "\n".join(result)
    if "활동 기간" not in cleaned:
        cleaned = re.sub(r"(\n\s*•\s*활동\s*목적)", "\n\n    • 활동 기간\n\\1", cleaned, count=1)
    if "필요 예산" not in cleaned:
        cleaned = re.sub(r"(\n\s*•\s*활동\s*계획)", "\n\n    • 필요 예산\n\\1", cleaned, count=1)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def make_docx(title: str, plan: str) -> bytes:
    document_xml = build_document_xml(plan)
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escape(title)}</dc:title>
  <dc:creator>행사 기획서 생성기</dc:creator>
  <cp:lastModifiedBy>행사 기획서 생성기</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Python</Application>
</Properties>"""

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("docProps/core.xml", core)
        docx.writestr("docProps/app.xml", app)
    return output.getvalue()


def build_document_xml(plan: str) -> str:
    paragraphs = []
    for raw_line in plan.splitlines():
        line = raw_line.rstrip()
        if not line:
            paragraphs.append("<w:p/>")
            continue
        stripped = line.strip()
        is_title = stripped.startswith("2026 ")
        is_section = stripped.startswith("•") or re.match(r"^\s*[-*]\s+\S", line)
        style = ""
        if is_title:
            style = '<w:pPr><w:jc w:val="center"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:pPr>'
        elif is_section:
            style = '<w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:pPr>'
        text_size = "32" if is_title else "22"
        bold = "<w:b/>" if is_title or is_section else ""
        text_xml = escape(line)
        paragraphs.append(
            f'<w:p>{style}<w:r><w:rPr>{bold}<w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="{text_size}"/></w:rPr><w:t xml:space="preserve">{text_xml}</w:t></w:r></w:p>'
        )

    body = "".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def send_json(handler: BaseHTTPRequestHandler, status: int, data: dict[str, Any]) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            page = FORM_TEMPLATE.replace("__CONFIGURED_KEYS__", str(len(configured_keys()))).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        if self.path == "/health":
            send_json(self, HTTPStatus.OK, {"ok": True, "configuredKeys": len(configured_keys())})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            if self.path in ("/generate", "/api/generate"):
                data = read_json(self)
                event_name = str(data.get("eventName", "")).strip()
                event_intro = str(data.get("eventIntro", "")).strip()
                if not event_name or not event_intro:
                    send_json(self, HTTPStatus.BAD_REQUEST, {"error": "행사 이름과 소개를 입력해주세요."})
                    return
                if len(event_name) > 80 or len(event_intro) > 4000:
                    send_json(self, HTTPStatus.BAD_REQUEST, {"error": "입력 내용이 너무 깁니다."})
                    return
                plan, key_slot = call_gemini(event_name, event_intro)
                send_json(self, HTTPStatus.OK, {"plan": plan, "keySlot": key_slot})
                return

            if self.path in ("/docx", "/api/docx"):
                data = read_json(self)
                title = str(data.get("title", "행사_기획서")).strip()[:120]
                plan = str(data.get("plan", "")).strip()
                if not plan:
                    send_json(self, HTTPStatus.BAD_REQUEST, {"error": "기획서 내용이 없습니다."})
                    return
                docx = make_docx(title, plan)
                filename = urllib.parse.quote(f"{title or '행사_기획서'}.docx")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(len(docx)))
                self.end_headers()
                self.wfile.write(docx)
                return

            self.send_error(HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError:
            send_json(self, HTTPStatus.BAD_REQUEST, {"error": "요청 형식이 올바르지 않습니다."})
        except Exception as exc:
            send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} {format % args}")


def create_server() -> ReusableThreadingHTTPServer:
    for port in range(SERVER_PORT, SERVER_PORT + PORT_RETRY_COUNT):
        try:
            return ReusableThreadingHTTPServer((SERVER_HOST, port), RequestHandler)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
    raise OSError(f"{SERVER_PORT}~{SERVER_PORT + PORT_RETRY_COUNT - 1}번 포트가 모두 사용 중입니다.")


def main() -> None:
    server = create_server()
    host, port = server.server_address
    print(f"행사 기획서 생성기 실행 중: http://{host}:{port}")
    print("종료하려면 Ctrl+C를 누르세요.")
    server.serve_forever()


if __name__ == "__main__":
    main()
