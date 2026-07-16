"""Tools de envio de mensagens (/send/* e presença de digitação).

Opções comuns a quase todos os envios: reply_to (id da msg respondida),
mentions ("5511...,5511..."), delay_ms (mostra 'digitando...' antes), read_chat,
read_messages, forward (marca como encaminhada), track_source/track_id
(rastreamento) e async_send (enfileira envio na fila interna).
"""

from typing import Any, Literal, Optional

from .core import apply_send_options, call, drop_none, mcp


@mcp.tool()
def send_text(
    number: str,
    text: str,
    link_preview: bool = False,
    link_preview_title: Optional[str] = None,
    link_preview_description: Optional[str] = None,
    link_preview_image: Optional[str] = None,
    link_preview_large: Optional[bool] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    forward: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia mensagem de texto para contato, grupo (@g.us) ou canal (@newsletter).

    number: telefone internacional (5511999999999) ou JID completo.
    link_preview*: preview automático ou customizado (título/descrição/imagem).
    """
    body = drop_none(
        {
            "number": number,
            "text": text,
            "linkPreview": link_preview or None,
            "linkPreviewTitle": link_preview_title,
            "linkPreviewDescription": link_preview_description,
            "linkPreviewImage": link_preview_image,
            "linkPreviewLarge": link_preview_large,
        }
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        forward=forward,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/text", instance, json_body=body)


@mcp.tool()
def send_media(
    number: str,
    media_type: Literal[
        "image", "video", "videoplay", "document", "audio", "myaudio", "ptt", "ptv", "sticker"
    ],
    file: str,
    caption: Optional[str] = None,
    doc_name: Optional[str] = None,
    thumbnail: Optional[str] = None,
    mimetype: Optional[str] = None,
    view_once: Optional[bool] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    forward: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia mídia: image, video, videoplay, document, audio, myaudio,
    ptt (áudio de voz), ptv (vídeo redondo) ou sticker.

    file: URL pública ou base64. caption: legenda. doc_name: nome do arquivo
    (document). view_once: visualização única.
    """
    body = drop_none(
        {
            "number": number,
            "type": media_type,
            "file": file,
            "text": caption,
            "docName": doc_name,
            "thumbnail": thumbnail,
            "mimetype": mimetype,
        }
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        forward=forward,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
        view_once=view_once,
    )
    return call("POST", "/send/media", instance, json_body=body)


@mcp.tool()
def send_menu(
    number: str,
    menu_type: Literal["button", "list", "poll", "carousel"],
    text: str,
    choices: list[str],
    footer_text: Optional[str] = None,
    list_button: Optional[str] = None,
    selectable_count: Optional[int] = None,
    image_button: Optional[str] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia mensagem interativa: botões, lista, enquete (poll) ou carrossel.

    choices: opções; em listas use "[Título da seção]" para abrir seções.
    selectable_count: nº de opções marcáveis (enquetes). list_button: texto do
    botão que abre a lista. image_button: imagem no topo (type=button).
    """
    body = drop_none(
        {
            "number": number,
            "type": menu_type,
            "text": text,
            "choices": choices,
            "footerText": footer_text,
            "listButton": list_button,
            "selectableCount": selectable_count,
            "imageButton": image_button,
        }
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/menu", instance, json_body=body)


@mcp.tool()
def send_carousel(
    number: str,
    text: str,
    cards: list[dict],
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    forward: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia carrossel de cartões com mídia e botões.

    cards: lista de {"text": str, "image"|"video"|"document": url,
    "buttons": [{"id": str, "text": str, "type": "REPLY"|"URL"|"CALL"|"COPY"}]}.
    """
    body = {"number": number, "text": text, "carousel": cards}
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        forward=forward,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/carousel", instance, json_body=body)


@mcp.tool()
def send_contact(
    number: str,
    full_name: str,
    phone_numbers: str,
    organization: Optional[str] = None,
    email: Optional[str] = None,
    url: Optional[str] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    forward: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia cartão de contato (vCard). phone_numbers: um ou mais números
    separados por vírgula."""
    body = drop_none(
        {
            "number": number,
            "fullName": full_name,
            "phoneNumber": phone_numbers,
            "organization": organization,
            "email": email,
            "url": url,
        }
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        forward=forward,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/contact", instance, json_body=body)


@mcp.tool()
def send_location(
    number: str,
    latitude: float,
    longitude: float,
    name: Optional[str] = None,
    address: Optional[str] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    forward: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia localização geográfica (pin no mapa) com nome e endereço opcionais."""
    body = drop_none(
        {
            "number": number,
            "latitude": latitude,
            "longitude": longitude,
            "name": name,
            "address": address,
        }
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        forward=forward,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/location", instance, json_body=body)


@mcp.tool()
def request_location(
    number: str,
    text: str,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia botão que pede a localização atual do usuário (ele toca e o
    WhatsApp abre a tela de compartilhar localização)."""
    body = {"number": number, "text": text}
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/location-button", instance, json_body=body)


@mcp.tool()
def send_pix_button(
    number: str,
    pix_type: Literal["CPF", "CNPJ", "PHONE", "EMAIL", "EVP"],
    pix_key: str,
    pix_name: Optional[str] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia botão nativo de PIX com a chave informada (o cliente vê recebedor,
    nome e chave para copiar/pagar)."""
    body = drop_none(
        {"number": number, "pixType": pix_type, "pixKey": pix_key, "pixName": pix_name}
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/pix-button", instance, json_body=body)


@mcp.tool()
def send_payment_request(
    number: str,
    amount: float,
    title: Optional[str] = None,
    text: Optional[str] = None,
    footer: Optional[str] = None,
    item_name: Optional[str] = None,
    invoice_number: Optional[str] = None,
    pix_key: Optional[str] = None,
    pix_type: Optional[Literal["CPF", "CNPJ", "PHONE", "EMAIL", "EVP"]] = None,
    pix_name: Optional[str] = None,
    payment_link: Optional[str] = None,
    file_url: Optional[str] = None,
    file_name: Optional[str] = None,
    boleto_code: Optional[str] = None,
    reply_to: Optional[str] = None,
    mentions: Optional[str] = None,
    delay_ms: Optional[int] = None,
    read_chat: Optional[bool] = None,
    read_messages: Optional[bool] = None,
    track_source: Optional[str] = None,
    track_id: Optional[str] = None,
    async_send: Optional[bool] = None,
    instance: Optional[str] = None,
) -> Any:
    """Envia solicitação de pagamento com botão nativo "Revisar e pagar":
    PIX, boleto (boleto_code = linha digitável, file_url = PDF), link de
    checkout homologado, tudo combinável. amount em BRL."""
    body = drop_none(
        {
            "number": number,
            "amount": amount,
            "title": title,
            "text": text,
            "footer": footer,
            "itemName": item_name,
            "invoiceNumber": invoice_number,
            "pixKey": pix_key,
            "pixType": pix_type,
            "pixName": pix_name,
            "paymentLink": payment_link,
            "fileUrl": file_url,
            "fileName": file_name,
            "boletoCode": boleto_code,
        }
    )
    apply_send_options(
        body,
        reply_to=reply_to,
        mentions=mentions,
        delay_ms=delay_ms,
        read_chat=read_chat,
        read_messages=read_messages,
        track_source=track_source,
        track_id=track_id,
        async_send=async_send,
    )
    return call("POST", "/send/request-payment", instance, json_body=body)


@mcp.tool()
def send_story(
    story_type: Literal["text", "image", "video", "audio", "myaudio", "ptt"],
    text: Optional[str] = None,
    file: Optional[str] = None,
    background_color: Optional[int] = None,
    font: Optional[int] = None,
    mimetype: Optional[str] = None,
    recipients: Optional[list[str]] = None,
    max_recipients: Optional[int] = None,
    instance: Optional[str] = None,
) -> Any:
    """Publica um status/story do WhatsApp (texto com cor/fonte, imagem, vídeo
    ou áudio). recipients: restringe a números específicos; max_recipients:
    limita o alcance."""
    body = drop_none(
        {
            "type": story_type,
            "text": text,
            "file": file,
            "background_color": background_color,
            "font": font,
            "mimetype": mimetype,
            "recipients": recipients,
            "max_recipients": max_recipients,
        }
    )
    return call("POST", "/send/status", instance, json_body=body)


@mcp.tool()
def send_typing(
    number: str,
    presence: Literal["composing", "recording", "paused"] = "composing",
    duration_ms: Optional[int] = None,
    instance: Optional[str] = None,
) -> Any:
    """Mostra 'digitando...' (composing) ou 'gravando áudio...' (recording) no
    chat por até 5 min (duration_ms; padrão do servidor se omitido)."""
    body = drop_none({"number": number, "presence": presence, "delay": duration_ms})
    return call("POST", "/message/presence", instance, json_body=body)
