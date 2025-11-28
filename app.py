# app.py

from dash import Dash, html, dcc, Input, Output, State

from agent.agent import LorcanaAgent

# Instantiate the agent once and reuse it
agent = LorcanaAgent()

app = Dash(__name__)
server = app.server  # in case you want to deploy with gunicorn, etc.

app.layout = html.Div(
    style={
        "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "padding": "24px",
        "maxWidth": "960px",
        "margin": "0 auto",
    },
    children=[
        html.H1("Lorcana Card Search", style={"marginBottom": "8px"}),
        html.P(
            "Type a natural-language query (e.g. "
            '"Find me all Ruby cards that cost more than 7 ink" or '
            '"Show me Nick Wilde cards that are sapphire and cost 3").',
            style={"marginBottom": "16px", "color": "#555"},
        ),
        html.Div(
            style={
                "display": "flex",
                "gap": "8px",
                "marginBottom": "16px",
            },
            children=[
                dcc.Input(
                    id="search-input",
                    type="text",
                    placeholder="Search for Lorcana cards...",
                    style={
                        "flex": "1",
                        "padding": "8px 12px",
                        "borderRadius": "8px",
                        "border": "1px solid #ccc",
                        "fontSize": "16px",
                    },
                ),
                html.Button(
                    "Search",
                    id="search-button",
                    n_clicks=0,
                    style={
                        "padding": "8px 16px",
                        "borderRadius": "8px",
                        "border": "none",
                        "backgroundColor": "#2563eb",
                        "color": "white",
                        "fontSize": "16px",
                        "cursor": "pointer",
                    },
                ),
            ],
        ),
        html.Div(
            id="status-message",
            style={"marginBottom": "16px", "color": "#444"},
        ),
        html.Div(
            id="results",
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "16px",
            },
        ),
    ],
)


@app.callback(
    Output("results", "children"),
    Output("status-message", "children"),
    Input("search-button", "n_clicks"),
    State("search-input", "value"),
    prevent_initial_call=True,
)
def run_lorcana_search(n_clicks, query):
    if not query or not query.strip():
        return [], "Please enter a search query."

    try:
        cards = agent.search_cards(query.strip())
    except Exception as e:
        # You might want to log this in a real app
        return [], f"Error while querying the Lorcana agent: {e}"

    if not cards:
        return [], "No cards found for that query."

    # Build a simple grid of card images
    card_divs = []
    for card in cards:
        image_url = card.get("image")
        name = card.get("name", "Unknown card")
        color = card.get("color", "")
        cost = card.get("cost", "")

        # Only render if there's an image URL
        if not image_url:
            continue

        card_divs.append(
            html.Div(
                style={
                    "width": "200px",
                    "borderRadius": "12px",
                    "border": "1px solid #ddd",
                    "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.08)",
                    "overflow": "hidden",
                    "backgroundColor": "white",
                },
                children=[
                    html.Img(
                        src=image_url,
                        alt=name,
                        style={
                            "width": "100%",
                            "display": "block",
                        },
                    ),
                    html.Div(
                        style={"padding": "8px 10px"},
                        children=[
                            html.Div(
                                name,
                                style={
                                    "fontWeight": "600",
                                    "fontSize": "14px",
                                    "marginBottom": "4px",
                                },
                            ),
                            html.Div(
                                f"{color.capitalize()} • Cost: {cost}"
                                if color or cost != ""
                                else "",
                                style={
                                    "fontSize": "12px",
                                    "color": "#666",
                                },
                            ),
                        ],
                    ),
                ],
            )
        )

    status = f"Showing {len(card_divs)} card(s)."
    return card_divs, status


if __name__ == "__main__":
    app.run(debug=True)
