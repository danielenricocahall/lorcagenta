# lorcana_agent.py (for example)

from typing import Optional, Dict, Any, List
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

    Returns:
        A JSON string representing the list of matching card dicts.
    """
    filters: Dict[str, Any] = {}

    if color:
        filters["color"] = color.lower()
    if cost is not None:
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
        """Original 'chatty' mode: returns a natural language answer."""
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

    def search_cards(self, question: str) -> List[Dict[str, Any]]:
        """
        Run the LLM with tools and return the *raw cards* from any
        `search_lorcana_cards` tool calls, as a list of dicts.

        This is what the Dash app will use.
        """
        messages = [
            SystemMessage(
                content=(
                    "You are an expert Disney Lorcana card assistant. "
                    "When the user asks about specific cards or card searches, "
                    "use the `search_lorcana_cards` tool to look them up in the local database. "
                    "Respond by calling the tool with appropriate arguments."
                )
            ),
            HumanMessage(content=question),
        ]

        ai_msg = self.llm_with_tools.invoke(messages)
        tool_calls = getattr(ai_msg, "tool_calls", []) or []

        all_cards: List[Dict[str, Any]] = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == "search_lorcana_cards":
                tool_output = search_lorcana_cards.invoke(tool_args)
                try:
                    cards = json.loads(tool_output)
                    if isinstance(cards, list):
                        all_cards.extend(cards)
                except json.JSONDecodeError:
                    # If something weird happens, just ignore this tool call.
                    continue

        return all_cards
