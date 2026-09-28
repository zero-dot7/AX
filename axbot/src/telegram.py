"""Minimal Telegram Bot API client — stdlib only. See DESIGN.md (B2)."""
import json
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org/bot{}/{}"
MAX_LEN = 4000  # safety margin under the 4096 limit


class BotError(Exception):
    pass


def split_message(text, limit=MAX_LEN):
    """Split into chunks on line boundaries, hard-split if a line is huge."""
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = line if not cur else cur + "\n" + line
    if cur:
        chunks.append(cur)
    return chunks


class Bot:
    def __init__(self, token):
        if not token:
            raise BotError("empty token")
        self.token = token

    def _call(self, method, payload, timeout):
        url = API.format(self.token, method)
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise BotError(f"telegram {method}: HTTP {e.code}") from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise BotError(f"telegram {method}: {e}") from None
        if not body.get("ok"):
            raise BotError(f"telegram {method}: {body.get('description')}")
        return body["result"]

    def get_updates(self, offset=0, timeout=25):
        return self._call("getUpdates",
                          {"offset": offset, "timeout": timeout,
                           "allowed_updates": ["message"]},
                          timeout=timeout + 10)

    def send_message(self, chat_id, text):
        for chunk in split_message(text):
            for attempt in range(2):
                try:
                    return self._call("sendMessage",
                                      {"chat_id": chat_id, "text": chunk}, 30)
                except BotError as e:
                    if "429" in str(e) and attempt == 0:
                        time.sleep(3)
                        continue
                    raise
