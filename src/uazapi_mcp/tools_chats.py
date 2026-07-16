"""Tools de chats, contatos, CRM (leads), etiquetas, bloqueios, respostas
rápidas, chamadas e integração Chatwoot."""

from typing import Any, Literal, Optional

from .core import call, drop_none, mcp


@mcp.tool()
def find_chats(
    is_group: Optional[bool] = None,
    name_contains: Optional[str] = None,
    archived: Optional[bool] = None,
    label_id: Optional[str] = None,
    lead_status: Optional[str] = None,
    lead_tags: Optional[str] = None,
    ticket_open: Optional[bool] = None,
    assigned_attendant_id: Optional[str] = None,
    operator: Literal["AND", "OR"] = "AND",
    sort: str = "-wa_lastMsgTimestamp",
    limit: int = 20,
    offset: int = 0,
    extra_filters: Optional[dict] = None,
    instance: Optional[str] = None,
) -> Any:
    """Busca chats (conversas e grupos) com filtros, por padrão ordenados pela
    mensagem mais recente.

    is_group: True só grupos, False só conversas. name_contains: nome contém.
    label_id: ID de etiqueta (ver labels). lead_*: filtros de CRM.
    extra_filters: dict com qualquer campo do chat para filtros avançados
    (ex {"wa_isPinned": true}); operadores ~, !~, !=, >=, >, <=, < no valor.
    """
    body: dict = {"operator": operator, "sort": sort, "limit": limit, "offset": offset}
    body.update(
        drop_none(
            {
                "wa_isGroup": is_group,
                "wa_name": name_contains,
                "wa_archived": archived,
                "wa_label": label_id,
                "lead_status": lead_status,
                "lead_tags": lead_tags,
                "lead_isTicketOpen": ticket_open,
                "lead_assignedAttendant_id": assigned_attendant_id,
            }
        )
    )
    if extra_filters:
        body.update(extra_filters)
    return call("POST", "/chat/find", instance, json_body=body)


@mcp.tool()
def chat_details(number: str, preview_image: bool = True, instance: Optional[str] = None) -> Any:
    """Detalhes completos de um contato ou chat (todos os campos, foto de
    perfil, grupos em comum). preview_image: foto menor (mais rápido)."""
    return call(
        "POST",
        "/chat/details",
        instance,
        json_body={"number": number, "preview": preview_image},
    )


@mcp.tool()
def check_numbers(numbers: list[str], instance: Optional[str] = None) -> Any:
    """Verifica se números estão no WhatsApp (vários de uma vez). Retorna JID
    correto, nome verificado e se é grupo/comunidade."""
    return call("POST", "/chat/check", instance, json_body={"numbers": numbers})


@mcp.tool()
def manage_chat(
    number: str,
    action: Literal[
        "archive",
        "unarchive",
        "pin",
        "unpin",
        "mute",
        "unmute",
        "read",
        "unread",
        "block",
        "unblock",
        "ephemeral",
    ],
    mute_hours: Optional[Literal[8, 168, -1]] = None,
    ephemeral_duration: Optional[Literal["off", "1d", "7d", "90d"]] = None,
    instance: Optional[str] = None,
) -> Any:
    """Gerencia um chat: arquivar, fixar, silenciar (mute_hours: 8, 168=1
    semana, -1=sempre), marcar lido/não lido, bloquear contato ou configurar
    mensagens temporárias (ephemeral_duration; só chat privado)."""
    if action in ("archive", "unarchive"):
        return call("POST", "/chat/archive", instance, json_body={"number": number, "archive": action == "archive"})
    if action in ("pin", "unpin"):
        return call("POST", "/chat/pin", instance, json_body={"number": number, "pin": action == "pin"})
    if action in ("mute", "unmute"):
        end = 0 if action == "unmute" else (mute_hours or 8)
        return call("POST", "/chat/mute", instance, json_body={"number": number, "muteEndTime": end})
    if action in ("read", "unread"):
        return call("POST", "/chat/read", instance, json_body={"number": number, "read": action == "read"})
    if action in ("block", "unblock"):
        return call("POST", "/chat/block", instance, json_body={"number": number, "block": action == "block"})
    duration = ephemeral_duration or "off"
    return call("POST", "/chat/ephemeral", instance, json_body={"number": number, "duration": duration})


@mcp.tool()
def delete_chat(
    number: str,
    delete_chat_whatsapp: bool = False,
    clear_chat_whatsapp: bool = False,
    delete_chat_db: bool = False,
    delete_messages_db: bool = False,
    confirm: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Deleta/limpa um chat (qualquer combinação): apagar chat do WhatsApp,
    limpar a conversa no WhatsApp, apagar chat do banco, apagar mensagens do
    banco. Requer confirm=True."""
    if not confirm:
        return {"error": True, "status": 0, "body": "operação destrutiva — chame com confirm=True."}
    body = {
        "number": number,
        "deleteChatWhatsApp": delete_chat_whatsapp,
        "clearChatWhatsApp": clear_chat_whatsapp,
        "deleteChatDB": delete_chat_db,
        "deleteMessagesDB": delete_messages_db,
    }
    return call("POST", "/chat/delete", instance, json_body=body)


@mcp.tool()
def chat_notes(
    number: str,
    action: Literal["get", "set", "refresh"] = "get",
    notes: Optional[str] = None,
    force: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Notas internas do chat (visíveis só para a conta): get lê, set grava
    (notes; string vazia limpa), refresh recarrega do WhatsApp."""
    if action == "set":
        return call("POST", "/chat/notes/edit", instance, json_body={"number": number, "notes": notes or ""})
    if action == "refresh":
        return call("POST", "/chat/notes/refresh", instance, json_body={"number": number, "force": force})
    return call("POST", "/chat/notes", instance, json_body={"number": number})


@mcp.tool()
def list_contacts(
    scope: Literal["address_book", "outside_address_book", "all"] = "address_book",
    limit: int = 100,
    offset: int = 0,
    instance: Optional[str] = None,
) -> Any:
    """Lista os contatos do WhatsApp com paginação. scope: da agenda, fora da
    agenda ou todos os conhecidos."""
    return call(
        "POST",
        "/contacts/list",
        instance,
        json_body={"contactScope": scope, "limit": limit, "offset": offset},
    )


@mcp.tool()
def manage_contact(
    action: Literal["add", "remove"],
    number: str,
    name: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Adiciona (com name) ou remove um contato da agenda do celular."""
    if action == "add":
        if not name:
            return {"error": True, "status": 0, "body": "action=add exige `name`."}
        return call("POST", "/contact/add", instance, json_body={"number": number, "name": name})
    return call("POST", "/contact/remove", instance, json_body={"number": number})


@mcp.tool()
def list_blocked(instance: Optional[str] = None) -> Any:
    """Lista os contatos bloqueados pela instância (bloquear/desbloquear é no
    manage_chat com action block/unblock)."""
    return call("GET", "/chat/blocklist", instance)


@mcp.tool()
def edit_lead(
    chat_id: str,
    name: Optional[str] = None,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[list[str]] = None,
    personal_id: Optional[str] = None,
    ticket_open: Optional[bool] = None,
    assigned_attendant_id: Optional[str] = None,
    kanban_order: Optional[int] = None,
    chatbot_disable_until: Optional[int] = None,
    custom_fields: Optional[dict] = None,
    instance: Optional[str] = None,
) -> Any:
    """Edita o lead/CRM de um chat: nome, email, status no funil, notas, tags,
    CPF/CNPJ (personal_id), ticket aberto/fechado, atendente, posição kanban e
    pausa do chatbot (chatbot_disable_until: timestamp UTC; 0 reativa).

    custom_fields: dict {"01".."20" ou "lead_field01".."lead_field20": valor}.
    """
    body: dict = drop_none(
        {
            "id": chat_id,
            "lead_name": name,
            "lead_fullName": full_name,
            "lead_email": email,
            "lead_status": status,
            "lead_notes": notes,
            "lead_tags": tags,
            "lead_personalid": personal_id,
            "lead_isTicketOpen": ticket_open,
            "lead_assignedAttendant_id": assigned_attendant_id,
            "lead_kanbanOrder": kanban_order,
            "chatbot_disableUntil": chatbot_disable_until,
        }
    )
    for key, value in (custom_fields or {}).items():
        k = str(key)
        if k.isdigit():
            k = f"lead_field{int(k):02d}"
        elif k.startswith("field"):
            k = "lead_" + k
        body[k] = value
    return call("POST", "/chat/editLead", instance, json_body=body)


@mcp.tool()
def update_lead_fields_map(mapping: dict, instance: Optional[str] = None) -> Any:
    """Define os NOMES dos até 20 campos personalizados de lead da instância
    (ex {"01": "CPF", "02": "Plano"}). Os valores por chat vão no edit_lead."""
    body = {}
    for key, value in mapping.items():
        k = str(key)
        if k.isdigit():
            k = f"lead_field{int(k):02d}"
        elif k.startswith("field"):
            k = "lead_" + k
        body[k] = value
    return call("POST", "/instance/updateFieldsMap", instance, json_body=body)


@mcp.tool()
def labels(
    action: Literal["list", "refresh", "create", "edit", "delete"] = "list",
    label_id: Optional[str] = None,
    name: Optional[str] = None,
    color: Optional[int] = None,
    force: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Etiquetas da instância: list, refresh (recarrega do WhatsApp), create
    (name, color 0-19), edit (label_id + name/color), delete (label_id)."""
    if action == "list":
        return call("GET", "/labels", instance)
    if action == "refresh":
        return call("POST", "/labels/refresh", instance, json_body={"force": force})
    if action == "create":
        body = drop_none({"labelid": "new", "name": name, "color": color, "delete": False})
        return call("POST", "/label/edit", instance, json_body=body)
    if not label_id:
        return {"error": True, "status": 0, "body": f"action={action} exige label_id."}
    if action == "delete":
        return call("POST", "/label/edit", instance, json_body={"labelid": label_id, "delete": True})
    body = drop_none({"labelid": label_id, "name": name, "color": color, "delete": False})
    return call("POST", "/label/edit", instance, json_body=body)


@mcp.tool()
def set_chat_labels(
    number: str,
    label_ids: Optional[list[str]] = None,
    add_label_id: Optional[str] = None,
    remove_label_id: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Etiqueta um chat: label_ids substitui o conjunto todo; add/remove_label_id
    mexe em uma só. Use IDs (ver labels), não nomes."""
    body = drop_none(
        {
            "number": number,
            "labelids": label_ids,
            "add_labelid": add_label_id,
            "remove_labelid": remove_label_id,
        }
    )
    return call("POST", "/chat/labels", instance, json_body=body)


@mcp.tool()
def quick_replies(
    action: Literal["list", "create", "update", "delete"] = "list",
    shortcut: Optional[str] = None,
    reply_type: Literal["text", "audio", "myaudio", "ptt", "document", "video", "image"] = "text",
    text: Optional[str] = None,
    file: Optional[str] = None,
    doc_name: Optional[str] = None,
    reply_id: Optional[str] = None,
    on_whatsapp: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Respostas rápidas (templates): list, create (shortcut + text/file),
    update (reply_id), delete (reply_id). on_whatsapp: sincroniza no WhatsApp
    Business (só texto)."""
    if action == "list":
        return call("GET", "/quickreply/showall", instance)
    if action == "delete":
        if not reply_id:
            return {"error": True, "status": 0, "body": "delete exige reply_id."}
        return call(
            "POST",
            "/quickreply/edit",
            instance,
            json_body={"id": reply_id, "delete": True, "shortCut": shortcut or "x", "type": reply_type},
        )
    body = drop_none(
        {
            "id": reply_id if action == "update" else None,
            "shortCut": shortcut,
            "type": reply_type,
            "text": text,
            "file": file,
            "docName": doc_name,
            "onWhatsApp": on_whatsapp or None,
        }
    )
    return call("POST", "/quickreply/edit", instance, json_body=body)


@mcp.tool()
def manage_call(
    action: Literal["make", "reject"],
    number: Optional[str] = None,
    call_id: Optional[str] = None,
    call_duration: Optional[int] = None,
    instance: Optional[str] = None,
) -> Any:
    """Chamadas de voz: make liga para um número (call_duration: encerra após N
    segundos); reject rejeita a chamada recebida (number/call_id opcionais)."""
    if action == "make":
        if not number:
            return {"error": True, "status": 0, "body": "make exige number."}
        return call(
            "POST",
            "/call/make",
            instance,
            json_body=drop_none({"number": number, "call_duration": call_duration}),
        )
    return call(
        "POST", "/call/reject", instance, json_body=drop_none({"number": number, "id": call_id})
    )


@mcp.tool()
def chatwoot_config(
    action: Literal["get", "set"] = "get",
    enabled: Optional[bool] = None,
    url: Optional[str] = None,
    access_token: Optional[str] = None,
    account_id: Optional[int] = None,
    inbox_id: Optional[int] = None,
    ignore_groups: Optional[bool] = None,
    sign_messages: Optional[bool] = None,
    create_new_conversation: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Vê ou configura a integração Chatwoot da instância (set exige enabled,
    url, access_token, account_id e inbox_id)."""
    if action == "get":
        return call("GET", "/chatwoot/config", instance)
    body = drop_none(
        {
            "enabled": enabled,
            "url": url,
            "access_token": access_token,
            "account_id": account_id,
            "inbox_id": inbox_id,
            "ignore_groups": ignore_groups,
            "sign_messages": sign_messages,
            "create_new_conversation": create_new_conversation,
        }
    )
    return call("PUT", "/chatwoot/config", instance, json_body=body)
