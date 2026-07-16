"""Entry point do uazapi-mcp: importa todos os módulos de tools (o import
registra as tools no FastMCP) e sobe o servidor stdio."""

from .core import mcp
from . import (  # noqa: F401  — imports registram as @mcp.tool()
    tools_admin,
    tools_instance,
    tools_send,
    tools_messages,
    tools_chats,
    tools_groups,
    tools_newsletter,
    tools_campaigns,
    tools_business,
    tools_events,
)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
