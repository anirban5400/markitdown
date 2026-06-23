import io
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from markitdown import MarkItDown


app = FastAPI(title="MarkItDown Web API")
converter = MarkItDown(enable_plugins=False)
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".html",
    ".htm",
    ".txt",
    ".csv",
    ".json",
    ".xml",
    ".epub",
    ".zip",
}

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MarkItDown Converter</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f5ef;
      --surface: #ffffff;
      --text: #1f2328;
      --muted: #687076;
      --line: #d8d2c4;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --danger: #b42318;
      --code: #111827;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    main {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 40px 0;
    }

    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.05;
      letter-spacing: 0;
    }

    .status {
      border: 1px solid var(--line);
      background: var(--surface);
      padding: 8px 12px;
      font-size: 14px;
      color: var(--muted);
      white-space: nowrap;
    }

    .layout {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 20px;
      align-items: stretch;
    }

    .panel {
      border: 1px solid var(--line);
      background: var(--surface);
      padding: 20px;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--muted);
    }

    input[type="file"] {
      width: 100%;
      min-height: 44px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      padding: 10px 12px;
      font: inherit;
    }

    .field {
      margin-bottom: 16px;
    }

    .actions,
    .result-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    button {
      min-height: 44px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      padding: 0 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      flex: 1;
    }

    button:hover {
      border-color: var(--accent-strong);
    }

    button.primary:hover {
      background: var(--accent-strong);
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.58;
    }

    button.success {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }

    .meta {
      min-height: 24px;
      margin-top: 14px;
      color: var(--muted);
      font-size: 14px;
    }

    .error {
      color: var(--danger);
      font-weight: 700;
    }

    .progress {
      margin-top: 16px;
    }

    .progress[hidden] {
      display: none;
    }

    .progress-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 13px;
    }

    .progress-track {
      position: relative;
      width: 100%;
      height: 10px;
      overflow: hidden;
      border: 1px solid var(--line);
      background: #ece7db;
    }

    .progress-fill {
      width: 0%;
      height: 100%;
      background: var(--accent);
      transition: width 120ms ease;
    }

    .progress-fill.indeterminate {
      position: absolute;
      width: 42%;
      animation: progress-slide 980ms ease-in-out infinite;
    }

    @keyframes progress-slide {
      0% {
        left: -42%;
      }

      100% {
        left: 100%;
      }
    }

    .toast {
      position: fixed;
      right: 20px;
      bottom: 20px;
      z-index: 10;
      max-width: min(360px, calc(100% - 40px));
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #fff;
      padding: 12px 14px;
      font-weight: 700;
      opacity: 0;
      transform: translateY(8px);
      pointer-events: none;
      transition: opacity 140ms ease, transform 140ms ease;
    }

    .toast.show {
      opacity: 1;
      transform: translateY(0);
    }

    .toast.error {
      border-color: var(--danger);
      background: var(--danger);
      color: #fff;
    }

    .result-panel {
      display: flex;
      min-height: 560px;
      flex-direction: column;
    }

    .result-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }

    .result-title {
      margin: 0;
      font-size: 16px;
    }

    textarea {
      width: 100%;
      flex: 1;
      min-height: 460px;
      resize: vertical;
      border: 1px solid var(--line);
      background: var(--code);
      color: #f9fafb;
      padding: 16px;
      font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }

    @media (max-width: 860px) {
      main {
        width: min(100% - 24px, 640px);
        padding: 24px 0;
      }

      header,
      .layout,
      .result-head {
        display: block;
      }

      .status {
        display: inline-block;
        margin-top: 14px;
      }

      .panel {
        margin-bottom: 16px;
      }

      .result-actions {
        margin-top: 12px;
      }

      .toast {
        right: 12px;
        bottom: 12px;
        max-width: calc(100% - 24px);
      }

      button,
      button.primary {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>MarkItDown Converter</h1>
      <div class="status" id="health">Checking service</div>
    </header>

    <section class="layout">
      <form class="panel" id="convertForm">
        <div class="field">
          <label for="file">File</label>
          <input id="file" name="file" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.html,.htm,.txt,.csv,.json,.xml,.epub,.zip" required>
        </div>

        <div class="actions">
          <button class="primary" id="convertButton" type="submit">Convert</button>
          <button id="clearButton" type="button">Clear</button>
        </div>

        <div class="meta" id="message"></div>
        <div class="progress" id="progress" hidden>
          <div class="progress-row">
            <span id="progressLabel">Waiting</span>
            <span id="progressPercent">0%</span>
          </div>
          <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-label="Conversion progress">
            <div class="progress-fill" id="progressFill"></div>
          </div>
        </div>
      </form>

      <section class="panel result-panel">
        <div class="result-head">
          <h2 class="result-title">Markdown</h2>
          <div class="result-actions">
            <button id="copyButton" type="button" disabled>Copy</button>
            <button id="downloadButton" type="button" disabled>Download</button>
          </div>
        </div>
        <textarea id="output" spellcheck="false" readonly></textarea>
      </section>
    </section>
  </main>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>

  <script>
    const form = document.getElementById("convertForm");
    const fileInput = document.getElementById("file");
    const output = document.getElementById("output");
    const message = document.getElementById("message");
    const health = document.getElementById("health");
    const convertButton = document.getElementById("convertButton");
    const clearButton = document.getElementById("clearButton");
    const copyButton = document.getElementById("copyButton");
    const downloadButton = document.getElementById("downloadButton");
    const toast = document.getElementById("toast");
    const progress = document.getElementById("progress");
    const progressLabel = document.getElementById("progressLabel");
    const progressPercent = document.getElementById("progressPercent");
    const progressTrack = progress.querySelector(".progress-track");
    const progressFill = document.getElementById("progressFill");
    const allowedExtensions = new Set([
      ".pdf",
      ".doc",
      ".docx",
      ".ppt",
      ".pptx",
      ".xls",
      ".xlsx",
      ".html",
      ".htm",
      ".txt",
      ".csv",
      ".json",
      ".xml",
      ".epub",
      ".zip",
    ]);
    let toastTimer = null;

    function setMessage(text, isError = false) {
      message.textContent = text;
      message.className = isError ? "meta error" : "meta";
    }

    function showToast(text, isError = false) {
      window.clearTimeout(toastTimer);
      toast.textContent = text;
      toast.className = isError ? "toast error show" : "toast show";
      toastTimer = window.setTimeout(() => {
        toast.className = isError ? "toast error" : "toast";
      }, 2200);
    }

    function setResult(text) {
      output.value = text;
      const hasText = text.length > 0;
      copyButton.disabled = !hasText;
      downloadButton.disabled = !hasText;
      copyButton.textContent = "Copy";
      copyButton.classList.remove("success");
    }

    function formatBytes(bytes) {
      if (bytes < 1024) {
        return `${bytes} B`;
      }

      const units = ["KB", "MB", "GB"];
      let size = bytes / 1024;
      let unitIndex = 0;

      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
      }

      return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unitIndex]}`;
    }

    function getExtension(filename) {
      const dotIndex = filename.lastIndexOf(".");
      return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : "";
    }

    function isAllowedFile(file) {
      return allowedExtensions.has(getExtension(file.name));
    }

    function resetProgress() {
      progress.hidden = true;
      progressLabel.textContent = "Waiting";
      progressPercent.textContent = "0%";
      progressFill.className = "progress-fill";
      progressFill.style.width = "0%";
      progressTrack.removeAttribute("aria-valuenow");
    }

    function setProgress(label, percent = null) {
      progress.hidden = false;
      progressLabel.textContent = label;

      if (percent === null) {
        progressPercent.textContent = "";
        progressFill.className = "progress-fill indeterminate";
        progressFill.style.width = "";
        progressTrack.removeAttribute("aria-valuenow");
        return;
      }

      const normalized = Math.max(0, Math.min(100, percent));
      progressPercent.textContent = `${Math.round(normalized)}%`;
      progressFill.className = "progress-fill";
      progressFill.style.width = `${normalized}%`;
      progressTrack.setAttribute("aria-valuenow", String(Math.round(normalized)));
    }

    function parseErrorMessage(text) {
      try {
        const payload = JSON.parse(text);
        return payload.detail || text || "Conversion failed.";
      } catch {
        return text || "Conversion failed.";
      }
    }

    function convertFile(file) {
      return new Promise((resolve, reject) => {
        const body = new FormData();
        body.append("file", file);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/convert");

        xhr.upload.addEventListener("progress", (event) => {
          if (!event.lengthComputable) {
            setProgress("Uploading...", null);
            return;
          }

          const percent = (event.loaded / event.total) * 100;
          setProgress(
            `Uploading ${formatBytes(event.loaded)} / ${formatBytes(event.total)}`,
            percent,
          );
        });

        xhr.upload.addEventListener("load", () => {
          setProgress("Processing document...", null);
          setMessage("Processing document...");
        });

        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(xhr.responseText);
            return;
          }

          reject(new Error(parseErrorMessage(xhr.responseText)));
        });

        xhr.addEventListener("error", () => {
          reject(new Error("Upload failed. Check your connection and try again."));
        });

        xhr.addEventListener("abort", () => {
          reject(new Error("Upload was cancelled."));
        });

        xhr.send(body);
      });
    }

    async function copyMarkdown() {
      if (!output.value) {
        throw new Error("Nothing to copy.");
      }

      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(output.value);
          return;
        } catch {
          // Fall back to selection-based copy below.
        }
      }

      output.focus();
      output.select();
      output.setSelectionRange(0, output.value.length);

      if (!document.execCommand("copy")) {
        throw new Error("Copy failed. Select the Markdown text and copy it manually.");
      }

      window.getSelection().removeAllRanges();
      output.blur();
    }

    async function checkHealth() {
      try {
        const response = await fetch("/health");
        health.textContent = response.ok ? "Service online" : "Service unavailable";
      } catch {
        health.textContent = "Service unavailable";
      }
    }

    fileInput.addEventListener("change", () => {
      if (!fileInput.files.length) {
        return;
      }

      if (!isAllowedFile(fileInput.files[0])) {
        fileInput.value = "";
        resetProgress();
        setMessage("Select a supported document file.", true);
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      if (!fileInput.files.length) {
        setMessage("Select a file first.", true);
        return;
      }

      const file = fileInput.files[0];

      if (!isAllowedFile(file)) {
        fileInput.value = "";
        resetProgress();
        setMessage("Select a supported document file.", true);
        return;
      }

      convertButton.disabled = true;
      setMessage("Preparing upload...");
      setResult("");
      setProgress(`Uploading 0 B / ${formatBytes(file.size)}`, 0);

      try {
        const text = await convertFile(file);
        setResult(text);
        setProgress("Processing complete.", 100);
        setMessage("Conversion complete.");
      } catch (error) {
        setMessage(error.message, true);
      } finally {
        convertButton.disabled = false;
      }
    });

    clearButton.addEventListener("click", () => {
      fileInput.value = "";
      setResult("");
      setMessage("");
      resetProgress();
    });

    copyButton.addEventListener("click", async () => {
      try {
        await copyMarkdown();
        copyButton.textContent = "✓ Copied";
        copyButton.classList.add("success");
        setMessage("Copied to clipboard.");
        showToast("Copied to clipboard");

        window.setTimeout(() => {
          copyButton.textContent = "Copy";
          copyButton.classList.remove("success");
        }, 1800);
      } catch (error) {
        setMessage(error.message, true);
        showToast(error.message, true);
      }
    });

    downloadButton.addEventListener("click", () => {
      const blob = new Blob([output.value], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "converted.md";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    });

    checkHealth();
  </script>
</body>
</html>
"""


@app.middleware("http")
async def no_store_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


def max_upload_bytes() -> int:
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "50"))
    return max_mb * 1024 * 1024


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/convert", response_class=PlainTextResponse)
async def convert(
    request: Request,
    file: UploadFile = File(...),
) -> str:
    content_length = request.headers.get("content-length")
    limit = max_upload_bytes()

    if content_length and int(content_length) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload exceeds {limit} bytes",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload a supported document or data file.",
        )

    written = 0
    buffer = io.BytesIO()

    while chunk := await file.read(1024 * 1024):
        written += len(chunk)
        if written > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Upload exceeds {limit} bytes",
            )
        buffer.write(chunk)

    buffer.seek(0)
    result = converter.convert_stream(buffer, file_extension=suffix or None)
    return result.text_content
