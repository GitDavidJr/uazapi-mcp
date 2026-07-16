"""Smoke test do uazapi-mcp contra um servidor UAZAPI FALSO (sem WhatsApp real).

Roda com:  uv run python tests/smoke_test.py
Sobe um http.server local imitando os endpoints principais da UAZAPI, aponta o
MCP para ele e chama as tools como funções, validando o fluxo completo:
admin -> use_instance -> connect/QR -> envio -> send_and_wait_reply (SSE).
"""

import base64
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ADMIN_TOKEN = "admin-secret-token-0000000000"
TOKEN_OZANA = "token-ozana-12345678901234567890"
TOKEN_NOVA = "token-nova-098765432109876543210"
TINY_PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
).decode()

INSTANCES = [
    {
        "id": "inst-ozana",
        "token": TOKEN_OZANA,
        "name": "Ozana",
        "owner": "5573999990000",
        "profileName": "Ozana IA",
        "status": "connected",
        "created": "2026-01-01T00:00:00Z",
    },
    {
        "id": "inst-nova",
        "token": TOKEN_NOVA,
        "name": "Nova",
        "owner": "",
        "profileName": "",
        "status": "disconnected",
        "created": "2026-07-01T00:00:00Z",
    },
]
STATE = {"nova_connecting": False, "created_seq": 0}


def _inst_by_token(token):
    return next((i for i in INSTANCES if i["token"] == token), None)


class FakeUazapi(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencia o log do http.server
        pass

    def _json(self, code, obj):
        payload = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}")
        except ValueError:
            return {}

    def _handle(self, method):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        admintoken = self.headers.get("admintoken")
        token = self.headers.get("token")
        body = self._body()

        if path == "/sse":
            tok = (query.get("token") or [None])[0]
            if not _inst_by_token(tok):
                return self._json(401, {"error": "invalid token"})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            try:
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
                time.sleep(0.8)
                evt = {
                    "type": "messages",
                    "data": {
                        "chatid": "5511888888888@s.whatsapp.net",
                        "sender": "5511888888888@s.whatsapp.net",
                        "senderName": "Cliente Teste",
                        "fromMe": False,
                        "wasSentByApi": False,
                        "isGroup": False,
                        "text": "sim, confirmo!",
                        "messageType": "text",
                        "messageid": "MSG123",
                        "messageTimestamp": int(time.time() * 1000),
                    },
                }
                self.wfile.write(f"data: {json.dumps(evt)}\n\n".encode())
                self.wfile.flush()
                time.sleep(5)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return None

        # ---- admin
        if path == "/instance/all":
            if admintoken != ADMIN_TOKEN:
                return self._json(401, {"error": "admintoken invalido"})
            return self._json(200, INSTANCES)
        if path == "/instance/create":
            if admintoken != ADMIN_TOKEN:
                return self._json(401, {"error": "admintoken invalido"})
            STATE["created_seq"] += 1
            inst = {
                "id": f"inst-new-{STATE['created_seq']}",
                "token": f"token-new-{STATE['created_seq']:030d}",
                "name": body.get("name", "sem nome"),
                "owner": "",
                "status": "disconnected",
                "adminField01": body.get("adminField01"),
            }
            INSTANCES.append(inst)
            return self._json(200, {"response": "ok", "instance": inst, "token": inst["token"], "connected": False})

        inst = _inst_by_token(token)
        if inst is None:
            return self._json(401, {"error": "token invalido"})

        if path == "/instance/status":
            connecting = inst["status"] == "connecting"
            payload = dict(inst)
            if connecting:
                payload["qrcode"] = "data:image/png;base64," + TINY_PNG_B64 * 5
            return self._json(
                200,
                {
                    "instance": payload,
                    "status": {"connected": inst["status"] == "connected", "loggedIn": inst["status"] == "connected"},
                },
            )
        if path == "/instance/connect":
            if inst["status"] != "connected":
                inst["status"] = "connecting"
            payload = dict(inst)
            payload["qrcode"] = "data:image/png;base64," + TINY_PNG_B64 * 5
            if body.get("phone"):
                payload["paircode"] = "ABCD-1234"
            return self._json(200, {"connected": False, "loggedIn": False, "instance": payload})
        if path in ("/send/text", "/send/media"):
            return self._json(200, {"response": {"status": "queued", "message": "ok"}, "echo": body, "used_token_tail": token[-6:]})
        if path == "/chat/find":
            return self._json(200, {"chats": [{"wa_chatid": "5511888888888@s.whatsapp.net", "wa_name": "Cliente Teste"}], "pagination": {"totalRecords": 1}})
        if path == "/instance" and method == "DELETE":
            INSTANCES.remove(inst)
            return self._json(200, {"response": "deleted"})
        if path == "/webhook" and method == "GET":
            return self._json(200, [{"id": "wh1", "enabled": True, "url": "https://exemplo.com/hook", "events": ["messages"]}])
        if path == "/instance/privacy" and method == "GET":
            return self._json(200, {"last": "all", "online": "all"})
        # fallback: ecoa o que recebeu (endpoints não modelados no fake)
        return self._json(200, {"ok": True, "path": path, "method": method, "echo": body})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_PUT(self):
        self._handle("PUT")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeUazapi)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    state_file = Path(tempfile.mkdtemp()) / "state.json"
    os.environ["UAZAPI_BASE_URL"] = f"http://127.0.0.1:{port}"
    os.environ["UAZAPI_ADMIN_TOKEN"] = ADMIN_TOKEN
    os.environ.pop("UAZAPI_TOKEN", None)
    os.environ["UAZAPI_STATE_FILE"] = str(state_file)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    import uazapi_mcp.server  # noqa: F401  (registra todas as tools)
    from uazapi_mcp.core import mcp
    from uazapi_mcp import (
        tools_admin,
        tools_business,
        tools_chats,
        tools_events,
        tools_instance,
        tools_send,
    )

    failures = []

    def check(name, cond, extra=""):
        status = "OK " if cond else "FAIL"
        print(f"[{status}] {name}{'  ' + str(extra)[:120] if extra and not cond else ''}")
        if not cond:
            failures.append(name)

    tools = mcp._tool_manager.list_tools()
    check(f"tools registradas ({len(tools)})", len(tools) >= 60)

    info = tools_admin.uazapi_info()
    check("uazapi_info admin_mode", info.get("admin_mode") is True and info.get("total_instances") == 2, info)

    lst = tools_admin.admin_list_instances(search="ozana")
    check("admin_list_instances busca", lst.get("count") == 1, lst)
    tok_shown = lst["instances"][0].get("token", "")
    check("token mascarado na listagem", "…" in tok_shown and TOKEN_OZANA not in json.dumps(lst), tok_shown)

    used = tools_instance.use_instance("Ozana")
    check("use_instance por nome", "Ozana" in json.dumps(used), used)
    saved = state_file.read_text()
    check("state file sem token", TOKEN_OZANA not in saved and TOKEN_NOVA not in saved, saved)

    st = tools_instance.instance_status()
    check("instance_status via default", (st.get("status") or {}).get("connected") is True, st)

    st2 = tools_instance.instance_status(instance="5573999990000")
    check("instance_status por número", (st2.get("status") or {}).get("connected") is True, st2)

    conn = tools_instance.connect_instance(instance="Nova")
    qr_file = conn.get("qr_file", "")
    check("connect_instance gera qr_file", qr_file and Path(qr_file).exists(), conn)
    check("qrcode não vaza em claro", "iVBOR" not in json.dumps(conn), None)

    qr = tools_instance.get_qr_code(instance="Nova")
    check("get_qr_code", qr.get("qr_file") and Path(qr["qr_file"]).exists(), qr)

    sent_qr = tools_instance.send_connection_qr(to="5511888888888", instance="Nova", via_instance="Ozana")
    check(
        "send_connection_qr envia pela Ozana",
        (sent_qr.get("sent") or {}).get("used_token_tail") == TOKEN_OZANA[-6:],
        sent_qr,
    )

    same = tools_instance.send_connection_qr(to="5511888888888", instance="Nova", via_instance="Nova")
    check("send_connection_qr recusa mesma instância", same.get("error") is True, same)

    pair = tools_instance.send_connection_qr(
        to="5511888888888", instance="Nova", via_instance="Ozana", paircode_phone="5511777777777"
    )
    check("send_connection_qr paircode", pair.get("paircode") == "ABCD-1234", pair)

    sent = tools_send.send_text(number="5511888888888", text="olá!", delay_ms=1200)
    check(
        "send_text default + delay",
        (sent.get("echo") or {}).get("delay") == 1200 and sent.get("used_token_tail") == TOKEN_OZANA[-6:],
        sent,
    )

    sent_nova = tools_send.send_text(number="5511888888888", text="oi", instance="Nova")
    check("send_text instance override", sent_nova.get("used_token_tail") == TOKEN_NOVA[-6:], sent_nova)

    chats = tools_chats.find_chats(name_contains="Cliente")
    check("find_chats", (chats.get("pagination") or {}).get("totalRecords") == 1, chats)

    t0 = time.time()
    reply = tools_events.send_and_wait_reply(number="5511888888888", text="confirma?", timeout_seconds=15)
    took = time.time() - t0
    check(
        "send_and_wait_reply via SSE",
        reply.get("replied") is True and reply["reply"].get("text") == "sim, confirmo!" and took < 10,
        reply,
    )

    created = tools_admin.admin_create_instance(name="Cliente XPTO", admin_field_01="plano-pro", connect_now=True)
    check(
        "admin_create_instance + connect_now",
        created.get("qr_file") and Path(created["qr_file"]).exists() and "token-new" not in json.dumps(created),
        created,
    )

    raw = tools_business.raw_api_request(method="GET", path="/instance/privacy")
    check("raw_api_request", raw.get("last") == "all", raw)

    deleted = tools_instance.delete_instance(instance="Cliente XPTO", confirm=True)
    check("delete_instance", not (isinstance(deleted, dict) and deleted.get("error")), deleted)

    no_confirm = tools_instance.disconnect_instance()
    check("disconnect exige confirm", no_confirm.get("error") is True, no_confirm)

    server.shutdown()
    print()
    if failures:
        print(f"❌ {len(failures)} teste(s) falharam: {failures}")
        sys.exit(1)
    print(f"✅ smoke test passou — {len(tools)} tools registradas.")


if __name__ == "__main__":
    main()
