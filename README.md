# uazapi-mcp

MCP (Model Context Protocol) server para a [UAZAPI](https://docs.uazapi.com) —
API HTTP de WhatsApp. Expõe **a API completa** (132 endpoints cobertos por
**84 tools**) para agentes de IA (Claude Code, Claude Desktop, Cursor, etc.):
do envio de mensagens ao gerenciamento do servidor inteiro — criar instâncias,
conectar por QR code/código de pareamento, webhooks, campanhas de disparo,
grupos, canais, CRM de leads e mais.

Projeto não-oficial, sem afiliação com a UAZAPI. Use conforme os termos de uso
do WhatsApp/UAZAPI.

## Dois modos de operação

| Modo | Variáveis | O que libera |
|---|---|---|
| **Instância única** | `UAZAPI_TOKEN` | As tools operam sempre no mesmo número (comportamento da v0.1) |
| **Admin (multi-instância)** | `UAZAPI_ADMIN_TOKEN` (+ opcional `UAZAPI_TOKEN`) | Tools `admin_*`, e **qualquer tool aceita `instance`** (id, nome, número ou token) para escolher o número na hora |

No modo admin, os tokens de instância são resolvidos **em memória** via
`/instance/all` — nunca vão para disco.

### Instância padrão (o número do dia a dia)

- `use_instance("Comercial")` — define a instância padrão por nome, número ou
  id. Fica salva entre sessões em `~/.config/uazapi-mcp/state.json`
  (**só id/nome/número — jamais o token**).
- Qualquer tool sem o parâmetro `instance` usa a padrão; com `instance="..."`
  usa outra pontualmente, sem trocar a padrão.
- Ordem de resolução: `instance` explícito → instância padrão → `UAZAPI_TOKEN`
  → única instância do servidor.

## Fluxos de destaque

**Criar e conectar um número novo, mandando o QR para alguém escanear:**

1. `admin_create_instance(name="Cliente X", connect_now=True)` — cria e já gera QR
2. `send_connection_qr(to="5511999999999", instance="Cliente X", via_instance="Comercial")`
   — envia a imagem do QR pelo WhatsApp de outra instância conectada (funciona
   para contato ou grupo; `paircode_phone=...` envia código digitável em vez de QR)
3. `wait_for_connection(instance="Cliente X")` — aguarda o scan acontecer

**Perguntar e esperar a resposta (sem polling):** `send_and_wait_reply(number,
text)` envia a pergunta e segura a conexão SSE (`/sse`) aberta até a resposta
daquele chat chegar (ou estourar o timeout). Em grupos, `reply_from` filtra de
quem aceitar resposta. `wait_for_message` é a variante passiva (só esperar).

## Tools (84)

| Categoria | Tools |
|---|---|
| **Visão geral** | `uazapi_info` |
| **Admin** (admin token) | `admin_list_instances`, `admin_create_instance`, `admin_update_admin_fields`, `admin_global_webhook`, `admin_server_action` (restart / rotacionar admin token) |
| **Instância & conexão** | `use_instance`, `instance_status`, `connect_instance`, `get_qr_code`, `send_connection_qr`, `wait_for_connection`, `disconnect_instance`, `delete_instance`, `reset_instance`, `rename_instance`, `set_instance_presence`, `instance_privacy`, `instance_proxy`, `list_proxy_cities`, `check_send_limits`, `update_profile`, `instance_webhook` |
| **Envio** | `send_text`, `send_media`, `send_menu` (botões/lista/enquete), `send_carousel`, `send_contact`, `send_location`, `request_location`, `send_pix_button`, `send_payment_request`, `send_story`, `send_typing` |
| **Tempo real (SSE)** | `send_and_wait_reply`, `wait_for_message` |
| **Mensagens** | `find_messages`, `sync_history`, `react_to_message`, `edit_message`, `delete_message`, `pin_message`, `mark_messages_read`, `download_message_media` (com transcrição opcional), `async_queue`, `set_async_delay` |
| **Chats & contatos** | `find_chats`, `chat_details`, `check_numbers`, `manage_chat` (arquivar/fixar/silenciar/ler/bloquear/temporárias), `delete_chat`, `chat_notes`, `list_contacts`, `manage_contact`, `list_blocked` |
| **CRM & atendimento** | `edit_lead`, `update_lead_fields_map`, `labels`, `set_chat_labels`, `quick_replies`, `manage_call`, `chatwoot_config` |
| **Grupos & comunidades** | `list_groups`, `group_info`, `create_group`, `update_group`, `group_participants`, `group_invite`, `leave_group`, `community` |
| **Canais (newsletters)** | `list_newsletters`, `newsletter_info`, `manage_newsletter`, `update_newsletter`, `newsletter_admins`, `newsletter_posts` |
| **Disparos em massa** | `create_campaign`, `create_campaign_advanced`, `list_campaigns`, `campaign_messages`, `campaign_control` |
| **Business & extras** | `business_profile`, `catalog`, `raw_api_request` (chama qualquer endpoint da API) |

Cobertura: todos os 132 endpoints do
[spec oficial](https://docs.uazapi.com/openapi-bundled.json) têm tool dedicada
ou agrupada; o `/sse` é usado internamente pelas tools de espera; qualquer
caso exótico passa pelo `raw_api_request`.

## Pré-requisitos

- Um servidor UAZAPI (self-hosted ou de um provedor) e:
  - o **admin token** (modo completo), e/ou
  - o **token de uma instância** já conectada (modo single-instance).
- [`uv`](https://docs.astral.sh/uv/) instalado (`brew install uv` no macOS).

## Instalar

### Claude Code

```bash
claude mcp add uazapi --scope user \
  -e UAZAPI_BASE_URL=https://SEU-SERVIDOR-UAZAPI.com \
  -e UAZAPI_ADMIN_TOKEN=SEU_ADMIN_TOKEN \
  -e UAZAPI_TOKEN=TOKEN_DA_INSTANCIA_PADRAO \
  -- uvx --from git+https://github.com/GitDavidJr/uazapi-mcp uazapi-mcp
```

(Use só as variáveis do seu modo: `UAZAPI_ADMIN_TOKEN`, `UAZAPI_TOKEN` ou ambas.)

### Claude Desktop, Cursor, ou qualquer cliente MCP genérico

```json
{
  "mcpServers": {
    "uazapi": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/GitDavidJr/uazapi-mcp", "uazapi-mcp"],
      "env": {
        "UAZAPI_BASE_URL": "https://SEU-SERVIDOR-UAZAPI.com",
        "UAZAPI_ADMIN_TOKEN": "SEU_ADMIN_TOKEN",
        "UAZAPI_TOKEN": "TOKEN_DA_INSTANCIA_PADRAO"
      }
    }
  }
}
```

> São 84 tools — clientes que carregam todos os schemas no contexto (ex.
> Claude Desktop) gastam ~10-15k tokens com isso. No Claude Code as tools são
> carregadas sob demanda.

### Rodando local (dev)

```bash
git clone https://github.com/GitDavidJr/uazapi-mcp.git
cd uazapi-mcp
UAZAPI_BASE_URL=... UAZAPI_ADMIN_TOKEN=... uv run uazapi-mcp
```

### Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `UAZAPI_BASE_URL` | sim | URL do servidor UAZAPI |
| `UAZAPI_ADMIN_TOKEN` | uma das duas | Admin token (modo multi-instância) |
| `UAZAPI_TOKEN` | uma das duas | Token da instância padrão/única |
| `UAZAPI_TIMEOUT` | não | Timeout HTTP em segundos (padrão 60) |
| `UAZAPI_STATE_FILE` | não | Caminho do state file (padrão `~/.config/uazapi-mcp/state.json`) |

## Segurança

- Tokens dão **controle total** dos números (e o admin token, do servidor
  inteiro). Nunca commite esses valores — sempre via variável de ambiente na
  config do cliente MCP.
- As respostas das tools **mascaram tokens por padrão** (`abcd…wxyz`) para não
  vazarem no histórico da conversa; `show_tokens=True` exibe quando você
  realmente precisa copiá-los.
- O state file guarda só id/nome/número da instância padrão — nunca tokens.
- QR codes não entram na conversa em base64: são salvos como PNG em arquivo
  temporário (e enviados direto pela API no `send_connection_qr`).
- Operações destrutivas (deletar instância/chat/campanha, desconectar, sair de
  grupo, restart do servidor, rotação de token) exigem `confirm=True`.

## Testes

`uv run python tests/smoke_test.py` — sobe um servidor UAZAPI falso local e
valida o fluxo completo (admin → use_instance → QR → envios → SSE), sem tocar
em WhatsApp real.

## Licença

MIT — veja [LICENSE](LICENSE).
