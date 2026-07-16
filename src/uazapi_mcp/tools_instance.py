"""Tools de ciclo de vida da instância: conexão (QR/paircode), status, webhook,
perfil, privacidade, proxy e a instância padrão do dia a dia (use_instance)."""

import time
from typing import Any, Literal, Optional

from .core import (
    ADMIN_TOKEN,
    call,
    drop_none,
    fetch_connection,
    get_default_ref,
    invalidate_instances_cache,
    is_error,
    match_instance,
    mcp,
    resolve_token,
    sanitize,
    save_qr_png,
    set_default_ref,
    slim_instance,
)


@mcp.tool()
def use_instance(instance: Optional[str] = None, clear: bool = False) -> Any:
    """Define a instância PADRÃO (o número do dia a dia) usada por todas as tools
    quando o parâmetro `instance` não é passado. Fica salva entre sessões
    (só id/nome/número — nunca o token). Requer admin token.

    instance: id, nome, número ou profileName da instância.
    clear: True para voltar ao comportamento padrão (sem instância fixa).
    """
    if clear:
        set_default_ref(None)
        return {"response": "instância padrão removida."}
    if not instance:
        ref = get_default_ref()
        return {"default_instance": ref or "nenhuma definida"}
    if not ADMIN_TOKEN:
        return {
            "error": True,
            "status": 0,
            "body": "use_instance exige UAZAPI_ADMIN_TOKEN (para resolver e trocar instâncias).",
        }
    inst = match_instance(instance)
    if is_error(inst):
        return inst
    set_default_ref(
        {"id": inst.get("id"), "name": inst.get("name"), "owner": inst.get("owner")}
    )
    return {
        "response": f"instância padrão agora é '{inst.get('name')}' ({inst.get('owner') or 'sem número'}).",
        "instance": slim_instance(inst),
    }


@mcp.tool()
def instance_status(instance: Optional[str] = None) -> Any:
    """Verifica o status de uma instância (conectada, conectando, desconectada).
    instance: id/nome/número (padrão: instância definida em use_instance)."""
    data = call("GET", "/instance/status", instance)
    if isinstance(data, dict) and not is_error(data):
        ref = get_default_ref()
        if ref:
            data["default_instance"] = ref
    return data


@mcp.tool()
def connect_instance(
    instance: Optional[str] = None,
    phone: Optional[str] = None,
    save_qr: bool = True,
) -> Any:
    """Inicia a conexão de uma instância ao WhatsApp.

    Sem `phone`: gera QR code (salvo como PNG local se save_qr=True; use
    send_connection_qr para mandar a alguém). Com `phone` (ex 5511999999999):
    gera código de pareamento digitável em vez de QR. O QR expira em ~1 min —
    gere de novo se precisar.
    """
    resolved = resolve_token(instance)
    if is_error(resolved):
        return resolved
    token, inst = resolved
    data = fetch_connection(token, phone=phone)
    if is_error(data):
        return data
    out = sanitize(data)
    qr = (data.get("instance") or {}).get("qrcode")
    paircode = (data.get("instance") or {}).get("paircode")
    if qr and save_qr:
        label = (inst or {}).get("name") or (data.get("instance") or {}).get("name") or "instance"
        out["qr_file"] = save_qr_png(qr, label)
        out["note"] = (
            "QR salvo em arquivo (expira em ~1 min). Envie com send_connection_qr "
            "ou acompanhe com wait_for_connection."
        )
    if paircode:
        out["note"] = f"Código de pareamento: {paircode} — digite no WhatsApp em Aparelhos conectados > Conectar com número."
    return out


@mcp.tool()
def get_qr_code(instance: Optional[str] = None, refresh: bool = True) -> Any:
    """Pega o QR code atual de conexão da instância e salva como PNG local.

    refresh=True força um novo ciclo de conexão (QR novinho). O arquivo pode
    ser lido/exibido ou enviado via send_connection_qr / send_media.
    """
    resolved = resolve_token(instance)
    if is_error(resolved):
        return resolved
    token, inst = resolved
    if refresh:
        data = fetch_connection(token)
    else:
        from .core import _request

        data = _request("GET", "/instance/status", token=token)
    if is_error(data):
        return data
    instd = data.get("instance") or {}
    status_obj = data.get("status") or {}
    connected = data.get("connected", status_obj.get("connected"))
    logged = data.get("loggedIn", status_obj.get("loggedIn"))
    if connected and logged:
        return {"response": "instância já está conectada — não há QR pendente.", "status": sanitize(data)}
    qr = instd.get("qrcode")
    if not qr:
        return {
            "error": True,
            "status": 0,
            "body": {"message": "QR indisponível no momento", "status": sanitize(data)},
        }
    path = save_qr_png(qr, instd.get("name") or (inst or {}).get("name") or "instance")
    return {
        "qr_file": path,
        "status": instd.get("status"),
        "paircode": instd.get("paircode") or None,
        "note": "QR expira em ~1 min. Reenvie/regenere se demorar para escanear.",
    }


@mcp.tool()
def send_connection_qr(
    to: str,
    instance: Optional[str] = None,
    via_instance: Optional[str] = None,
    caption: Optional[str] = None,
    paircode_phone: Optional[str] = None,
) -> Any:
    """Gera o QR de conexão de uma instância e ENVIA por WhatsApp para um
    contato ou grupo — para a pessoa escanear e conectar o número dela.

    to: número/JID de destino (ex 5511999999999 ou ...@g.us).
    instance: a instância A CONECTAR (padrão: instância padrão).
    via_instance: instância JÁ CONECTADA que envia a mensagem (padrão: a padrão).
    paircode_phone: se informado, envia código de pareamento (texto) em vez de QR.
    """
    target = resolve_token(instance)
    if is_error(target):
        return target
    via = resolve_token(via_instance)
    if is_error(via):
        return via
    target_token, target_inst = target
    via_token, _ = via
    if target_token == via_token:
        return {
            "error": True,
            "status": 0,
            "body": (
                "a instância a conectar e a que envia são a mesma — uma instância "
                "desconectada não consegue enviar o próprio QR. Passe via_instance "
                "com uma instância conectada (ou instance com a que quer conectar)."
            ),
        }

    data = fetch_connection(target_token, phone=paircode_phone)
    if is_error(data):
        return data
    instd = data.get("instance") or {}
    status_obj = data.get("status") or {}
    if data.get("connected", status_obj.get("connected")) and data.get(
        "loggedIn", status_obj.get("loggedIn")
    ):
        return {"response": "essa instância já está conectada — nada a enviar."}

    from .core import _request

    label = instd.get("name") or (target_inst or {}).get("name") or "instância"
    if paircode_phone:
        code = instd.get("paircode")
        if not code:
            return {"error": True, "status": 0, "body": "código de pareamento não veio — tente sem paircode_phone (QR)."}
        text = (
            f"🔗 Código para conectar o WhatsApp ({label}): *{code}*\n\n"
            "No celular: WhatsApp > Aparelhos conectados > Conectar aparelho > "
            "Conectar com número de telefone, e digite o código."
        )
        sent = _request("POST", "/send/text", token=via_token, json_body={"number": to, "text": text})
        return {"paircode": code, "sent": sanitize(sent)}

    qr = instd.get("qrcode")
    if not qr:
        return {"error": True, "status": 0, "body": {"message": "QR não disponível", "status": sanitize(data)}}
    qr_file = save_qr_png(qr, label)
    sent = _request(
        "POST",
        "/send/media",
        token=via_token,
        json_body={
            "number": to,
            "type": "image",
            "file": qr,
            "text": caption
            or (
                f"📱 QR para conectar o WhatsApp ({label}): abra o WhatsApp > "
                "Aparelhos conectados > Conectar aparelho e escaneie. Expira em ~1 minuto!"
            ),
        },
    )
    return {
        "sent": sanitize(sent),
        "qr_file": qr_file,
        "note": "QR expira em ~1 min. Se a pessoa não escanear a tempo, chame send_connection_qr de novo. Use wait_for_connection para saber quando conectar.",
    }


@mcp.tool()
def wait_for_connection(instance: Optional[str] = None, timeout_seconds: int = 60) -> Any:
    """Aguarda (poll) até a instância ficar conectada e logada, ou estourar o
    timeout (máx 120s). Útil logo após alguém escanear o QR."""
    resolved = resolve_token(instance)
    if is_error(resolved):
        return resolved
    token, _ = resolved
    from .core import _request

    deadline = time.time() + min(timeout_seconds, 120)
    last = None
    while time.time() < deadline:
        last = _request("GET", "/instance/status", token=token)
        if is_error(last):
            return last
        status_obj = last.get("status") or {}
        if status_obj.get("connected") and status_obj.get("loggedIn"):
            invalidate_instances_cache()
            return {"connected": True, "status": sanitize(last)}
        time.sleep(3)
    return {"connected": False, "timeout": True, "status": sanitize(last)}


@mcp.tool()
def disconnect_instance(instance: Optional[str] = None, confirm: bool = False) -> Any:
    """Desconecta a instância do WhatsApp (encerra a sessão; reconectar vai
    exigir novo QR). Requer confirm=True."""
    if not confirm:
        return {"error": True, "status": 0, "body": "desconectar exige confirm=True (vai precisar de novo QR para voltar)."}
    data = call("POST", "/instance/disconnect", instance)
    invalidate_instances_cache()
    return data


@mcp.tool()
def delete_instance(instance: str, confirm: bool = False) -> Any:
    """DELETA uma instância do servidor (irreversível). Exige `instance`
    explícita (id/nome/número) e confirm=True."""
    if not confirm:
        return {"error": True, "status": 0, "body": "deletar instância é irreversível — chame com confirm=True."}
    data = call("DELETE", "/instance", instance)
    invalidate_instances_cache()
    ref = get_default_ref()
    if ref and not is_error(data):
        inst = match_instance(instance) if ADMIN_TOKEN else None
        # se a padrão foi deletada, limpa a seleção
        if inst is None or is_error(inst):
            fresh_ids = []
            from .core import all_instances

            fresh = all_instances(force=True)
            if not is_error(fresh):
                fresh_ids = [i.get("id") for i in fresh]
            if ref.get("id") not in fresh_ids:
                set_default_ref(None)
                data = {"result": data, "note": "a instância padrão foi deletada; seleção limpa."}
    return data


@mcp.tool()
def reset_instance(instance: Optional[str] = None) -> Any:
    """Reinicia o runtime da instância (sessão travada, envio não progride).
    Não apaga nada — é um restart controlado só daquela instância."""
    return call("POST", "/instance/reset", instance)


@mcp.tool()
def rename_instance(new_name: str, instance: Optional[str] = None) -> Any:
    """Muda o nome da instância no painel UAZAPI (não mexe no perfil WhatsApp)."""
    data = call("POST", "/instance/updateInstanceName", instance, json_body={"name": new_name})
    invalidate_instances_cache()
    return data


@mcp.tool()
def set_instance_presence(
    presence: Literal["available", "unavailable"], instance: Optional[str] = None
) -> Any:
    """Define a presença global da conta: available (online) ou unavailable."""
    return call("POST", "/instance/presence", instance, json_body={"presence": presence})


@mcp.tool()
def instance_privacy(
    last_seen: Optional[Literal["all", "contacts", "contact_blacklist", "none"]] = None,
    online: Optional[Literal["all", "match_last_seen"]] = None,
    profile_photo: Optional[Literal["all", "contacts", "contact_blacklist", "none"]] = None,
    status_privacy: Optional[Literal["all", "contacts", "contact_blacklist", "none"]] = None,
    read_receipts: Optional[Literal["all", "none"]] = None,
    group_add: Optional[Literal["all", "contacts", "contact_blacklist", "none"]] = None,
    call_add: Optional[Literal["all", "known"]] = None,
    instance: Optional[str] = None,
) -> Any:
    """Vê (sem argumentos) ou altera as configurações de privacidade do WhatsApp:
    visto por último, online, foto de perfil, recado, confirmação de leitura,
    quem pode adicionar a grupos e quem pode ligar."""
    body = drop_none(
        {
            "last": last_seen,
            "online": online,
            "profile": profile_photo,
            "status": status_privacy,
            "readreceipts": read_receipts,
            "groupadd": group_add,
            "calladd": call_add,
        }
    )
    if not body:
        return call("GET", "/instance/privacy", instance)
    return call("POST", "/instance/privacy", instance, json_body=body)


@mcp.tool()
def instance_proxy(
    mode: Optional[Literal["custom", "internal", "none"]] = None,
    proxy_url: Optional[str] = None,
    proxy_fallback: Optional[str] = None,
    confirm_no_proxy: bool = False,
    rotate_now: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Vê (sem argumentos) ou configura o proxy da instância.

    mode=custom exige proxy_url (http/https/socks5); mode=internal usa o proxy
    gerenciado da UAZAPI (rotate_now=True troca o IP); mode=none exige
    confirm_no_proxy=True.
    """
    if mode is None and not rotate_now:
        return call("GET", "/instance/proxy", instance)
    body = drop_none(
        {
            "mode": mode,
            "proxy_url": proxy_url,
            "proxy_fallback": proxy_fallback,
            "confirm_no_proxy": confirm_no_proxy or None,
            "rotate_now": rotate_now or None,
        }
    )
    return call("POST", "/instance/proxy", instance, json_body=body)


@mcp.tool()
def list_proxy_cities(
    country: str = "br",
    state: Optional[str] = None,
    search: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Lista cidades disponíveis do proxy interno gerenciado (para usar nos
    campos proxy_managed_* do connect_instance)."""
    params = drop_none({"country": country, "state": state, "search": search})
    return call("GET", "/proxy-managed/cities", instance, params=params)


@mcp.tool()
def check_send_limits(instance: Optional[str] = None) -> Any:
    """Consulta os limites atuais do WhatsApp para iniciar conversas novas
    (diagnóstico de bloqueios/capping, erro provider_code 463)."""
    return call("GET", "/instance/wa_messages_limits", instance)


@mcp.tool()
def update_profile(
    name: Optional[str] = None,
    image: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Altera o perfil do WhatsApp conectado: nome de exibição e/ou foto.

    image: URL, base64, ou "remove" para tirar a foto.
    """
    if name is None and image is None:
        return {"error": True, "status": 0, "body": "informe name e/ou image."}
    out: dict = {}
    if name is not None:
        out["name"] = call("POST", "/profile/name", instance, json_body={"name": name})
    if image is not None:
        out["image"] = call("POST", "/profile/image", instance, json_body={"image": image})
    return out


@mcp.tool()
def instance_webhook(
    action: Literal["get", "set", "add", "update", "delete"] = "get",
    url: Optional[str] = None,
    events: Optional[list[str]] = None,
    exclude_messages: Optional[list[str]] = None,
    add_url_events: Optional[bool] = None,
    add_url_types_messages: Optional[bool] = None,
    enabled: Optional[bool] = None,
    webhook_id: Optional[str] = None,
    include_errors: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Vê ou configura o(s) webhook(s) DESTA instância.

    action=set: modo simples (um webhook único). add/update/delete: gerencia
    múltiplos webhooks (update/delete exigem webhook_id). events válidos:
    connection, history, messages, messages_update, newsletter_messages, call,
    contacts, presence, groups, labels, chats, chat_labels, blocks, sender.
    include_errors: retorna também os últimos erros de entrega.
    """
    if action == "get":
        result = call("GET", "/webhook", instance)
    else:
        body = drop_none(
            {
                "url": url,
                "events": events,
                "excludeMessages": exclude_messages,
                "addUrlEvents": add_url_events,
                "addUrlTypesMessages": add_url_types_messages,
                "enabled": enabled,
                "id": webhook_id,
                "action": action if action != "set" else None,
            }
        )
        result = call("POST", "/webhook", instance, json_body=body)
    if include_errors:
        result = {"webhook": result, "errors": call("GET", "/webhook/errors", instance)}
    return result
