"""Núcleo do uazapi-mcp: configuração, HTTP, resolução de instâncias e estado local.

Modos de operação:
- Só UAZAPI_TOKEN: modo single-instance (compatível com v0.1) — as tools de
  instância usam sempre esse token.
- UAZAPI_ADMIN_TOKEN (com ou sem UAZAPI_TOKEN): modo admin — tools de admin
  liberadas (criar/listar instâncias, webhook global etc.) e qualquer tool
  aceita `instance` (id, nome, número ou token) para escolher a instância.
  Os tokens de instância são resolvidos em memória via /instance/all e NUNCA
  são gravados em disco.

A "instância padrão" (número do dia a dia) é definida pela tool use_instance e
fica salva em ~/.config/uazapi-mcp/state.json (apenas id/nome/número — sem token).
"""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("UAZAPI_BASE_URL", "").rstrip("/")
ADMIN_TOKEN = os.environ.get("UAZAPI_ADMIN_TOKEN", "")
ENV_TOKEN = os.environ.get("UAZAPI_TOKEN", "")
TIMEOUT = float(os.environ.get("UAZAPI_TIMEOUT", "60"))

if not BASE_URL or not (ADMIN_TOKEN or ENV_TOKEN):
    raise RuntimeError(
        "Defina UAZAPI_BASE_URL e pelo menos um token nas variáveis de ambiente "
        "do servidor MCP: UAZAPI_ADMIN_TOKEN (gerencia o servidor inteiro) e/ou "
        "UAZAPI_TOKEN (token de uma instância específica)."
    )

mcp = FastMCP("uazapi")

STATE_FILE = Path(
    os.environ.get("UAZAPI_STATE_FILE")
    or Path.home() / ".config" / "uazapi-mcp" / "state.json"
)

QR_DIR = Path(tempfile.gettempdir()) / "uazapi-mcp"

# Chaves cujo valor é secreto e sai mascarado das respostas por padrão.
SENSITIVE_KEYS = {
    "token",
    "admintoken",
    "admin_token",
    "openai_apikey",
    "chatwoot_access_token",
    "apikey",
}

MAX_STR = 4000  # strings maiores que isso são truncadas nas respostas


# ---------------------------------------------------------------- estado local


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def get_default_ref() -> Optional[dict]:
    """Instância padrão persistida (dict com id/name/owner) ou None."""
    ref = _load_state().get("default_instance")
    return ref if isinstance(ref, dict) else None


def set_default_ref(ref: Optional[dict]) -> None:
    state = _load_state()
    if ref is None:
        state.pop("default_instance", None)
    else:
        state["default_instance"] = ref
    _save_state(state)


# ------------------------------------------------------------------------ HTTP


def _request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    admin: bool = False,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> Any:
    headers = {"Accept": "application/json"}
    if admin:
        if not ADMIN_TOKEN:
            return {
                "error": True,
                "status": 0,
                "body": "operação exige UAZAPI_ADMIN_TOKEN (não configurado).",
            }
        headers["admintoken"] = ADMIN_TOKEN
    if token:
        headers["token"] = token
    try:
        resp = httpx.request(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            params=params,
            json=json_body,
            timeout=timeout or TIMEOUT,
        )
    except httpx.HTTPError as exc:
        return {"error": True, "status": 0, "body": f"falha HTTP: {exc}"}
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:2000]}
    if resp.status_code >= 400:
        return {"error": True, "status": resp.status_code, "body": data}
    return data


def is_error(data: Any) -> bool:
    return isinstance(data, dict) and data.get("error") is True


def admin_call(
    method: str,
    path: str,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    show_tokens: bool = False,
) -> Any:
    return sanitize(
        _request(method, path, admin=True, params=params, json_body=json_body),
        show_tokens=show_tokens,
    )


# ----------------------------------------------------- instâncias e resolução

_instances_cache: dict = {"ts": 0.0, "data": None}
CACHE_TTL = 30.0


def all_instances(force: bool = False) -> Any:
    """Lista crua de instâncias via admin (com cache de 30s, tokens em memória)."""
    if not ADMIN_TOKEN:
        return {
            "error": True,
            "status": 0,
            "body": "listar/resolver instâncias exige UAZAPI_ADMIN_TOKEN.",
        }
    now = time.time()
    if force or _instances_cache["data"] is None or now - _instances_cache["ts"] > CACHE_TTL:
        data = _request("GET", "/instance/all", admin=True)
        if is_error(data):
            return data
        if isinstance(data, dict):
            data = data.get("instances") or data.get("response") or data
        if not isinstance(data, list):
            return {"error": True, "status": 0, "body": {"resposta inesperada": str(data)[:500]}}
        _instances_cache.update(ts=now, data=data)
    return _instances_cache["data"]


def invalidate_instances_cache() -> None:
    _instances_cache.update(ts=0.0, data=None)


def _digits(s: Optional[str]) -> str:
    return re.sub(r"\D", "", s or "")


def match_instance(ref: str) -> Any:
    """Acha uma instância por id, token, nome, profileName ou número (owner)."""
    instances = all_instances()
    if is_error(instances):
        return instances
    ref_norm = ref.strip()
    low = ref_norm.lower()
    refd = _digits(ref_norm)

    matchers = [
        lambda i: i.get("id") == ref_norm,
        lambda i: i.get("token") == ref_norm,
        lambda i: (i.get("name") or "").lower() == low,
        lambda i: (i.get("profileName") or "").lower() == low,
        lambda i: bool(refd) and len(refd) >= 8 and _digits(i.get("owner")).endswith(refd),
        lambda i: bool(low) and low in (i.get("name") or "").lower(),
    ]
    for pred in matchers:
        cands = [i for i in instances if pred(i)]
        if len(cands) == 1:
            return cands[0]
        if len(cands) > 1:
            return {
                "error": True,
                "status": 0,
                "body": {
                    "message": f"referência '{ref}' é ambígua entre {len(cands)} instâncias",
                    "candidates": [slim_instance(c) for c in cands],
                },
            }
    return {
        "error": True,
        "status": 0,
        "body": f"nenhuma instância encontrada para '{ref}'. Use admin_list_instances para ver as disponíveis.",
    }


def resolve_token(instance: Optional[str] = None) -> Any:
    """Resolve qual token usar. Retorna (token, instance_dict|None) ou dict de erro.

    Ordem sem `instance`: instância padrão (use_instance) > UAZAPI_TOKEN >
    única instância do servidor (modo admin).
    """
    if instance:
        if ADMIN_TOKEN:
            inst = match_instance(instance)
            if not is_error(inst):
                return inst.get("token"), inst
            if len(instance) >= 20 and " " not in instance:
                return instance, None  # aceita token literal desconhecido do /instance/all
            return inst
        if len(instance) >= 20 and " " not in instance:
            return instance, None
        return {
            "error": True,
            "status": 0,
            "body": (
                "sem UAZAPI_ADMIN_TOKEN não dá para resolver instância por nome/número. "
                "Omita `instance` (usa o UAZAPI_TOKEN) ou passe o token literal da instância."
            ),
        }

    ref = get_default_ref()
    if ref and ADMIN_TOKEN:
        instances = all_instances()
        if is_error(instances):
            return instances
        for i in instances:
            if i.get("id") == ref.get("id"):
                return i.get("token"), i
        return {
            "error": True,
            "status": 0,
            "body": (
                f"a instância padrão ({ref.get('name') or ref.get('id')}) não existe mais no servidor. "
                "Rode use_instance de novo para escolher outra."
            ),
        }
    if ENV_TOKEN:
        return ENV_TOKEN, None
    if ADMIN_TOKEN:
        instances = all_instances()
        if is_error(instances):
            return instances
        if len(instances) == 1:
            return instances[0].get("token"), instances[0]
        return {
            "error": True,
            "status": 0,
            "body": (
                f"o servidor tem {len(instances)} instâncias e nenhuma padrão definida. "
                "Chame use_instance(<nome|número|id>) ou passe `instance` na própria tool."
            ),
        }
    return {"error": True, "status": 0, "body": "nenhum token disponível."}


def instance_request(
    method: str,
    path: str,
    instance: Optional[str] = None,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> Any:
    resolved = resolve_token(instance)
    if is_error(resolved):
        return resolved
    token, _ = resolved
    return _request(method, path, token=token, params=params, json_body=json_body, timeout=timeout)


def call(
    method: str,
    path: str,
    instance: Optional[str] = None,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    timeout: Optional[float] = None,
    show_tokens: bool = False,
) -> Any:
    """instance_request + sanitize — atalho usado pela maioria das tools."""
    return sanitize(
        instance_request(method, path, instance, params, json_body, timeout),
        show_tokens=show_tokens,
    )


# ------------------------------------------------------------- apresentação


def mask_token(t: str) -> str:
    if not t:
        return ""
    if len(t) <= 8:
        return "***"
    return t[:4] + "…" + t[-4:]


def sanitize(obj: Any, show_tokens: bool = False, _depth: int = 0) -> Any:
    """Mascara segredos e remove/trunca payloads gigantes (qrcode base64 etc.)."""
    if _depth > 8:
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl == "qrcode" and isinstance(v, str) and len(v) > 200:
                out[k] = "<qrcode base64 omitido — use get_qr_code para salvar em arquivo>"
            elif kl in SENSITIVE_KEYS and isinstance(v, str) and v and not show_tokens:
                out[k] = mask_token(v)
            else:
                out[k] = sanitize(v, show_tokens, _depth + 1)
        return out
    if isinstance(obj, list):
        return [sanitize(v, show_tokens, _depth + 1) for v in obj]
    if isinstance(obj, str) and len(obj) > MAX_STR:
        return obj[:MAX_STR] + f"…[truncado, {len(obj)} chars]"
    return obj


def slim_instance(inst: dict, show_token: bool = False) -> dict:
    """Versão enxuta de uma instância para listagens (sem chatbot/campos internos)."""
    ref = get_default_ref() or {}
    out = {
        "id": inst.get("id"),
        "name": inst.get("name"),
        "status": inst.get("status"),
        "owner": inst.get("owner"),
        "profileName": inst.get("profileName"),
        "systemName": inst.get("systemName"),
        "token": inst.get("token") if show_token else mask_token(inst.get("token") or ""),
        "adminField01": inst.get("adminField01"),
        "adminField02": inst.get("adminField02"),
        "created": inst.get("created"),
        "lastDisconnectReason": inst.get("lastDisconnectReason"),
    }
    if inst.get("paircode"):
        out["paircode"] = inst["paircode"]
    if ref.get("id") and inst.get("id") == ref.get("id"):
        out["isDefault"] = True
    return {k: v for k, v in out.items() if v not in (None, "")}


# ------------------------------------------------------------- conexão / QR


def save_qr_png(qr_b64: str, label: str) -> str:
    """Decodifica o QR base64 e salva como PNG em um diretório temporário."""
    QR_DIR.mkdir(parents=True, exist_ok=True)
    data = qr_b64.split(",", 1)[1] if qr_b64.startswith("data:") else qr_b64
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", label or "instance")[:40]
    path = QR_DIR / f"qr-{safe}-{int(time.time())}.png"
    path.write_bytes(base64.b64decode(data))
    return str(path)


def fetch_connection(token: str, phone: Optional[str] = None, wait_seconds: float = 12.0) -> Any:
    """POST /instance/connect e aguarda o qrcode/paircode aparecer (ou conectar)."""
    body = {"phone": phone} if phone else {}
    data = _request("POST", "/instance/connect", token=token, json_body=body)
    deadline = time.time() + wait_seconds
    while not is_error(data) and time.time() < deadline:
        inst = data.get("instance") or {}
        status_obj = data.get("status") or {}
        connected = data.get("connected", status_obj.get("connected"))
        logged = data.get("loggedIn", status_obj.get("loggedIn"))
        if connected and logged:
            return data
        if inst.get("qrcode") or inst.get("paircode"):
            return data
        time.sleep(2)
        data = _request("GET", "/instance/status", token=token)
    return data


def apply_send_options(
    body: dict,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    forward: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    view_once: Optional[bool] = None,
) -> dict:
    """Aplica os campos opcionais comuns dos endpoints /send/* no body."""
    opts = {
        "replyid": reply_to,
        "mentions": mentions,
        "delay": delay_ms,
        "readchat": read_chat,
        "readmessages": read_messages,
        "forward": forward,
        "track_source": track_source,
        "track_id": track_id,
        "async": async_send,
        "viewOnce": view_once,
    }
    body.update({k: v for k, v in opts.items() if v is not None})
    return body


def drop_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}
