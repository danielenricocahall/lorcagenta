# agent.py
"""
New-style LangChain agent for asking natural language questions
about Lorcana cards stored in CardStore.

- Uses ChatOpenAI + bind_tools (no langchain.agents / AgentExecutor).
- Wraps CardStore.get_cards(...) in a tool the model can call.
"""

from typing import Optional, Dict, Any
import json

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from db.card_store import CardStore

card_store = CardStore.get_card_store("sqlite")


@tool
def search_lorcana_cards(
    color: Optional[str] = None, cost: Optional[int] = None, name: Optional[str] = None
) -> str:
    """
    Search Lorcana cards in the local CardStore.

    Args:
        color: Ink color (e.g. "ruby", "amber", "steel").
        cost: Ink cost (integer).
        name: Full or partial card name (e.g. "Nick Wilde").
        text: Substring to match in rules/ability text if available.

    Returns:
        A JSON string representing the list of matching card dicts.
    """
    filters: Dict[str, Any] = {}

    if color:
        filters["color"] = color.lower()
    if cost:
        filters["cost"] = cost
    if name:
        filters["name"] = name

    cards = card_store.get_cards(**filters)

    return json.dumps(cards, ensure_ascii=False)


class LorcanaAgent:
    def __init__(self, model: str = "gpt-4.1-mini", temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.tools = [search_lorcana_cards]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def invoke(self, question: str) -> str:
        messages = [
            SystemMessage(
                content=(
                    "You are an expert Disney Lorcana card assistant. "
                    "When the user asks about specific cards or card searches, "
                    "use the `search_lorcana_cards` tool to look them up in the local database. "
                    "Explain your answers clearly using the tool results."
                )
            ),
            HumanMessage(content=question),
        ]

        ai_msg = self.llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        if not tool_calls:
            return ai_msg.content

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            if tool_name == "search_lorcana_cards":
                tool_output = search_lorcana_cards.invoke(tool_args)
            else:
                tool_output = f"Unknown tool: {tool_name}"

            messages.append(
                ToolMessage(
                    content=tool_output,
                    tool_call_id=tool_id,
                )
            )

        final_msg = self.llm.invoke(messages)
        return final_msg.content


if __name__ == "__main__":
    agent = LorcanaAgent()

    print(agent.invoke("Find me all Ruby cards that cost more than 7 ink."))
    print(agent.invoke("Show me Nick Wilde cards that are sapphire and cost 3."))
    print(agent.invoke("What Lorcana cards match Belle?"))
