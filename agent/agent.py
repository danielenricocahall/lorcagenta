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

    def search_cards(
        self, question: str, max_iterations: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Run the LLM with tools in multiple rounds and return the *raw cards* from any
        `search_lorcana_cards` tool calls, as a list of dicts.

        The model can:
        - Call `search_lorcana_cards` multiple times in a single response.
        - Ask for more tool calls in later iterations after seeing previous results.

        We stop when the model stops calling tools or we hit `max_iterations`.
        """
        messages = [
            SystemMessage(
                content=(
                    "You are an expert Disney Lorcana card assistant. "
                    "The user will ask for cards using natural language. "
                    "Your ONLY job is to decide which `search_lorcana_cards` tool calls to make.\n\n"
                    "Rules:\n"
                    "1. Always respond by calling `search_lorcana_cards` with appropriate arguments.\n"
                    "   - Use `color`, `cost`, and/or `name` when helpful.\n"
                    "2. You MAY call `search_lorcana_cards` multiple times in a single response, "
                    "   for example when the user asks for cards related to a Disney movie: "
                    "   call the tool once per relevant character (Belle, Beast, Lumiere, Cogsworth, etc.).\n"
                    "3. After you have no more useful searches to perform, respond with a normal assistant "
                    "   message with *no* tool calls. That means you're done.\n"
                    "4. Do NOT explain results or talk to the user in this mode; just decide what to search.\n"
                )
            ),
            HumanMessage(content=question),
        ]

        all_cards: List[Dict[str, Any]] = []
        seen_ids = (
            set()
        )  # avoid duplicates if your card dicts have a stable 'id' or similar

        for _ in range(max_iterations):
            ai_msg = self.llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            tool_calls = getattr(ai_msg, "tool_calls", []) or []
            if not tool_calls:
                # Model didn't call any tools this round -> we're done
                break

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                print(f"Invoking tool {tool_name} with args {tool_args}")

                if tool_name == "search_lorcana_cards":
                    tool_output = search_lorcana_cards.invoke(tool_args)
                else:
                    tool_output = json.dumps(
                        {"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False
                    )

                # Send tool result back to the model so it can decide if more searches are needed
                messages.append(
                    ToolMessage(
                        content=tool_output,
                        tool_call_id=tool_id,
                    )
                )

                cards = json.loads(tool_output)

                for card in cards:
                    card_id = card.get("id")
                    if card_id not in seen_ids:
                        seen_ids.add(card_id)
                        all_cards.append(card)

        return all_cards
