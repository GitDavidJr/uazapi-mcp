"""Tools de tempo real via SSE (/sse): enviar uma pergunta e ESPERAR a resposta
chegar, sem polling — a conexão fica aberta e o WhatsApp empurra o evento."""

import json
import time
from typing import Any, Optional

import httpx

from .core import (
    BASE_URL,
    _digits,
    _request,
    drop_none,
    is_error,
    mcp,
    resolve_token,
    sanitize,
)

MAX_WAIT = 3600


def _slim_message(msg: dict) -> dict:
    keys = (
        "chatid",
        "sender",
        "senderName",
        "text",
        "messageType",
        "messageid",
        "id",
        "isGroup",
        "buttonOrListid",
        "vote",
        "quoted",
        "fileURL",
        "messageTimestamp",
    )
    return {k: msg.get(k) for k in keys if msg.get(k) not in (None, "")}


def _extract_message(evt: Any) -> Optional[dict]:
    """Formatos possíveis: {type, data: {msg}}, {message: {...}} ou a msg direta."""
    if not isinstance(evt, dict):
        return None
    for candidate in (evt.get("data"), evt.get("message"), evt):
        if isinstance(candidate, dict) and ("chatid" in candidate or "messageid" in candidate):
            return candidate
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict) and "chatid" in item:
                    return item
    return None


def _chat_matches(chatid: str, target_digits: str) -> bool:
    cd = _digits(chatid.split("@", 1)[0])
    return bool(cd) and (cd == target_digits or cd.endswith(target_digits) or target_digits.endswith(cd))


def _wait_incoming(
    token: str,
    chat_digits: Optional[str],
    sender_digits: Optional[str],
    timeout_seconds: int,
    after_ms: float,
    send_fn=None,
) -> Any:
    """Abre o SSE, opcionalmente envia algo (send_fn) e espera a 1ª mensagem
    recebida que casa com os filtros."""
    deadline = time.time() + min(timeout_seconds, MAX_WAIT)
    params = {"token": token, "events": "messages"}
    try:
        with httpx.stream(
            "GET",
            f"{BASE_URL}/sse",
            params=params,
            timeout=httpx.Timeout(connect=15, read=min(timeout_seconds, MAX_WAIT) + 10, write=15, pool=15),
        ) as resp:
            if resp.status_code >= 400:
                return {
                    "error": True,
                    "status": resp.status_code,
                    "body": "SSE indisponível neste servidor/token.",
                }
            sent = None
            if send_fn is not None:
                sent = send_fn()
                if is_error(sent):
                    return sent
                after_ms = time.time() * 1000
            data_buf: list[str] = []
            for line in resp.iter_lines():
                if time.time() > deadline:
                    break
                if line == "":
                    if not data_buf:
                        continue
                    payload = "\n".join(data_buf)
                    data_buf = []
                    try:
                        evt = json.loads(payload)
                    except ValueError:
                        continue
                    msg = _extract_message(evt)
                    if not msg or msg.get("fromMe") or msg.get("wasSentByApi"):
                        continue
                    ts = msg.get("messageTimestamp")
                    if isinstance(ts, (int, float)) and ts and ts < after_ms - 15000:
                        continue  # mensagem antiga que estava no buffer
                    if chat_digits and not _chat_matches(str(msg.get("chatid") or ""), chat_digits):
                        continue
                    if sender_digits and not _chat_matches(str(msg.get("sender") or ""), sender_digits):
                        continue
                    result = {"replied": True, "reply": _slim_message(msg)}
                    if sent is not None:
                        result["sent"] = sanitize(sent)
                    return result
                elif line.startswith("data:"):
                    data_buf.append(line[5:].lstrip())
    except httpx.HTTPError:
        pass  # timeout de leitura ou queda da conexão → trata como "sem resposta"
    return {
        "replied": False,
        "timeout_seconds": timeout_seconds,
        "note": (
            "ninguém respondeu dentro do tempo. A resposta ainda pode chegar — "
            "consulte depois com find_messages(chat_id=...)."
        ),
    }


@mcp.tool()
def send_and_wait_reply(
    number: str,
    text: str,
    timeout_seconds: int = 120,
    reply_from: Optional[str] = None,
    reply_to: Optional[str] = None,
    delay_ms: Optional[int] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia uma pergunta por texto e ESPERA a resposta chegar (push via SSE,
    sem polling). Retorna a primeira mensagem recebida daquele chat.

    number: contato ou grupo (@g.us). reply_from: em grupos, só aceita resposta
    dessa pessoa (número). timeout_seconds: quanto esperar (máx 3600; clientes
    MCP podem impor timeout menor). Se estourar, a resposta pode ser lida
    depois com find_messages.
    """
    resolved = resolve_token(instance)
    if is_error(resolved):
        return resolved
    token, _ = resolved
    body = drop_none({"number": number, "text": text, "replyid": reply_to, "delay": delay_ms})

    def _send():
        return _request("POST", "/send/text", token=token, json_body=body)

    target_digits = _digits(number.split("@", 1)[0])
    sender_digits = _digits(reply_from.split("@", 1)[0]) if reply_from else None
    return _wait_incoming(
        token,
        chat_digits=target_digits or None,
        sender_digits=sender_digits,
        timeout_seconds=timeout_seconds,
        after_ms=time.time() * 1000,
        send_fn=_send,
    )


@mcp.tool()
def wait_for_message(
    from_chat: Optional[str] = None,
    from_sender: Optional[str] = None,
    timeout_seconds: int = 120,
    instance: Optional[str] = None,
) -> Any:
    """Espera (push via SSE, sem polling) a próxima mensagem RECEBIDA pela
    instância, opcionalmente filtrando por chat (from_chat: número ou JID,
    inclusive grupo) e/ou por remetente (from_sender, útil em grupos)."""
    resolved = resolve_token(instance)
    if is_error(resolved):
        return resolved
    token, _ = resolved
    chat_digits = _digits(from_chat.split("@", 1)[0]) if from_chat else None
    sender_digits = _digits(from_sender.split("@", 1)[0]) if from_sender else None
    return _wait_incoming(
        token,
        chat_digits=chat_digits,
        sender_digits=sender_digits,
        timeout_seconds=timeout_seconds,
        after_ms=time.time() * 1000,
    )
