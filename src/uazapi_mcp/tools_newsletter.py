"""Tools de canais/newsletters do WhatsApp."""

from typing import Any, Literal, Optional

from .core import call, drop_none, mcp


def _nl_ref(newsletter: Optional[str]) -> dict:
    """Aceita id numérico ou JID completo (@newsletter) e monta o body certo."""
    if not newsletter:
        return {}
    if "@" in newsletter:
        return {"jid": newsletter}
    return {"id": newsletter}


@mcp.tool()
def list_newsletters(instance: Optional[str] = None) -> Any:
    """Lista os canais (newsletters) que a conta segue/administra."""
    return call("GET", "/newsletter/list", instance)


@mcp.tool()
def newsletter_info(
    newsletter: Optional[str] = None,
    invite_key: Optional[str] = None,
    search_text: Optional[str] = None,
    country_codes: Optional[list[str]] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Busca canais: por id/JID (newsletter), por chave de convite (invite_key)
    ou pesquisa no diretório público (search_text, country_codes, after para
    paginação)."""
    if search_text is not None or country_codes or after:
        body = drop_none(
            {
                "searchText": search_text,
                "countryCodes": country_codes,
                "limit": limit,
                "after": after,
            }
        )
        return call("POST", "/newsletter/search", instance, json_body=body)
    if invite_key:
        return call("POST", "/newsletter/link", instance, json_body={"key": invite_key})
    if not newsletter:
        return {"error": True, "status": 0, "body": "informe newsletter, invite_key ou search_text."}
    return call("POST", "/newsletter/info", instance, json_body=_nl_ref(newsletter))


@mcp.tool()
def manage_newsletter(
    action: Literal[
        "create", "delete", "follow", "unfollow", "mute", "unmute", "subscribe_live"
    ],
    newsletter: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    picture: Optional[str] = None,
    confirm: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Gerencia canais: create (name, description, picture), delete (confirm),
    follow/unfollow, mute/unmute e subscribe_live (updates temporários).
    newsletter: id numérico ou JID @newsletter."""
    if action == "create":
        if not name:
            return {"error": True, "status": 0, "body": "create exige name."}
        body = drop_none({"name": name, "description": description, "picture": picture})
        return call("POST", "/newsletter/create", instance, json_body=body)
    if not newsletter:
        return {"error": True, "status": 0, "body": f"{action} exige newsletter (id ou JID)."}
    ref = _nl_ref(newsletter)
    if action == "delete":
        if not confirm:
            return {"error": True, "status": 0, "body": "deletar canal exige confirm=True."}
        return call("POST", "/newsletter/delete", instance, json_body=ref)
    paths = {
        "follow": "/newsletter/follow",
        "unfollow": "/newsletter/unfollow",
        "mute": "/newsletter/mute",
        "unmute": "/newsletter/unmute",
        "subscribe_live": "/newsletter/subscribe",
    }
    return call("POST", paths[action], instance, json_body=ref)


@mcp.tool()
def update_newsletter(
    newsletter: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    picture: Optional[str] = None,
    reaction_codes: Optional[Literal["all", "basic", "none", "blocklist"]] = None,
    transfer_owner_to: Optional[str] = None,
    quit_admin: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Atualiza um canal (só os campos informados): nome, descrição, foto,
    reações permitidas (reaction_codes) e transferência de dono
    (transfer_owner_to: telefone; quit_admin sai de admin depois)."""
    ref = _nl_ref(newsletter)
    results: dict = {}
    if name is not None:
        results["name"] = call("POST", "/newsletter/name", instance, json_body={**ref, "name": name})
    if description is not None:
        results["description"] = call(
            "POST", "/newsletter/description", instance, json_body={**ref, "description": description}
        )
    if picture is not None:
        results["picture"] = call("POST", "/newsletter/picture", instance, json_body={**ref, "picture": picture})
    if reaction_codes is not None:
        results["settings"] = call(
            "POST", "/newsletter/settings", instance, json_body={**ref, "reactionCodes": reaction_codes}
        )
    if transfer_owner_to is not None:
        results["owner_transfer"] = call(
            "POST",
            "/newsletter/owner/transfer",
            instance,
            json_body={**ref, "phone": transfer_owner_to, "quitAdmin": quit_admin},
        )
    if not results:
        return {"error": True, "status": 0, "body": "nenhum campo para atualizar foi informado."}
    return results


@mcp.tool()
def newsletter_admins(
    action: Literal["invite", "remove", "revoke", "accept"],
    newsletter: str,
    phone: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Admins do canal: invite/remove/revoke (exigem phone) e accept (aceita
    convite de admin recebido pela própria conta)."""
    ref = _nl_ref(newsletter)
    if action == "accept":
        return call("POST", "/newsletter/admin/accept", instance, json_body=ref)
    if not phone:
        return {"error": True, "status": 0, "body": f"{action} exige phone."}
    return call("POST", f"/newsletter/admin/{action}", instance, json_body={**ref, "phone": phone})


@mcp.tool()
def newsletter_posts(
    newsletter: str,
    action: Literal["list", "updates", "react", "edit", "delete", "mark_viewed"] = "list",
    count: Optional[int] = None,
    before_id: Optional[int] = None,
    after_id: Optional[int] = None,
    since: Optional[int] = None,
    server_id: Optional[int] = None,
    message_id: Optional[str] = None,
    text: Optional[str] = None,
    emoji: Optional[str] = None,
    server_ids: Optional[list[int]] = None,
    instance: Optional[str] = None,
) -> Any:
    """Posts de um canal: list (histórico; before_id pagina para trás), updates
    (views/reações; after_id/since), react (server_id + emoji; vazio remove),
    edit (server_id ou message_id + text), delete (server_id ou message_id) e
    mark_viewed (server_ids)."""
    ref = _nl_ref(newsletter)
    if action == "list":
        return call(
            "POST",
            "/newsletter/messages",
            instance,
            json_body=drop_none({**ref, "count": count, "beforeid": before_id}),
        )
    if action == "updates":
        return call(
            "POST",
            "/newsletter/updates",
            instance,
            json_body=drop_none({**ref, "count": count, "afterid": after_id, "since": since}),
        )
    if action == "react":
        if server_id is None:
            return {"error": True, "status": 0, "body": "react exige server_id."}
        return call(
            "POST",
            "/newsletter/reaction",
            instance,
            json_body={**ref, "serverid": server_id, "reaction": emoji or ""},
        )
    if action == "edit":
        if not text:
            return {"error": True, "status": 0, "body": "edit exige text."}
        return call(
            "POST",
            "/newsletter/messages/edit",
            instance,
            json_body=drop_none({**ref, "serverid": server_id, "messageid": message_id, "text": text}),
        )
    if action == "delete":
        return call(
            "POST",
            "/newsletter/messages/delete",
            instance,
            json_body=drop_none({**ref, "serverid": server_id, "messageid": message_id}),
        )
    if not server_ids:
        return {"error": True, "status": 0, "body": "mark_viewed exige server_ids."}
    return call("POST", "/newsletter/viewed", instance, json_body={**ref, "serverids": server_ids})
