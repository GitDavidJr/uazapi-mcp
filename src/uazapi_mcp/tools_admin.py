"""Tools de administração do servidor UAZAPI (exigem UAZAPI_ADMIN_TOKEN)."""

from typing import Any, Literal, Optional

from .core import (
    ADMIN_TOKEN,
    BASE_URL,
    ENV_TOKEN,
    admin_call,
    all_instances,
    drop_none,
    fetch_connection,
    get_default_ref,
    invalidate_instances_cache,
    is_error,
    mcp,
    sanitize,
    save_qr_png,
    slim_instance,
)


@mcp.tool()
def uazapi_info() -> Any:
    """Mostra a configuração atual do MCP: servidor, modo (admin/instância única),
    instância padrão em uso e um resumo das instâncias (se houver admin token).
    Boa primeira chamada para se orientar."""
    info: dict = {
        "base_url": BASE_URL,
        "admin_mode": bool(ADMIN_TOKEN),
        "single_instance_token": bool(ENV_TOKEN),
        "default_instance": get_default_ref()
        or ("<UAZAPI_TOKEN do ambiente>" if ENV_TOKEN else None),
    }
    if ADMIN_TOKEN:
        instances = all_instances()
        if is_error(instances):
            info["instances_error"] = instances
        else:
            by_status: dict = {}
            for i in instances:
                by_status[i.get("status", "?")] = by_status.get(i.get("status", "?"), 0) + 1
            info["total_instances"] = len(instances)
            info["instances_by_status"] = by_status
    return info


@mcp.tool()
def admin_list_instances(
    search: Optional[str] = None,
    status: Optional[str] = None,
    show_tokens: bool = False,
    full: bool = False,
    force_refresh: bool = False,
) -> Any:
    """Lista todas as instâncias do servidor UAZAPI (requer admin token).

    search: filtra por nome, número (owner), profileName ou id (contém).
    status: filtra por status (connected, disconnected, connecting, hibernated).
    show_tokens: True para exibir os tokens completos (padrão: mascarados).
    full: True para retornar todos os campos de cada instância.
    """
    instances = all_instances(force=force_refresh)
    if is_error(instances):
        return instances
    result = instances
    if search:
        s = search.lower()
        result = [
            i
            for i in result
            if s in (i.get("name") or "").lower()
            or s in (i.get("profileName") or "").lower()
            or s in (i.get("owner") or "").lower()
            or s in (i.get("id") or "").lower()
        ]
    if status:
        result = [i for i in result if (i.get("status") or "").lower() == status.lower()]
    if full:
        return {"count": len(result), "instances": sanitize(result, show_tokens=show_tokens)}
    return {
        "count": len(result),
        "instances": [slim_instance(i, show_token=show_tokens) for i in result],
    }


@mcp.tool()
def admin_create_instance(
    name: str,
    admin_field_01: Optional[str] = None,
    admin_field_02: Optional[str] = None,
    connect_now: bool = False,
    show_token: bool = False,
) -> Any:
    """Cria uma nova instância de WhatsApp no servidor (requer admin token).

    A instância nasce desconectada. Com connect_now=True já inicia a conexão e
    salva o QR code em arquivo PNG (use send_connection_qr para mandar o QR a
    alguém, ou get_qr_code/wait_for_connection para acompanhar).
    show_token: True para retornar o token completo da nova instância.
    """
    body = drop_none(
        {"name": name, "adminField01": admin_field_01, "adminField02": admin_field_02}
    )
    data = admin_call("POST", "/instance/create", json_body=body, show_tokens=show_token)
    if is_error(data):
        return data
    invalidate_instances_cache()
    raw = data if isinstance(data, dict) else {}
    token = None
    # token vem mascarado em `data` se show_token=False; busca o cru de novo
    if connect_now:
        fresh = all_instances(force=True)
        if not is_error(fresh):
            created = next(
                (i for i in fresh if i.get("id") == (raw.get("instance") or {}).get("id")),
                None,
            )
            token = (created or {}).get("token")
        if token:
            conn = fetch_connection(token)
            if not is_error(conn):
                inst = conn.get("instance") or {}
                if inst.get("qrcode"):
                    data["qr_file"] = save_qr_png(inst["qrcode"], inst.get("name") or name)
                    data["note"] = (
                        "QR salvo em arquivo (expira em ~1 min). Use send_connection_qr "
                        "para enviar a um contato/grupo, ou wait_for_connection para aguardar."
                    )
                data["connect"] = sanitize(conn, show_tokens=show_token)
            else:
                data["connect"] = conn
    return data


@mcp.tool()
def admin_update_admin_fields(
    instance: str,
    admin_field_01: Optional[str] = None,
    admin_field_02: Optional[str] = None,
) -> Any:
    """Atualiza os campos administrativos (metadados livres, ex. nome do cliente,
    plano) de uma instância. instance: id, nome ou número (requer admin token)."""
    from .core import match_instance

    inst = match_instance(instance)
    if is_error(inst):
        return inst
    body = drop_none(
        {
            "id": inst.get("id"),
            "adminField01": admin_field_01,
            "adminField02": admin_field_02,
        }
    )
    data = admin_call("POST", "/instance/updateAdminFields", json_body=body)
    invalidate_instances_cache()
    return data


@mcp.tool()
def admin_global_webhook(
    action: Literal["get", "set"] = "get",
    url: Optional[str] = None,
    events: Optional[list[str]] = None,
    exclude_messages: Optional[list[str]] = None,
    add_url_events: Optional[bool] = None,
    add_url_types_messages: Optional[bool] = None,
    include_errors: bool = False,
) -> Any:
    """Vê ou configura o webhook GLOBAL (eventos de TODAS as instâncias; requer admin).

    events: connection, history, messages, messages_update, newsletter_messages,
    call, contacts, presence, groups, labels, chats, chat_labels, blocks, sender.
    exclude_messages: wasSentByApi, wasNotSentByApi, fromMeYes, fromMeNo,
    isGroupYes, isGroupNo. include_errors: também retorna os últimos 20 erros
    de entrega.
    """
    if action == "set":
        if not url:
            return {"error": True, "status": 0, "body": "action=set exige `url`."}
        body = drop_none(
            {
                "url": url,
                "events": events,
                "excludeMessages": exclude_messages,
                "addUrlEvents": add_url_events,
                "addUrlTypesMessages": add_url_types_messages,
            }
        )
        result = admin_call("POST", "/globalwebhook", json_body=body)
    else:
        result = admin_call("GET", "/globalwebhook")
    if include_errors:
        result = {"webhook": result, "errors": admin_call("GET", "/globalwebhook/errors")}
    return result


@mcp.tool()
def admin_server_action(
    action: Literal["restart", "rotate_admin_token"],
    confirm: bool = False,
) -> Any:
    """Ações críticas do servidor UAZAPI (requer admin token e confirm=True).

    restart: reinicia a aplicação inteira (todas as instâncias reconectam).
    rotate_admin_token: gera um NOVO admin token (o atual para de valer; máx.
    1 rotação a cada 24h). O novo token é retornado em claro — atualize
    UAZAPI_ADMIN_TOKEN na config do MCP imediatamente.
    """
    if not confirm:
        return {
            "error": True,
            "status": 0,
            "body": f"ação '{action}' afeta o servidor todo. Chame de novo com confirm=True.",
        }
    if action == "restart":
        return admin_call("POST", "/admin/restart")
    # rotate: NÃO mascarar, senão o novo token se perde para sempre
    from .core import _request

    data = _request("POST", "/admin/token/rotate", admin=True)
    if not is_error(data):
        data["warning"] = (
            "Guarde o admin_token acima AGORA e atualize UAZAPI_ADMIN_TOKEN na "
            "configuração deste MCP — o token antigo já parou de funcionar."
        )
    return data
