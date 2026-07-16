"""Tools de ações em mensagens: buscar, reagir, editar, apagar, fixar, marcar
como lida, baixar mídia e fila async de envio direto."""

from typing import Any, Literal, Optional

from .core import call, drop_none, mcp


@mcp.tool()
def find_messages(
    chat_id: Optional[str] = None,
    message_id: Optional[str] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    instance: Optional[str] = None,
) -> Any:
    """Busca mensagens já sincronizadas (histórico/contexto de um chat).

    chat_id: JID do chat/grupo (ex "5511999999999@s.whatsapp.net" ou "...@g.us").
    message_id: busca uma mensagem exata. track_source/track_id: filtra por
    rastreamento. offset 0 = mais recentes.
    """
    body = drop_none(
        {
            "chatid": chat_id,
            "id": message_id,
            "track_source": track_source,
            "track_id": track_id,
            "limit": limit,
            "offset": offset,
        }
    )
    return call("POST", "/message/find", instance, json_body=body)


@mcp.tool()
def sync_history(
    chat_id: str,
    count: int = 20,
    anchor_message_id: Optional[str] = None,
    mode: Literal["history", "exact"] = "history",
    instance: Optional[str] = None,
) -> Any:
    """Pede ao WhatsApp mensagens antigas de um chat que ainda não estão no
    banco local (quando find_messages não tem contexto suficiente).

    mode=history: busca para trás a partir da âncora (anchor_message_id) ou da
    mais antiga conhecida. mode=exact: recarrega exatamente a mensagem informada.
    """
    body = drop_none(
        {"number": chat_id, "mode": mode, "count": count, "messageid": anchor_message_id}
    )
    return call("POST", "/message/history-sync", instance, json_body=body)


@mcp.tool()
def react_to_message(
    chat_id: str, message_id: str, emoji: str, instance: Optional[str] = None
) -> Any:
    """Reage a uma mensagem com um emoji (string vazia remove a reação)."""
    return call(
        "POST",
        "/message/react",
        instance,
        json_body={"number": chat_id, "id": message_id, "text": emoji},
    )


@mcp.tool()
def edit_message(message_id: str, new_text: str, instance: Optional[str] = None) -> Any:
    """Edita o texto de uma mensagem já enviada (recurso nativo do WhatsApp)."""
    return call("POST", "/message/edit", instance, json_body={"id": message_id, "text": new_text})


@mcp.tool()
def delete_message(message_id: str, instance: Optional[str] = None) -> Any:
    """Apaga uma mensagem PARA TODOS na conversa."""
    return call("POST", "/message/delete", instance, json_body={"id": message_id})


@mcp.tool()
def pin_message(
    message_id: str,
    pin: bool = True,
    duration_days: Literal[1, 7, 30] = 30,
    instance: Optional[str] = None,
) -> Any:
    """Fixa (pin=True) ou desafixa (pin=False) uma mensagem no chat.
    duration_days: 1, 7 ou 30."""
    return call(
        "POST",
        "/message/pin",
        instance,
        json_body={"id": message_id, "pin": pin, "duration": duration_days},
    )


@mcp.tool()
def mark_messages_read(message_ids: list[str], instance: Optional[str] = None) -> Any:
    """Marca uma ou mais mensagens como lidas (confirmação azul, se ativada)."""
    return call("POST", "/message/markread", instance, json_body={"id": message_ids})


@mcp.tool()
def download_message_media(
    message_id: str,
    transcribe: bool = False,
    generate_mp3: bool = True,
    download_quoted: bool = False,
    openai_apikey: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Baixa o arquivo de uma mensagem de mídia e retorna a URL pública.

    transcribe=True: transcreve áudio para texto (usa a chave OpenAI da
    instância ou openai_apikey). download_quoted=True: baixa a mídia da
    mensagem citada.
    """
    body = drop_none(
        {
            "id": message_id,
            "return_link": True,
            "return_base64": False,
            "generate_mp3": generate_mp3,
            "transcribe": transcribe or None,
            "openai_apikey": openai_apikey,
            "download_quoted": download_quoted or None,
        }
    )
    return call("POST", "/message/download", instance, json_body=body, timeout=120)


@mcp.tool()
def async_queue(
    action: Literal["status", "clear"] = "status", instance: Optional[str] = None
) -> Any:
    """Consulta (status) ou cancela (clear) a fila interna de envios feitos com
    async_send=True. Não afeta campanhas do sender."""
    if action == "clear":
        return call("DELETE", "/message/async", instance)
    return call("GET", "/message/async", instance)


@mcp.tool()
def set_async_delay(
    min_seconds: int, max_seconds: int, instance: Optional[str] = None
) -> Any:
    """Configura o intervalo (aleatório entre min e max, em segundos) entre
    mensagens da fila async de envio direto."""
    return call(
        "POST",
        "/instance/updateDelaySettings",
        instance,
        json_body={"msg_delay_min": min_seconds, "msg_delay_max": max_seconds},
    )
