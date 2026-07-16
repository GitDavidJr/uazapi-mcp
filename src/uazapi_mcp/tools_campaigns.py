"""Tools de envio em massa (campanhas do sender)."""

from typing import Any, Literal, Optional

from .core import call, drop_none, mcp


@mcp.tool()
def create_campaign(
    numbers: list[str],
    message_type: Literal[
        "text",
        "image",
        "video",
        "videoplay",
        "audio",
        "document",
        "contact",
        "location",
        "list",
        "button",
        "poll",
        "carousel",
    ] = "text",
    text: Optional[str] = None,
    file: Optional[str] = None,
    doc_name: Optional[str] = None,
    link_preview: Optional[bool] = None,
    choices: Optional[list[str]] = None,
    footer_text: Optional[str] = None,
    list_button: Optional[str] = None,
    selectable_count: Optional[int] = None,
    image_button: Optional[str] = None,
    full_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    organization: Optional[str] = None,
    email: Optional[str] = None,
    url: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_name: Optional[str] = None,
    address: Optional[str] = None,
    delay_min_seconds: int = 10,
    delay_max_seconds: int = 30,
    schedule_for: int = 0,
    folder_name: Optional[str] = None,
    info: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Cria uma campanha de disparo em massa: a MESMA mensagem para vários
    números, com delay aleatório entre delay_min/max_seconds (anti-bloqueio).

    schedule_for: 0 = agora; < 100000 = minutos a partir de agora; senão
    timestamp unix em ms. Campos extras conforme message_type (file p/ mídia,
    choices p/ list/button/poll, latitude/longitude p/ location etc.).
    Controle depois com list_campaigns / campaign_control.
    """
    body = drop_none(
        {
            "numbers": numbers,
            "type": message_type,
            "text": text,
            "file": file,
            "docName": doc_name,
            "linkPreview": link_preview,
            "choices": choices,
            "footerText": footer_text,
            "listButton": list_button,
            "selectableCount": selectable_count,
            "imageButton": image_button,
            "fullName": full_name,
            "phoneNumber": phone_number,
            "organization": organization,
            "email": email,
            "url": url,
            "latitude": latitude,
            "longitude": longitude,
            "name": location_name,
            "address": address,
            "delayMin": delay_min_seconds,
            "delayMax": delay_max_seconds,
            "scheduled_for": schedule_for,
            "folder": folder_name,
            "info": info,
        }
    )
    return call("POST", "/sender/simple", instance, json_body=body, timeout=120)


@mcp.tool()
def create_campaign_advanced(
    messages: list[dict],
    delay_min_seconds: int = 10,
    delay_max_seconds: int = 30,
    schedule_for: int = 0,
    info: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Campanha avançada: mensagens DIFERENTES por destinatário.

    messages: lista de {"number": ..., "type": "text|image|...", "text": ...,
    "file": ..., + campos do tipo} (mesmos campos do create_campaign, por item).
    """
    body = drop_none(
        {
            "messages": messages,
            "delayMin": delay_min_seconds,
            "delayMax": delay_max_seconds,
            "scheduled_for": schedule_for,
            "info": info,
        }
    )
    return call("POST", "/sender/advanced", instance, json_body=body, timeout=120)


@mcp.tool()
def list_campaigns(status: Optional[str] = None, instance: Optional[str] = None) -> Any:
    """Lista as campanhas de envio em massa da instância (mais recentes
    primeiro), com progresso e status."""
    params = drop_none({"status": status})
    return call("GET", "/sender/listfolders", instance, params=params)


@mcp.tool()
def campaign_messages(
    folder_id: str,
    status: Optional[Literal["Scheduled", "Sent", "Failed"]] = None,
    limit: int = 100,
    offset: int = 0,
    instance: Optional[str] = None,
) -> Any:
    """Lista as mensagens de uma campanha, com filtro por status
    (Scheduled/Sent/Failed) e paginação."""
    body = drop_none(
        {"folder_id": folder_id, "messageStatus": status, "limit": limit, "offset": offset}
    )
    return call("POST", "/sender/listmessages", instance, json_body=body)


@mcp.tool()
def campaign_control(
    action: Literal["stop", "continue", "delete", "clear_done", "clear_all"],
    folder_id: Optional[str] = None,
    keep_hours: int = 168,
    confirm: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Controla campanhas: stop (pausa), continue (retoma) e delete (apaga
    pendentes) numa campanha (folder_id); clear_done limpa enviadas antigas
    (keep_hours); clear_all APAGA TODA a fila (exige confirm=True)."""
    if action in ("stop", "continue", "delete"):
        if not folder_id:
            return {"error": True, "status": 0, "body": f"{action} exige folder_id."}
        if action == "delete" and not confirm:
            return {"error": True, "status": 0, "body": "delete apaga as mensagens pendentes da campanha — confirme com confirm=True."}
        return call("POST", "/sender/edit", instance, json_body={"folder_id": folder_id, "action": action})
    if action == "clear_done":
        return call("POST", "/sender/cleardone", instance, json_body={"hours": keep_hours})
    if not confirm:
        return {"error": True, "status": 0, "body": "clear_all apaga TODA a fila (pendentes e histórico) — confirme com confirm=True."}
    return call("DELETE", "/sender/clearall", instance)
