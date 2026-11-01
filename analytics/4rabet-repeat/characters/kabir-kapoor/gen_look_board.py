"""Generate 4-look concept board for Kabir Kapoor via KIE Nano Banana 2.1."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "LOOKBOARD_4_variants_C_fullbody_16x9.jpg"
BOARD = "C_NEW"
REPO = Path(r"C:\Users\317\reels-media")
JOBS = "https://api.kie.ai/api/v1/jobs"
UPLOAD = "https://kieai.redpandaai.co/api/file-stream-upload"

REFS = [
    ROOT / "REF_kabir_orange_suit.jpg",
    ROOT / "LOGO_starkbet.png",
    ROOT / "REF_card_layout_bunty.jpg",
    ROOT / "LOOKBOARD_4_variants.jpg",
]

PROMPT = """
ONE photoreal horizontal 16:9 concept board (widescreen), 2x2 grid of FOUR brand-new full-body looks. Light gray seamless studio. Thin black gutters. Labels A B C D in small white text at each panel bottom.

IMPORTANT: reference image 4 is a PREVIOUS board — do NOT repeat those outfits (no orange fedora black suit, no cobalt double-breasted, no half orange/indigo blazer, no track jacket). Invent four completely fresh silhouettes.

IDENTITY (all panels): Kabir Kapoor from reference image 1 — South Asian, thick black rectangular glasses, dark wavy hair with bright orange streak above left ear, thick black handlebar mustache with curled tips, short beard. Same face. Starkbet logo from reference image 2 on clothing: STARK (deep indigo) stacked over BET (bright orange).

FRAMING (every panel): true full body head-to-toe lookbook shot; entire shoes on the floor with empty floor margin below; legs fully visible; no waist/knee/shin crop; camera pulled back so the whole person fits inside each cell of the widescreen grid.

FOUR NEW LOOKS (quirky-cool, recognizable, not clown):

A — DESERT BANDIT HOST: sand/cream linen open shirt over orange Starkbet tee; indigo waistcoat; cream trousers; brown boots; thin orange scarf loosely at neck; no hat; glasses stay. Warm traveler-host vibe.

B — RAIN DEALER: long charcoal trench coat worn open; neon-orange raincoat lining flashing; black slim trousers; polished black boots; Starkbet on black hoodie underneath; no hat. Cinematic rainy-city bookie.

C — CRICKET UNCLE FLEX: ivory cricket-style sweater vest with thin orange+indigo stripes over white tee with Starkbet; navy chinos; white sneakers; flat indigo newsboy/baker boy cap (NOT a fedora). Soft local-celebrity charm.

D — MIRROR CLUB: glossy black vinyl/leather slim jacket; cobalt mesh long-sleeve underlayer; black slim pants; chunky white sneakers with orange sole; tiny Starkbet metal pin on lapel; rectangular glasses; no hat. Nightclub host energy.

Standing, facing camera, relaxed hands. Commercial casting light. Widescreen 16:9 composition overall.
""".strip()

def load_key() -> str:
    env = (REPO / ".env").read_text(encoding="utf-8")
    m = re.search(r"^KIE_API_KEY=(.+)$", env, re.M)
    if not m:
        raise SystemExit("KIE_API_KEY missing in .env")
    key = m.group(1).strip().strip('"').strip("'")
    if len(key) < 8:
        raise SystemExit("KIE_API_KEY empty")
    return key


def upload(path: Path, key: str) -> str:
    boundary = "----kieboundary7MA4YWxkTrZu0gW"
    data = path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            data,
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="uploadPath"\r\n\r\n',
            b"kabir-refs\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="fileName"\r\n\r\n',
            path.name.encode() + b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        UPLOAD,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = json.loads(r.read().decode())
    if payload.get("code") not in (200, None) and not payload.get("success", True):
        raise RuntimeError(f"upload failed: {payload}")
    data = payload.get("data") or payload
    url = data.get("downloadUrl") if isinstance(data, dict) else None
    if not url:
        raise RuntimeError(f"no downloadUrl: {payload}")
    print("uploaded", path.name)
    return url


def create_task(key: str, image_urls: list[str]) -> str:
    payload = {
        "model": "nano-banana-2-1",
        "input": {
            "prompt": PROMPT,
            "image_input": image_urls,
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "output_format": "jpg",
        },
    }
    req = urllib.request.Request(
        f"{JOBS}/createTask",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read().decode())
    if body.get("code") != 200:
        raise RuntimeError(f"createTask failed: {body}")
    task_id = body["data"]["taskId"]
    print("task", task_id)
    return task_id


def poll(key: str, task_id: str, timeout_s: int = 300) -> str:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        req = urllib.request.Request(
            f"{JOBS}/recordInfo?taskId={task_id}",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode())
        data = body.get("data") or {}
        state = data.get("state") or data.get("status") or body.get("msg")
        print("state", state)
        if state in ("success", "SUCCESS", "finished", "complete", "completed"):
            result = data.get("resultJson") or data.get("result") or data
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    pass
            urls = []
            if isinstance(result, dict):
                urls = result.get("resultUrls") or result.get("result_urls") or []
                if not urls and result.get("url"):
                    urls = [result["url"]]
            if not urls and data.get("resultUrls"):
                urls = data["resultUrls"]
            if not urls:
                raise RuntimeError(f"success but no urls: {body}")
            return urls[0]
        if state in ("fail", "failed", "FAILED", "error"):
            raise RuntimeError(f"task failed: {body}")
        time.sleep(4)
    raise TimeoutError("poll timeout")


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as r:
        dest.write_bytes(r.read())
    print("saved", dest, "bytes", dest.stat().st_size)


def main() -> None:
    key = load_key()
    for p in REFS:
        if not p.exists():
            raise SystemExit(f"missing ref {p}")
    urls = [upload(p, key) for p in REFS]
    task_id = create_task(key, urls)
    result_url = poll(key, task_id)
    download(result_url, OUT)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode(errors="replace")[:1000])
        raise
