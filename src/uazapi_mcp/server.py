import os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("UAZAPI_BASE_URL", "").rstrip("/")
TOKEN = os.environ.get("UAZAPI_TOKEN", "")

if not BASE_URL or not TOKEN:
    raise RuntimeError(
        "Defina UAZAPI_BASE_URL e UAZAPI_TOKEN nas variaveis de ambiente "
        "do servidor MCP (token da instancia/numero do WhatsApp)."
    )

mcp = FastMCP("uazapi")


def _request(
    method: str,
    path: str,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> Any:
    headers = {"token": TOKEN, "Accept": "application/json"}
    resp = httpx.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        params=params,
        json=json_body,
        timeout=30,
    )
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}
    if resp.status_code >= 400:
        return {"error": True, "status": resp.status_code, "body": data}
    return data


@mcp.tool()
def instance_status() -> Any:
    """Verifica se a instancia do WhatsApp esta conectada e pronta para uso."""
    return _request("GET", "/instance/status")


@mcp.tool()
def list_groups(force_refresh: bool = False, include_participants: bool = False) -> Any:
    """Lista todos os grupos de WhatsApp da instancia, com seus IDs (formato @g.us).

    force_refresh: ignora o cache e busca dados atualizados direto do WhatsApp.
    include_participants: inclui a lista de participantes de cada grupo na resposta.
    """
    params = {"force": force_refresh, "noparticipants": not include_participants}
    return _request("GET", "/group/list", params=params)


@mcp.tool()
def group_info(group_id: str, get_invite_link: bool = False) -> Any:
    """Detalhes de um grupo especifico: nome, descricao, participantes, admins.

    group_id: JID do grupo, ex "120363153742561022@g.us" (ver list_groups).
    get_invite_link: tambem retorna o link de convite atual do grupo.
    """
    return _request(
        "POST",
        "/group/info",
        json_body={"groupjid": group_id, "getInviteLink": get_invite_link},
    )


@mcp.tool()
def send_text(number: str, text: str, link_preview: bool = False) -> Any:
    """Envia uma mensagem de texto para um contato, grupo ou canal.

    number: telefone em formato internacional (ex 5511999999999), JID de grupo
    (termina em @g.us), de usuario (@s.whatsapp.net) ou de canal (@newsletter).
    link_preview: gera preview automatico se o texto contiver um link.
    """
    return _request(
        "POST",
        "/send/text",
        json_body={"number": number, "text": text, "linkPreview": link_preview},
    )


@mcp.tool()
def send_media(
    number: str,
    media_type: str,
    file: str,
    caption: Optional[str] = None,
    doc_name: Optional[str] = None,
) -> Any:
    """Envia midia (imagem, video, audio ou documento) para um contato, grupo ou canal.

    number: mesmo formato de send_text.
    media_type: um de image, video, videoplay, document, audio, myaudio, ptt, ptv, sticker.
    file: URL publica ou conteudo em base64 do arquivo.
    caption: legenda opcional (campo "text" da API).
    doc_name: nome do arquivo, usado apenas quando media_type="document".
    """
    body = {"number": number, "type": media_type, "file": file}
    if caption is not None:
        body["text"] = caption
    if doc_name is not None:
        body["docName"] = doc_name
    return _request("POST", "/send/media", json_body=body)


@mcp.tool()
def find_messages(chat_id: str, limit: int = 100, offset: int = 0) -> Any:
    """Busca mensagens ja sincronizadas de um chat ou grupo (contexto/historico).

    chat_id: JID do chat/grupo, ex "120363153742561022@g.us" ou "5511999999999@s.whatsapp.net".
    limit: numero maximo de mensagens (padrao 100).
    offset: deslocamento para paginacao (0 = mais recentes).
    """
    return _request(
        "POST",
        "/message/find",
        json_body={"chatid": chat_id, "limit": limit, "offset": offset},
    )


@mcp.tool()
def sync_history(chat_id: str, count: int = 20, anchor_message_id: Optional[str] = None) -> Any:
    """Pede ao WhatsApp para sincronizar mensagens mais antigas de um chat/grupo
    que ainda nao estao disponiveis localmente (util quando find_messages nao
    tem contexto suficiente).

    chat_id: JID completo do chat/grupo.
    count: quantidade desejada de mensagens antigas a sincronizar (1-100).
    anchor_message_id: ID de mensagem de referencia para buscar a partir dela
    (se omitido, sincroniza a partir da mensagem mais antiga conhecida).
    """
    body = {"number": chat_id, "mode": "history", "count": count}
    if anchor_message_id is not None:
        body["messageid"] = anchor_message_id
    return _request("POST", "/message/history-sync", json_body=body)


@mcp.tool()
def find_chats(
    is_group: Optional[bool] = None,
    name_contains: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "-wa_lastMsgTimestamp",
) -> Any:
    """Busca chats (grupos e/ou conversas individuais) com filtros, ordenados
    por padrao pela mensagem mais recente. Util para achar rapidamente um
    grupo ou contato sem listar tudo.

    is_group: True para so grupos, False para so conversas individuais, None para ambos.
    name_contains: filtra pelo nome do chat/contato (contem).
    """
    body: dict = {"limit": limit, "offset": offset, "sort": sort}
    if is_group is not None:
        body["wa_isGroup"] = is_group
    if name_contains is not None:
        body["wa_name"] = name_contains
    return _request("POST", "/chat/find", json_body=body)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
