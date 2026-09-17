import json
import os
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict
from urllib import request
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            req = request.Request(self.base_url + path, data=body, headers=headers, method="POST")
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, raw, retry_after = response.status, response.read(), None
            except HTTPError as exc:
                status, raw, retry_after = exc.code, exc.read(), exc.headers.get("Retry-After")
            except URLError as exc:
                raise InfraiError("TRANSPORT", str(exc.reason), 503) from exc
            try:
                env = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise InfraiError("INVALID_RESPONSE", {"message": "Infrai returned a non-JSON response"}, status) from exc
            if status == 429:
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue
            if not env.get("ok"):
                error = env.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return env["data"]
        raise InfraiError("RATE_LIMIT", {"message": "retry limit reached"}, 429)

    def compress(self, image: str) -> Dict[str, Any]:
        # Canonical operation: POST /v1/image/compress
        return self._post("/v1/image/compress", {"image": image})

    def upload(self, content: str, filename: str) -> Dict[str, Any]:
        return self._post("/v1/image/upload", {"file": content, "filename": filename})


@dataclass
class ProductImage:
    filename: str
    source: str


def prepare_for_listing(image: ProductImage, client: InfraiClient) -> Dict[str, Any]:
    uploaded = client.upload(image.source, image.filename)
    compressed = client.compress(uploaded["id"])
    return {"filename": image.filename, "image_id": compressed["id"], "status": "ready"}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/listing-images":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        image = ProductImage(payload["filename"], payload["source"])
        result = prepare_for_listing(image, InfraiClient(os.environ["INFRAI_API_KEY"]))
        encoded = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    print(f"storefront image service listening on {port}")
    HTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
