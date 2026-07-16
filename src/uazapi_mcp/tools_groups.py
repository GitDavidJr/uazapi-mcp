"""Tools de grupos e comunidades do WhatsApp."""

from typing import Any, Literal, Optional

from .core import call, drop_none, mcp


@mcp.tool()
def list_groups(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    force_refresh: bool = False,
    include_participants: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Lista os grupos da instância (IDs @g.us), com busca por nome e paginação.

    force_refresh: ignora cache e busca direto do WhatsApp.
    include_participants: inclui participantes (resposta bem maior).
    """
    body = drop_none(
        {
            "search": search,
            "limit": limit,
            "offset": offset,
            "force": force_refresh or None,
            "noParticipants": not include_participants,
        }
    )
    return call("POST", "/group/list", instance, json_body=body)


@mcp.tool()
def group_info(
    group_id: str,
    get_invite_link: bool = False,
    get_pending_requests: bool = False,
    force_refresh: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Detalhes de um grupo: nome, descrição, participantes, admins,
    configurações; opcionalmente link de convite e solicitações pendentes.

    group_id: JID do grupo, ex "120363153742561022@g.us" (ver list_groups).
    """
    return call(
        "POST",
        "/group/info",
        instance,
        json_body={
            "groupjid": group_id,
            "getInviteLink": get_invite_link,
            "getRequestsParticipants": get_pending_requests,
            "force": force_refresh,
        },
    )


@mcp.tool()
def create_group(name: str, participants: list[str], instance: Optional[str] = None) -> Any:
    """Cria um grupo com os participantes iniciais (números internacionais,
    ex ["5511999999999", ...]). Mínimo 1 participante além do criador."""
    return call(
        "POST",
        "/group/create",
        instance,
        json_body={"name": name, "participants": participants},
    )


@mcp.tool()
def update_group(
    group_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    image: Optional[str] = None,
    only_admins_send: Optional[bool] = None,
    only_admins_edit: Optional[bool] = None,
    join_approval_required: Optional[bool] = None,
    who_can_add_members: Optional[Literal["admin_add", "all_member_add"]] = None,
    ephemeral_duration: Optional[Literal["off", "1d", "7d", "90d"]] = None,
    instance: Optional[str] = None,
) -> Any:
    """Atualiza configurações de um grupo (só os campos informados; requer admin
    do grupo): nome, descrição, imagem (URL/base64/"remove"), só admins enviam
    (announce), só admins editam (locked), aprovação de entrada, quem pode
    adicionar membros e mensagens temporárias."""
    results: dict = {}
    if name is not None:
        results["name"] = call("POST", "/group/updateName", instance, json_body={"groupjid": group_id, "name": name})
    if description is not None:
        results["description"] = call(
            "POST", "/group/updateDescription", instance, json_body={"groupjid": group_id, "description": description}
        )
    if image is not None:
        results["image"] = call("POST", "/group/updateImage", instance, json_body={"groupjid": group_id, "image": image})
    if only_admins_send is not None:
        results["announce"] = call(
            "POST", "/group/updateAnnounce", instance, json_body={"groupjid": group_id, "announce": only_admins_send}
        )
    if only_admins_edit is not None:
        results["locked"] = call(
            "POST", "/group/updateLocked", instance, json_body={"groupjid": group_id, "locked": only_admins_edit}
        )
    if join_approval_required is not None:
        results["join_approval"] = call(
            "POST",
            "/group/updateJoinApproval",
            instance,
            json_body={"groupjid": group_id, "IsJoinApprovalRequired": join_approval_required},
        )
    if who_can_add_members is not None:
        results["member_add_mode"] = call(
            "POST",
            "/group/updateMemberAddMode",
            instance,
            json_body={"groupjid": group_id, "MemberAddMode": who_can_add_members},
        )
    if ephemeral_duration is not None:
        results["ephemeral"] = call(
            "POST", "/group/ephemeral", instance, json_body={"groupjid": group_id, "duration": ephemeral_duration}
        )
    if not results:
        return {"error": True, "status": 0, "body": "nenhum campo para atualizar foi informado."}
    return results


@mcp.tool()
def group_participants(
    group_id: str,
    action: Literal["add", "remove", "promote", "demote", "approve", "reject"],
    participants: list[str],
    instance: Optional[str] = None,
) -> Any:
    """Gerencia participantes do grupo: add/remove, promote/demote (admin) e
    approve/reject (solicitações pendentes). participants: números ou JIDs."""
    return call(
        "POST",
        "/group/updateParticipants",
        instance,
        json_body={"groupjid": group_id, "action": action, "participants": participants},
    )


@mcp.tool()
def group_invite(
    action: Literal["get_link", "reset_link", "join", "preview"],
    group_id: Optional[str] = None,
    invite_code: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Convites de grupo: get_link/reset_link (do grupo group_id) e
    join/preview (com invite_code ou URL de convite — preview mostra infos sem
    entrar)."""
    if action in ("get_link", "reset_link"):
        if not group_id:
            return {"error": True, "status": 0, "body": f"{action} exige group_id."}
        if action == "get_link":
            return call(
                "POST", "/group/info", instance, json_body={"groupjid": group_id, "getInviteLink": True}
            )
        return call("POST", "/group/resetInviteCode", instance, json_body={"groupjid": group_id})
    if not invite_code:
        return {"error": True, "status": 0, "body": f"{action} exige invite_code (código ou URL)."}
    path = "/group/join" if action == "join" else "/group/inviteInfo"
    return call("POST", path, instance, json_body={"invitecode": invite_code})


@mcp.tool()
def leave_group(group_id: str, confirm: bool = False, instance: Optional[str] = None) -> Any:
    """Sai de um grupo (se for o último admin, o grupo é dissolvido). Requer
    confirm=True."""
    if not confirm:
        return {"error": True, "status": 0, "body": "sair de grupo exige confirm=True."}
    return call("POST", "/group/leave", instance, json_body={"groupjid": group_id})


@mcp.tool()
def community(
    action: Literal["create", "add_groups", "remove_groups"],
    name: Optional[str] = None,
    community_id: Optional[str] = None,
    group_ids: Optional[list[str]] = None,
    instance: Optional[str] = None,
) -> Any:
    """Comunidades: create (name) cria com o grupo de avisos; add_groups/
    remove_groups (community_id + group_ids) vincula/desvincula grupos."""
    if action == "create":
        if not name:
            return {"error": True, "status": 0, "body": "create exige name."}
        return call("POST", "/community/create", instance, json_body={"name": name})
    if not community_id or not group_ids:
        return {"error": True, "status": 0, "body": f"{action} exige community_id e group_ids."}
    return call(
        "POST",
        "/community/editgroups",
        instance,
        json_body={
            "community": community_id,
            "action": "add" if action == "add_groups" else "remove",
            "groupjids": group_ids,
        },
    )
