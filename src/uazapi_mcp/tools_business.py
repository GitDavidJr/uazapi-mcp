"""Tools de WhatsApp Business (perfil comercial, catálogo) e o escape hatch
raw_api_request para qualquer endpoint não coberto por tool dedicada."""

from typing import Any, Literal, Optional

from .core import admin_call, call, drop_none, mcp


@mcp.tool()
def business_profile(
    action: Literal["get", "update", "categories"] = "get",
    jid: Optional[str] = None,
    description: Optional[str] = None,
    address: Optional[str] = None,
    email: Optional[str] = None,
    instance: Optional[str] = None,
) -> Any:
    """Perfil comercial (WhatsApp Business): get (da conta ou de um jid),
    update (description/address/email da conta conectada) e categories
    (categorias de negócio disponíveis)."""
    if action == "categories":
        return call("GET", "/business/get/categories", instance)
    if action == "update":
        body = drop_none({"description": description, "address": address, "email": email})
        return call("POST", "/business/update/profile", instance, json_body=body)
    return call("POST", "/business/get/profile", instance, json_body=drop_none({"jid": jid}))


@mcp.tool()
def catalog(
    action: Literal["list", "info", "show", "hide", "delete"] = "list",
    jid: Optional[str] = None,
    product_id: Optional[str] = None,
    after: Optional[str] = None,
    confirm: bool = False,
    instance: Optional[str] = None,
) -> Any:
    """Catálogo de produtos (WhatsApp Business): list (jid do catálogo; after
    pagina), info (jid + product_id), show/hide (exibe/oculta product_id) e
    delete (product_id; exige confirm=True)."""
    if action == "list":
        if not jid:
            return {"error": True, "status": 0, "body": "list exige jid (do catálogo/perfil)."}
        return call("POST", "/business/catalog/list", instance, json_body=drop_none({"jid": jid, "after": after}))
    if action == "info":
        if not jid or not product_id:
            return {"error": True, "status": 0, "body": "info exige jid e product_id."}
        return call("POST", "/business/catalog/info", instance, json_body={"jid": jid, "id": product_id})
    if not product_id:
        return {"error": True, "status": 0, "body": f"{action} exige product_id."}
    if action == "delete" and not confirm:
        return {"error": True, "status": 0, "body": "delete remove o produto do catálogo — confirme com confirm=True."}
    return call("POST", f"/business/catalog/{action}", instance, json_body={"id": product_id})


@mcp.tool()
def raw_api_request(
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
    path: str,
    body: Optional[dict] = None,
    params: Optional[dict] = None,
    instance: Optional[str] = None,
    use_admin_token: bool = False,
    show_tokens: bool = False,
) -> Any:
    """Chama QUALQUER endpoint da UAZAPI diretamente (escape hatch para o que
    não tem tool dedicada). Docs: https://docs.uazapi.com

    path: ex "/chat/find". use_admin_token: usa o admintoken em vez do token
    de instância. instance: resolve o token da instância como nas outras tools.
    """
    if not path.startswith("/"):
        path = "/" + path
    if use_admin_token:
        return admin_call(method, path, params=params, json_body=body, show_tokens=show_tokens)
    return call(method, path, instance, params=params, json_body=body, show_tokens=show_tokens)
