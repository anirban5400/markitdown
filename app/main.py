import asyncio
import io
import ipaddress
import os
import socket
import time
import uuid
from pathlib import Path
from tempfile import gettempdir
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from markitdown import MarkItDown
from pydantic import BaseModel, HttpUrl


app = FastAPI(title="MarkItDown Web API")
converter = MarkItDown(enable_plugins=False)
TEMP_DOWNLOAD_DIR = Path(gettempdir()) / "markitdown-downloads"
downloaded_files: dict[str, Path] = {}
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


class ConvertUrlRequest(BaseModel):
    url: HttpUrl


class ConvertUrlResponse(BaseModel):
    markdown: str
    cleanup_id: str

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

    input[type="file"],
    input[type="url"] {
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

    .divider {
      height: 1px;
      margin: 20px 0;
      background: var(--line);
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
      <section class="panel">
        <form id="convertForm">
          <div class="field">
            <label for="file">File</label>
            <input id="file" name="file" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.html,.htm,.txt,.csv,.json,.xml,.epub,.zip" required>
          </div>

          <div class="actions">
            <button class="primary" id="convertButton" type="submit">Convert</button>
            <button id="clearButton" type="button">Clear</button>
          </div>
        </form>

        <div class="divider"></div>

        <form id="urlForm">
          <div class="field">
            <label for="pdfUrl">PDF URL</label>
            <input id="pdfUrl" name="url" type="url" placeholder="https://example.com/file.pdf">
          </div>

          <div class="actions">
            <button class="primary" id="urlButton" type="submit">Download & Convert</button>
          </div>
        </form>

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
      </section>

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
    const urlForm = document.getElementById("urlForm");
    const pdfUrlInput = document.getElementById("pdfUrl");
    const output = document.getElementById("output");
    const message = document.getElementById("message");
    const health = document.getElementById("health");
    const convertButton = document.getElementById("convertButton");
    const urlButton = document.getElementById("urlButton");
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
    let currentCleanupId = null;

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
        if (typeof payload.detail === "string") {
          return payload.detail;
        }
        return text || "Conversion failed.";
      } catch {
        return text || "Conversion failed.";
      }
    }

    async function cleanupDownloadedFile() {
      if (!currentCleanupId) {
        return;
      }

      const cleanupId = currentCleanupId;
      currentCleanupId = null;

      try {
        await fetch(`/cleanup/${encodeURIComponent(cleanupId)}`, { method: "DELETE" });
      } catch {
        // The server also expires abandoned files, so cleanup failure should not block the UI.
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

    async function convertUrl(url) {
      const response = await fetch("/convert-url", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      const text = await response.text();

      if (!response.ok) {
        throw new Error(parseErrorMessage(text));
      }

      try {
        return JSON.parse(text);
      } catch {
        throw new Error("URL conversion returned an invalid response.");
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
      urlButton.disabled = true;
      setMessage("Preparing upload...");
      setResult("");
      setProgress(`Uploading 0 B / ${formatBytes(file.size)}`, 0);

      try {
        await cleanupDownloadedFile();
        const text = await convertFile(file);
        setResult(text);
        setProgress("Processing complete.", 100);
        setMessage("Conversion complete.");
      } catch (error) {
        setMessage(error.message, true);
      } finally {
        convertButton.disabled = false;
        urlButton.disabled = false;
      }
    });

    urlForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const url = pdfUrlInput.value.trim();

      if (!url) {
        setMessage("Paste a direct PDF URL first.", true);
        return;
      }

      convertButton.disabled = true;
      urlButton.disabled = true;
      setMessage("Downloading PDF...");
      setResult("");
      setProgress("Downloading PDF...", null);

      try {
        await cleanupDownloadedFile();
        const result = await convertUrl(url);
        currentCleanupId = result.cleanup_id;
        setResult(result.markdown || "");
        setProgress("Processing complete.", 100);
        setMessage("Conversion complete.");
      } catch (error) {
        setMessage(error.message, true);
        resetProgress();
      } finally {
        convertButton.disabled = false;
        urlButton.disabled = false;
      }
    });

    clearButton.addEventListener("click", async () => {
      clearButton.disabled = true;
      await cleanupDownloadedFile();
      fileInput.value = "";
      pdfUrlInput.value = "";
      setResult("");
      setMessage("");
      resetProgress();
      clearButton.disabled = false;
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


def temp_file_ttl_seconds() -> int:
    return int(os.getenv("TEMP_FILE_TTL_SECONDS", "1800"))


def ensure_temp_download_dir() -> None:
    TEMP_DOWNLOAD_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def is_public_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not resolve the PDF URL host.",
        ) from None

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False

    return True


async def validate_public_pdf_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paste a valid HTTP or HTTPS PDF URL.",
        )

    is_public = await asyncio.to_thread(is_public_host, parsed.hostname)
    if not is_public:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF URL host must be publicly reachable.",
        )


def looks_like_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def looks_like_pdf_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return "application/pdf" in content_type or looks_like_pdf_url(str(response.url))


def delete_downloaded_file(cleanup_id: str) -> None:
    path = downloaded_files.pop(cleanup_id, None)
    if path and path.exists():
        path.unlink(missing_ok=True)


async def delete_after_ttl(cleanup_id: str, created_at: float) -> None:
    await asyncio.sleep(temp_file_ttl_seconds())
    path = downloaded_files.get(cleanup_id)
    if path and time.time() >= created_at + temp_file_ttl_seconds():
        delete_downloaded_file(cleanup_id)


async def download_pdf(url: str, cleanup_id: str) -> Path:
    ensure_temp_download_dir()
    target = TEMP_DOWNLOAD_DIR / f"{cleanup_id}.pdf"
    limit = max_upload_bytes()
    written = 0

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    current_url = url

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            headers={"User-Agent": "MarkItDown-Web-API/1.0"},
        ) as client:
            for _ in range(6):
                await validate_public_pdf_url(current_url)

                async with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="PDF URL returned a redirect without a target.",
                            )
                        current_url = urljoin(str(response.url), location)
                        continue

                    if response.status_code >= 400:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"PDF download failed with HTTP {response.status_code}.",
                        )

                    if not looks_like_pdf_response(response):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="URL did not return a PDF response.",
                        )

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > limit:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Downloaded PDF exceeds {limit} bytes",
                        )

                    with target.open("wb") as handle:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            written += len(chunk)
                            if written > limit:
                                raise HTTPException(
                                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                    detail=f"Downloaded PDF exceeds {limit} bytes",
                                )
                            handle.write(chunk)
                    break
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF URL redirected too many times.",
                )
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except httpx.RequestError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not download PDF: {exc.__class__.__name__}",
        ) from exc

    if written == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Downloaded PDF was empty.",
        )

    return target


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


@app.post("/convert-url", response_model=ConvertUrlResponse)
async def convert_url(payload: ConvertUrlRequest) -> ConvertUrlResponse:
    url = str(payload.url)
    cleanup_id = uuid.uuid4().hex
    created_at = time.time()
    path: Path | None = None

    await validate_public_pdf_url(url)

    try:
        path = await download_pdf(url, cleanup_id)

        with path.open("rb") as buffer:
            result = converter.convert_stream(buffer, file_extension=".pdf")

        downloaded_files[cleanup_id] = path
        asyncio.create_task(delete_after_ttl(cleanup_id, created_at))
        return ConvertUrlResponse(markdown=result.text_content, cleanup_id=cleanup_id)
    except Exception:
        if path:
            path.unlink(missing_ok=True)
        raise


@app.delete("/cleanup/{cleanup_id}")
def cleanup(cleanup_id: str) -> dict[str, bool]:
    delete_downloaded_file(cleanup_id)
    return {"deleted": True}
