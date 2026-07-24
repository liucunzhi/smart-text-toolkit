"""
Smart Text Toolkit API
FastAPI-based API service for text processing utilities.
Designed for deployment on Render (free tier) and monetization via RapidAPI.
"""
import re
import json
import html as html_module
import os
import threading
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import time
import hashlib
import csv
import io
import base64
import qrcode as qrcode_lib

app = FastAPI(
    title="Smart Text Toolkit API",
    description="All-in-one text & media utility API: Markdown/HTML conversion, JSON formatting, code highlighting, QR codes, CSV/JSON conversion, image Base64 encoding, text diff, and URL shortening.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory rate limiter
import threading
rate_limits = {}
rate_limits_lock = threading.Lock()

def check_rate_limit(client_ip: str, max_rpm: int = 60):
    now = time.time()
    with rate_limits_lock:
        if client_ip in rate_limits:
            window_start, count = rate_limits[client_ip]
            if now - window_start > 60:
                rate_limits[client_ip] = (now, 1)
                return True
            if count >= max_rpm:
                return False
            rate_limits[client_ip] = (window_start, count + 1)
            return True
        rate_limits[client_ip] = (now, 1)
        # Periodic cleanup: remove entries older than 120s
        if len(rate_limits) > 10000:
            stale = [ip for ip, (ts, _) in rate_limits.items() if now - ts > 120]
            for ip in stale:
                del rate_limits[ip]
        return True

# Models
class MarkdownRequest(BaseModel):
    markdown: str = Field(..., min_length=1, max_length=100000)

class JsonFormatRequest(BaseModel):
    json_text: str = Field(..., min_length=1, max_length=500000)
    indent: int = Field(default=2, ge=0, le=8)

class CodeHighlightRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000)
    language: str = Field(default="plaintext", max_length=50)

class QrCodeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    size: int = Field(default=10, ge=1, le=50)
    color: str = Field(default="#000000", max_length=7)
    bg_color: str = Field(default="#FFFFFF", max_length=7)

class Csv2JsonRequest(BaseModel):
    csv_text: str = Field(..., min_length=1, max_length=500000)
    delimiter: str = Field(default=",", max_length=1)

class TextDiffRequest(BaseModel):
    text_a: str = Field(..., min_length=1, max_length=100000)
    text_b: str = Field(..., min_length=1, max_length=100000)
    context_lines: int = Field(default=3, ge=0, le=10)

class UrlShortenRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    custom_alias: Optional[str] = Field(default=None, max_length=20)

class BaseResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

# HTML sanitization — escape user HTML to prevent XSS
ALLOWED_TAGS = {'b', 'i', 'em', 'strong', 'a', 'code', 'pre', 'del', 'img', 'br', 'hr',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'blockquote', 'span'}

def _sanitize_html(text: str) -> str:
    """Strip dangerous HTML patterns from generated markdown output.
    Removes event handlers, javascript: URLs, and script tags."""
    # Strip dangerous event handler attributes
    text = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    # Strip javascript: protocol URLs
    text = re.sub(r'(?<=["\'])\s*javascript\s*:[^\s"\']*', '', text, flags=re.IGNORECASE)
    # Strip <script> tags and their content
    text = re.sub(r'<script\b[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    return text

# Markdown to HTML
def _inline_format(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Images before links (images start with !)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
    return text

def md_to_html(md_text: str) -> str:
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    code_block_lang = ""
    code_block_content = []
    in_list = False
    list_type = None

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_lang = line.strip()[3:].strip()
                code_block_content = []
            else:
                in_code_block = False
                lang_class = f' class="language-{html_module.escape(code_block_lang)}"' if code_block_lang else ''
                code_html = html_module.escape('\n'.join(code_block_content))
                html_lines.append(f'<pre><code{lang_class}>{code_html}</code></pre>')
            i += 1
            continue
        if in_code_block:
            code_block_content.append(line)
            i += 1
            continue
        # Close list
        if in_list and not line.strip().startswith(('- ', '* ', '+ ')) and not re.match(r'^\d+\.\s', line.strip()):
            html_lines.append(f'</{list_type}>')
            in_list = False
            list_type = None

        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            html_lines.append(f'<h{level}>{_inline_format(header_match.group(2))}</h{level}>')
            i += 1
            continue

        if re.match(r'^(\*{3,}|-{3,}|_{3,})$', line.strip()):
            html_lines.append('<hr>')
            i += 1
            continue

        list_match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
        if list_match:
            if not in_list or list_type != 'ul':
                if in_list: html_lines.append(f'</{list_type}>')
                html_lines.append('<ul>')
                in_list, list_type = True, 'ul'
            html_lines.append(f'<li>{_inline_format(list_match.group(2))}</li>')
            i += 1
            continue

        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if ol_match:
            if not in_list or list_type != 'ol':
                if in_list: html_lines.append(f'</{list_type}>')
                html_lines.append('<ol>')
                in_list, list_type = True, 'ol'
            html_lines.append(f'<li>{_inline_format(ol_match.group(2))}</li>')
            i += 1
            continue

        if re.match(r'^>\s?(.*)$', line):
            html_lines.append(f'<blockquote>{_inline_format(re.match(r"^>\s?(.*)$", line).group(1))}</blockquote>')
            i += 1
            continue

        if not line.strip():
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p>{_inline_format(line)}</p>')
        i += 1

    if in_list:
        html_lines.append(f'</{list_type}>')
    raw_html = '\n'.join(html_lines)
    return _sanitize_html(raw_html)

# Code highlighting
KEYWORDS = {
    'python': ['def', 'class', 'import', 'from', 'return', 'if', 'elif', 'else', 'for', 'while',
               'try', 'except', 'finally', 'with', 'as', 'yield', 'raise', 'pass', 'break', 'continue',
               'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'lambda', 'async', 'await'],
    'javascript': ['function', 'const', 'let', 'var', 'return', 'if', 'else', 'for', 'while',
                   'try', 'catch', 'finally', 'throw', 'new', 'class', 'extends', 'import', 'export',
                   'default', 'async', 'await', 'typeof', 'instanceof', 'null', 'undefined', 'true', 'false'],
    'html': ['html', 'head', 'body', 'div', 'span', 'p', 'a', 'img', 'ul', 'ol', 'li', 'table',
             'tr', 'td', 'th', 'form', 'input', 'button', 'script', 'style', 'link', 'meta', 'title'],
    'java': ['public', 'private', 'protected', 'class', 'interface', 'extends', 'implements', 'static',
             'final', 'void', 'int', 'long', 'double', 'float', 'boolean', 'char', 'String', 'new',
             'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'throw', 'throws', 'import', 'package'],
    'sql': ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
            'TABLE', 'INTO', 'VALUES', 'SET', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'ON', 'AND', 'OR',
            'NOT', 'NULL', 'IS', 'LIKE', 'IN', 'BETWEEN', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT'],
}

def highlight_code(code: str, language: str) -> str:
    escaped = html_module.escape(code)
    lang_keywords = KEYWORDS.get(language.lower(), [])
    if not lang_keywords:
        return f'<pre><code>{escaped}</code></pre>'
    for kw in sorted(lang_keywords, key=len, reverse=True):
        escaped = re.sub(rf'\b({re.escape(kw)})\b', r'<span class="kw">\1</span>', escaped)
    escaped = re.sub(r'(&quot;[^&]*&quot;)', r'<span class="str">\1</span>', escaped)
    escaped = re.sub(r"(&#x27;[^&]*&#x27;)", r'<span class="str">\1</span>', escaped)
    escaped = re.sub(r'(#.*$)', r'<span class="cm">\1</span>', escaped, flags=re.MULTILINE)
    return f'<pre><code class="language-{language}">{escaped}</code></pre>'

# URL shortening store (in-memory)
url_store = {}
url_counter = 0
BASE_URL = os.getenv("BASE_URL", "https://text-toolkit-api.onrender.com")

def generate_short_code(url: str, custom_alias: str = None) -> str:
    global url_counter
    if custom_alias:
        if custom_alias in url_store:
            raise ValueError(f"Alias '{custom_alias}' already taken")
        url_store[custom_alias] = url
        return custom_alias
    url_counter += 1
    code = base64.urlsafe_b64encode(hashlib.md5(f"{url}{url_counter}".encode()).digest()[:6]).decode().rstrip('=')
    url_store[code] = url
    return code

def generate_qrcode(text: str, size: int = 10, color: str = "#000000", bg_color: str = "#FFFFFF") -> str:
    qr = qrcode_lib.QRCode(version=1, box_size=size, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color=color, back_color=bg_color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

def csv_to_json(csv_text: str, delimiter: str = ",") -> list:
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
    return [row for row in reader]

def text_diff(text_a: str, text_b: str, context_lines: int = 3) -> dict:
    import difflib
    a_lines = text_a.split('\n')
    b_lines = text_b.split('\n')
    diff = list(difflib.unified_diff(a_lines, b_lines, lineterm='', n=context_lines))
    changes = {"added": 0, "removed": 0, "unchanged": 0}
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            changes['added'] += 1
        elif line.startswith('-') and not line.startswith('---'):
            changes['removed'] += 1
        elif line.startswith(' '):
            changes['unchanged'] += 1
    return {"diff": '\n'.join(diff), "stats": changes, "total_changes": changes['added'] + changes['removed']}

# Endpoints
@app.get("/api/health")
async def health_check():
    return {"success": True, "data": {"status": "healthy", "service": "Smart Text Toolkit API", "version": "1.1.0"}, "timestamp": time.time()}

@app.post("/api/md2html", response_model=BaseResponse)
async def markdown_to_html(request: Request, body: MarkdownRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        html_output = md_to_html(body.markdown)
        return BaseResponse(success=True, data={"html": html_output, "input_length": len(body.markdown), "output_length": len(html_output)})
    except Exception as e:
        return BaseResponse(success=False, error=str(e))

@app.post("/api/format-json", response_model=BaseResponse)
async def format_json(request: Request, body: JsonFormatRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        # Defend against deeply nested JSON (DoS via RecursionError)
        max_depth = 100
        depth = 0
        for ch in body.json_text:
            if ch in '{([': depth += 1
            elif ch in '})]': depth -= 1
            if depth > max_depth:
                return BaseResponse(success=False, error=f"JSON nesting too deep (max={max_depth})")
        parsed = json.loads(body.json_text)
        formatted = json.dumps(parsed, indent=body.indent, ensure_ascii=False)
        is_dict = isinstance(parsed, dict)
        return BaseResponse(success=True, data={"formatted": formatted, "is_valid": True, "keys_count": len(parsed) if is_dict else None})
    except RecursionError:
        return BaseResponse(success=False, error="JSON nesting too deep")
    except json.JSONDecodeError as e:
        return BaseResponse(success=False, error=f"Invalid JSON at line {e.lineno}, col {e.colno}: {e.msg}")

@app.post("/api/code-highlight", response_model=BaseResponse)
async def code_highlight(request: Request, body: CodeHighlightRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        highlighted = highlight_code(body.code, body.language)
        return BaseResponse(success=True, data={"html": highlighted, "language": body.language, "supported_languages": list(KEYWORDS.keys())})
    except Exception as e:
        return BaseResponse(success=False, error=str(e))

@app.get("/api/languages")
async def list_languages():
    return BaseResponse(success=True, data={"languages": list(KEYWORDS.keys())})

@app.post("/api/qrcode", response_model=BaseResponse)
async def qr_code(request: Request, body: QrCodeRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        img_b64 = generate_qrcode(body.text, body.size, body.color, body.bg_color)
        return BaseResponse(success=True, data={
            "qr_code_base64": img_b64,
            "format": "png",
            "text": body.text,
            "size": body.size
        })
    except Exception as e:
        return BaseResponse(success=False, error=str(e))

@app.post("/api/csv2json", response_model=BaseResponse)
async def csv_to_json_endpoint(request: Request, body: Csv2JsonRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        data = csv_to_json(body.csv_text, body.delimiter)
        return BaseResponse(success=True, data={
            "json_array": data,
            "row_count": len(data),
            "delimiter": body.delimiter
        })
    except Exception as e:
        return BaseResponse(success=False, error=f"CSV parse error: {str(e)}")

@app.post("/api/img2base64")
async def img_to_base64(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        # Validate file type — only allow image MIME types
        ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp", "image/svg+xml"}
        ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
        if file.content_type and file.content_type not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        if file.filename:
            ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext and ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported extension: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        b64 = base64.b64encode(contents).decode()
        mime = file.content_type or "application/octet-stream"
        return {"success": True, "data": {
            "base64": f"data:{mime};base64,{b64}",
            "filename": file.filename,
            "size_bytes": len(contents),
            "mime_type": mime
        }}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/text-diff", response_model=BaseResponse)
async def text_diff_endpoint(request: Request, body: TextDiffRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        result = text_diff(body.text_a, body.text_b, body.context_lines)
        return BaseResponse(success=True, data=result)
    except Exception as e:
        return BaseResponse(success=False, error=str(e))

@app.post("/api/url-shorten", response_model=BaseResponse)
async def url_shorten(request: Request, body: UrlShortenRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    try:
        code = generate_short_code(body.url, body.custom_alias)
        return BaseResponse(success=True, data={
            "short_code": code,
            "short_url": f"{BASE_URL}/s/{code}",
            "original_url": body.url
        })
    except ValueError as e:
        return BaseResponse(success=False, error=str(e))

@app.get("/s/{short_code}")
async def redirect_short_url(request: Request, short_code: str):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip, max_rpm=120):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    if short_code in url_store:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url_store[short_code], status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
