from __future__ import annotations

import json
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings
from .image_io import image_data_url


class ApiError(RuntimeError):
    pass


class OpenAICompatClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def chat_json(self, model: str, messages: list[dict[str, Any]], *, max_tokens: int = 900) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
        }
        data = self._request_json("POST", "/chat/completions", payload)
        content = data["choices"][0]["message"]["content"]
        return parse_json_object(content)

    def edit_image(self, model: str, image_path: Path, prompt: str, *, size: str = "1024x1024") -> str:
        fields = {"model": model, "prompt": prompt, "size": size}
        files = {"image": image_path}
        data = self._request_multipart("/images/edits", fields, files)
        try:
            return data["data"][0]["b64_json"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiError(f"Image edit response did not contain data[0].b64_json: {data}") from exc

    def _request_json(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.settings.base_url + path,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
        )
        return self._send(request)

    def _request_multipart(self, path: str, fields: dict[str, str], files: dict[str, Path]) -> dict[str, Any]:
        boundary = "----physical-agent-" + uuid.uuid4().hex
        parts: list[bytes] = []
        for name, value in fields.items():
            parts.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
            )
        for name, file_path in files.items():
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            file_bytes = file_path.read_bytes()
            parts.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"; filename="{file_path.name}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode("utf-8")
                + file_bytes
                + b"\r\n"
            )
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        request = Request(
            self.settings.base_url + path,
            data=b"".join(parts),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        return self._send(request)

    def _send(self, request: Request) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2**attempt)
                    last_error = ApiError(f"HTTP {exc.code}: {body}")
                    continue
                raise ApiError(f"HTTP {exc.code}: {body}") from exc
            except URLError as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise ApiError(f"Network error: {exc}") from exc
        raise ApiError(str(last_error))


def vision_user_message(text: str, image_paths: list[Path]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for path in image_paths:
        content.append({"type": "image_url", "image_url": {"url": image_data_url(path)}})
    return {"role": "user", "content": content}


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object from model response.")
    return value
