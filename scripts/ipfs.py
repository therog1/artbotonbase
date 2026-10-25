"""Pin each days/<date>.png to IPFS (Pinata) and point days/<date>.json at ipfs://CID.

Idempotent: days/ipfs.json maps date -> {cid, sha256 of the image}. A day is
re-pinned only if its image bytes changed. Any Pinata error skips that day;
the script always exits 0 so it never blocks anything else.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DAYS = Path("days")
INDEX = DAYS / "ipfs.json"
V3_URL = "https://uploads.pinata.cloud/v3/files"
PIN_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
HTTPS = "https://therog1.github.io/artbotonbase/days/{date}.png"


def mime_of(data):
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return "application/octet-stream", "bin"


def _multipart(fields, name, data, mime):
    boundary = uuid.uuid4().hex
    parts = [
        (f'Content-Disposition: form-data; name="{k}"\r\n\r\n').encode() + v.encode()
        for k, v in fields.items()
    ]
    parts.append(
        (f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
         f"Content-Type: {mime}\r\n\r\n").encode() + data
    )
    body = b"".join(f"--{boundary}\r\n".encode() + p + b"\r\n" for p in parts)
    return body + f"--{boundary}--\r\n".encode(), boundary


def _post(url, jwt, body, boundary):
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {jwt}",
            "User-Agent": "artbot-ipfs/1.0",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)


def pin(jwt, date, data, mime, ext):
    name = f"artbot-{date}.{ext}"
    # Pinata Files API (v3), public network. Falls back to the legacy pinning API.
    try:
        body, b = _multipart({"network": "public", "name": name}, name, data, mime)
        return _post(V3_URL, jwt, body, b)["data"]["cid"]
    except urllib.error.HTTPError as err:
        if err.code not in (401, 403, 404):
            raise
        v3 = f"v3 {err.code} {err.read().decode(errors='replace')[:160]}"
    body, b = _multipart(
        {"pinataMetadata": json.dumps({"name": name}), "pinataOptions": json.dumps({"cidVersion": 1})},
        name, data, mime,
    )
    try:
        return _post(PIN_URL, jwt, body, b)["IpfsHash"]
    except urllib.error.HTTPError as err:
        legacy = f"legacy {err.code} {err.read().decode(errors='replace')[:160]}"
        raise RuntimeError(f"{v3} | {legacy}") from None


def point_json(date, cid, mime):
    path = DAYS / f"{date}.json"
    if not path.exists():
        return False
    meta = json.loads(path.read_text())
    want = f"ipfs://{cid}"
    if meta.get("image") == want:
        return False
    meta["image"] = want
    meta["image_https"] = HTTPS.format(date=date)
    meta["media"] = {"mimeType": mime}
    path.write_text(json.dumps(meta))
    return True


def main():
    jwt = os.environ.get("PINATA_JWT", "").strip()
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    changed = 0
    for png in sorted(DAYS.glob("*.png")):
        date = png.stem
        data = png.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        mime, ext = mime_of(data)
        entry = index.get(date)
        if not entry or entry.get("sha256") != digest:
            if not jwt:
                print(f"{date}: no PINATA_JWT, skipped")
                continue
            try:
                cid = pin(jwt, date, data, mime, ext)
            except Exception as err:  # never fail the run
                detail = f" {err}" if isinstance(err, RuntimeError) else ""
                if hasattr(err, "code"):
                    try:
                        detail = f" {err.code} {err.read().decode()[:200]}"
                    except Exception:
                        detail = f" {err.code}"
                print(f"{date}: pin failed ({type(err).__name__}{detail}), skipped")
                if entry:  # old CID is for an older image: fall back to https
                    path = DAYS / f"{date}.json"
                    if path.exists():
                        meta = json.loads(path.read_text())
                        if meta.get("image") == f"ipfs://{entry['cid']}":
                            meta["image"] = HTTPS.format(date=date)
                            path.write_text(json.dumps(meta))
                            changed += 1
                continue
            entry = {"cid": cid, "sha256": digest, "mime": mime}
            index[date] = entry
            changed += 1
            print(f"{date}: pinned {cid}")
            time.sleep(0.5)
        if point_json(date, entry["cid"], entry.get("mime", mime)):
            changed += 1
            print(f"{date}: json -> ipfs://{entry['cid']}")
    INDEX.write_text(json.dumps(index, indent=1, sort_keys=True) + "\n")
    print(f"changes: {changed}")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"ipfs step error ({type(err).__name__}), skipped")
    sys.exit(0)
