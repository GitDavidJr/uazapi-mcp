# uazapi-mcp

MCP (Model Context Protocol) server para a [UAZAPI](https://docs.uazapi.com) —
a API HTTP de WhatsApp usada por várias plataformas de automação. Expõe uma
instância conectada da UAZAPI como ferramentas para agentes de IA (Claude
Code, Claude Desktop, Cursor, etc.): listar grupos, enviar mensagens e ler o
histórico/contexto de conversas.

Projeto não-oficial, sem afiliação com a UAZAPI. Use conforme os termos de
uso do WhatsApp/UAZAPI.

## Ferramentas disponíveis

| Tool | Descrição |
|---|---|
| `instance_status` | Verifica se a instância está conectada |
| `list_groups` | Lista todos os grupos e seus IDs (`@g.us`) |
| `group_info` | Detalhes de um grupo (nome, descrição, participantes) |
| `send_text` | Envia texto para contato, grupo ou canal |
| `send_media` | Envia imagem, vídeo, áudio ou documento |
| `find_messages` | Busca mensagens já sincronizadas de um chat/grupo (contexto/histórico) |
| `sync_history` | Pede ao WhatsApp para sincronizar mensagens mais antigas de um chat |
| `find_chats` | Busca chats/grupos com filtros (nome, se é grupo, etc.) |

Cobre os endpoints mais usados no dia a dia. A UAZAPI tem 132 endpoints ao
todo (spec completo em `https://docs.uazapi.com/openapi-bundled.json`) —
PRs adicionando mais tools são bem-vindos.

## Pré-requisitos

- Uma instância UAZAPI já criada e **conectada** a um número de WhatsApp
  (self-hosted ou de algum provedor que rode UAZAPI).
- A **URL do servidor** e o **token da instância** — normalmente disponíveis
  no painel da própria UAZAPI, em "Dados da instância" (Server URL / Instance
  Token).
- [`uv`](https://docs.astral.sh/uv/) instalado (`brew install uv` no macOS).

## Instalar

### Claude Code (recomendado — um comando só)

```bash
claude mcp add uazapi --scope user \
  -e UAZAPI_BASE_URL=https://SEU-SERVIDOR-UAZAPI.com \
  -e UAZAPI_TOKEN=SEU_TOKEN_DE_INSTANCIA \
  -- uvx --from git+https://github.com/GitDavidJr/uazapi-mcp uazapi-mcp
```

Isso instala e registra o servidor direto do GitHub, sem precisar clonar nada
manualmente. `--scope user` deixa disponível em qualquer projeto/sessão.

### Claude Desktop, Cursor, ou qualquer cliente MCP genérico

Adicione ao seu arquivo de config MCP (`claude_desktop_config.json`,
`.cursor/mcp.json`, etc.):

```json
{
  "mcpServers": {
    "uazapi": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/GitDavidJr/uazapi-mcp", "uazapi-mcp"],
      "env": {
        "UAZAPI_BASE_URL": "https://SEU-SERVIDOR-UAZAPI.com",
        "UAZAPI_TOKEN": "SEU_TOKEN_DE_INSTANCIA"
      }
    }
  }
}
```

### Rodando local (dev)

```bash
git clone https://github.com/GitDavidJr/uazapi-mcp.git
cd uazapi-mcp
UAZAPI_BASE_URL=https://SEU-SERVIDOR-UAZAPI.com \
UAZAPI_TOKEN=SEU_TOKEN_DE_INSTANCIA \
uv run uazapi-mcp
```

## Segurança

`UAZAPI_TOKEN` dá controle total do número de WhatsApp conectado à instância
(ler mensagens, enviar mensagens, sair de grupos, etc.). Nunca commite esse
valor — sempre passe via variável de ambiente na configuração do seu cliente
MCP.

## Licença

MIT — veja [LICENSE](LICENSE).
