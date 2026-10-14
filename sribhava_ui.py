import html
import sqlite3

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sribhava Retail", layout="wide")

st.markdown("""
<style>
.stApp {
    background-image:
        radial-gradient(45vmax 45vmax at 12% 18%, rgba(167, 139, 250, 0.32), transparent 62%),
        radial-gradient(50vmax 50vmax at 88% 12%, rgba(34, 211, 238, 0.24), transparent 62%),
        radial-gradient(55vmax 55vmax at 82% 88%, rgba(244, 114, 182, 0.26), transparent 62%),
        radial-gradient(40vmax 40vmax at 14% 90%, rgba(59, 130, 246, 0.26), transparent 62%),
        radial-gradient(1.6px 1.6px at 30px 40px, rgba(255, 255, 255, 0.65), transparent),
        radial-gradient(1.2px 1.2px at 120px 160px, rgba(196, 181, 253, 0.6), transparent),
        radial-gradient(1.4px 1.4px at 210px 90px, rgba(103, 232, 249, 0.55), transparent),
        linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
        linear-gradient(160deg, #0d0a1a 0%, #170f2e 45%, #0b1f33 100%);
    background-size:
        140% 140%, 140% 140%, 140% 140%, 140% 140%,
        180px 180px, 260px 260px, 340px 340px,
        48px 48px, 48px 48px,
        100% 100%;
    background-repeat:
        no-repeat, no-repeat, no-repeat, no-repeat,
        repeat, repeat, repeat,
        repeat, repeat,
        no-repeat;
    background-position:
        0% 0%, 100% 0%, 100% 100%, 0% 100%,
        0 0, 0 0, 0 0,
        0 0, 0 0,
        0 0;
    background-attachment: fixed;
    animation: aurora 40s ease-in-out infinite;
}
@keyframes aurora {
    0% {
        background-position:
            0% 0%, 100% 0%, 100% 100%, 0% 100%,
            0 0, 0 0, 0 0, 0 0, 0 0, 0 0;
    }
    50% {
        background-position:
            45% 30%, 55% 45%, 65% 55%, 35% 70%,
            0 0, 0 0, 0 0, 0 0, 0 0, 0 0;
    }
    100% {
        background-position:
            0% 0%, 100% 0%, 100% 100%, 0% 100%,
            0 0, 0 0, 0 0, 0 0, 0 0, 0 0;
    }
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.25; }
}
@media (prefers-reduced-motion: reduce) {
    .stApp { animation: none; }
    .live::before { animation: none; }
}

header[data-testid="stHeader"] {
    background: transparent;
}
header[data-testid="stHeader"] * {
    color: #c4b5fd !important;
}

.hero { margin-bottom: 8px; }
.hero-title {
    font-size: 2.9rem;
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(90deg, #a78bfa, #f472b6, #22d3ee);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-sub {
    color: #b9a8dd;
    font-size: 1.1rem;
    margin-top: 2px;
}
.live {
    display: inline-block;
    margin-top: 8px;
    padding: 2px 12px;
    border-radius: 999px;
    background: rgba(34, 211, 238, 0.12);
    border: 1px solid rgba(34, 211, 238, 0.5);
    color: #67e8f9;
    font-size: 0.85rem;
}
.live::before {
    content: "●";
    margin-right: 6px;
    animation: pulse 1.6s ease-in-out infinite;
}

p, .stMarkdown, label {
    color: #e0d8f5;
}
[data-testid="stCaptionContainer"] {
    color: #b9a8dd;
}

.stExpander, [data-testid="stExpander"] {
    background: rgba(36, 26, 62, 0.8);
    border: 1px solid #5b3fa0;
    border-radius: 12px;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.stExpander:hover, [data-testid="stExpander"]:hover {
    transform: translateY(-2px);
    border-color: #f472b6;
    box-shadow: 0 6px 24px rgba(244, 114, 182, 0.25);
}
.stExpander summary, [data-testid="stExpander"] summary {
    color: #f5f3ff;
    font-weight: 600;
}

[data-testid="stMetric"] {
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 10px 14px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    background-image: linear-gradient(rgba(28, 20, 50, 0.93), rgba(28, 20, 50, 0.93)),
                      linear-gradient(135deg, #a78bfa, #f472b6, #22d3ee);
    background-origin: border-box;
    background-clip: padding-box, border-box;
    backdrop-filter: blur(6px);
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 18px rgba(167, 139, 250, 0.4);
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {
    color: #c4b5fd !important;
    font-size: 0.92rem !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    color: #f5f3ff !important;
    font-size: 1.75rem !important;
}

.st-key-cards_ai [data-testid="stMetric"],
.st-key-cards_trace [data-testid="stMetric"] {
    background-image: linear-gradient(rgba(16, 26, 48, 0.94), rgba(16, 26, 48, 0.94)),
                      linear-gradient(135deg, #22d3ee, #3b82f6);
}
.st-key-cards_ai [data-testid="stMetricValue"], .st-key-cards_ai [data-testid="stMetricValue"] *,
.st-key-cards_trace [data-testid="stMetricValue"], .st-key-cards_trace [data-testid="stMetricValue"] * {
    color: #67e8f9 !important;
}
.st-key-cards_ai [data-testid="stMetric"]:hover,
.st-key-cards_trace [data-testid="stMetric"]:hover {
    box-shadow: 0 0 18px rgba(34, 211, 238, 0.45);
}

.st-key-cards_human [data-testid="stMetric"] {
    background-image: linear-gradient(rgba(30, 20, 52, 0.94), rgba(30, 20, 52, 0.94)),
                      linear-gradient(135deg, #a78bfa, #f472b6);
}
.st-key-cards_human [data-testid="stMetricValue"], .st-key-cards_human [data-testid="stMetricValue"] * {
    color: #e9d5ff !important;
}
.st-key-cards_human [data-testid="stMetric"]:hover {
    box-shadow: 0 0 18px rgba(244, 114, 182, 0.45);
}

.st-key-cards_speed [data-testid="stMetric"] {
    background-image: linear-gradient(rgba(36, 24, 40, 0.94), rgba(36, 24, 40, 0.94)),
                      linear-gradient(135deg, #fbbf24, #f472b6);
}
.st-key-cards_speed [data-testid="stMetricValue"], .st-key-cards_speed [data-testid="stMetricValue"] * {
    color: #fde68a !important;
}
.st-key-cards_speed [data-testid="stMetric"]:hover {
    box-shadow: 0 0 18px rgba(251, 191, 36, 0.45);
}

.st-key-cards_safety [data-testid="stMetric"] {
    background-image: linear-gradient(rgba(36, 24, 34, 0.94), rgba(36, 24, 34, 0.94)),
                      linear-gradient(135deg, #f472b6, #fbbf24);
}
.st-key-cards_safety [data-testid="stMetricValue"], .st-key-cards_safety [data-testid="stMetricValue"] * {
    color: #fbcfe8 !important;
}
.st-key-cards_safety [data-testid="stMetric"]:hover {
    box-shadow: 0 0 18px rgba(244, 114, 182, 0.45);
}

.stMarkdown table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}
.stMarkdown th {
    color: #c4b5fd;
    text-align: left;
    border-bottom: 1px solid #5b3fa0;
    padding: 6px 8px;
}
.stMarkdown td {
    color: #e0d8f5;
    border-bottom: 1px solid rgba(91, 63, 160, 0.4);
    padding: 6px 8px;
    vertical-align: top;
}

.trace-card {
    background: rgba(28, 20, 50, 0.88);
    border: 1px solid rgba(91, 63, 160, 0.6);
    border-left-width: 5px;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 10px;
}
.trace-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
}
.trace-agent {
    font-weight: 700;
    color: #f5f3ff;
}
.trace-decision {
    font-weight: 600;
    color: #fde68a;
}
.trace-meta {
    color: #b9a8dd;
    font-size: 0.85rem;
    margin: 2px 0 6px 0;
}
.trace-reason {
    color: #e0d8f5;
    font-size: 0.95rem;
    line-height: 1.45;
    white-space: pre-wrap;
}

div[data-baseweb="select"] > div {
    background: rgba(28, 20, 50, 0.92);
    border-color: #5b3fa0;
}
div[data-baseweb="select"] > div * {
    color: #f5f3ff !important;
}

button[role="tab"][aria-selected="true"] {
    color: #f472b6;
}

[class*="st-key-approve_"] button,
[class*="st-key-reject_"] button {
    border-radius: 8px;
    border: none;
    padding: 8px 24px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
[class*="st-key-approve_"] button {
    background-color: #16a34a;
}
[class*="st-key-approve_"] button:hover {
    background-color: #22c55e;
}
[class*="st-key-reject_"] button {
    background-color: #dc2626;
}
[class*="st-key-reject_"] button:hover {
    background-color: #ef4444;
}
[class*="st-key-approve_"] button:hover,
[class*="st-key-reject_"] button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
}
[class*="st-key-approve_"] button p,
[class*="st-key-reject_"] button p {
    color: #ffffff !important;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Estimated Gemini prices in USD per 1M tokens, as (input, output).
# Low and high come from two price pages that disagreed. Check ai.google.dev/pricing.
PRICE_LOW = (0.15, 1.25)
PRICE_HIGH = (0.30, 2.50)

ESCALATED_STATUSES = ("pending_human_review", "human_approved", "rejected")

# Tickets before this id were run when MCP startup was counted inside "Pipeline",
# so their times are not representative. Checked against the database: #11-#17 took 28-110 s,
# #18 onward take about 4-8 s.
FIRST_FAST_TICKET = 18

# Only count timing and token rows for tickets that still exist in the tickets table.
TRACES_QUERY = (
    "SELECT ticket_id, agent_name, latency_ms, input_tokens, output_tokens "
    "FROM traces WHERE ticket_id IN (SELECT id FROM tickets)"
)

STATUS_LABELS = {
    "auto_resolved": "Auto-resolved",
    "pending_human_review": "Awaiting human",
    "human_approved": "Approved by human",
    "rejected": "Rejected by human",
    "error": "Error",
    "open": "In progress",
    "resolved": "Resolved (old version)",
}
STATUS_COLORS = {
    "Auto-resolved": "#22d3ee",
    "Awaiting human": "#a78bfa",
    "Approved by human": "#4ade80",
    "Rejected by human": "#f472b6",
    "Error": "#fbbf24",
    "In progress": "#94a3b8",
    "Resolved (old version)": "#64748b",
}

AGENT_COLORS = {
    "Classifier": "#22d3ee",
    "Policy": "#a78bfa",
    "Action": "#f472b6",
    "Critic": "#fbbf24",
}
TRACE_COLORS = {**AGENT_COLORS, "Rule": "#fb7185"}

ROUTE_AGREED = "Auto-resolved (Critic agreed)"
ROUTE_OVERRULED = "Critic overruled an auto-resolve"
ROUTE_ACTION_ESCALATED = "Escalated by the Action agent"
ROUTE_RULE = "Escalated by the fixed rule"
ROUTE_COLORS = {
    ROUTE_AGREED: "#22d3ee",
    ROUTE_OVERRULED: "#fbbf24",
    ROUTE_ACTION_ESCALATED: "#a78bfa",
    ROUTE_RULE: "#f472b6",
}

LIGHT_TEXT = "#e0d8f5"
CHART_HEIGHT = 280

CATEGORY_GRADIENT = alt.Gradient(
    gradient="linear",
    stops=[
        alt.GradientStop(color="#7c3aed", offset=0),
        alt.GradientStop(color="#f472b6", offset=1),
    ],
    x1=0, x2=1, y1=0, y2=0,
)


def load(query, params=None):
    """Reads from tickets.db in read-only mode, so these numbers can never change your data."""
    conn = sqlite3.connect("file:tickets.db?mode=ro", uri=True)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def percent(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "-"


def md_safe(text, limit):
    """Makes free text safe to put inside a markdown table cell."""
    cleaned = str(text if text is not None else "").replace("\n", " ").replace("|", "/").replace("$", "\\$")
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


def style_chart(chart):
    """Makes a chart readable on the dark page: transparent background, light text."""
    return (
        chart.configure(background="transparent")
        .configure_axis(
            labelColor=LIGHT_TEXT,
            titleColor=LIGHT_TEXT,
            labelFontSize=13,
            titleFontSize=13,
            gridColor="#3f2d5c",
            domainColor="#5b3fa0",
        )
        .configure_legend(
            labelColor=LIGHT_TEXT, titleColor=LIGHT_TEXT, labelFontSize=13, titleFontSize=13
        )
        .configure_view(strokeWidth=0)
    )


def bar_chart_with_counts(
    df, label_col, count_col, colors=None, x_title="Tickets", number_format="d", height=None
):
    """Horizontal bars, biggest first, with the number printed at the end of each bar."""
    y = alt.Y(
        f"{label_col}:N",
        sort="-x",
        title=None,
        axis=alt.Axis(labelLimit=240, labelOverlap=False),
    )
    x = alt.X(f"{count_col}:Q", title=x_title)

    if colors:
        color = alt.Color(
            f"{label_col}:N",
            scale=alt.Scale(domain=list(colors.keys()), range=list(colors.values())),
            legend=None,
        )
        bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4).encode(
            y=y, x=x, color=color, tooltip=[label_col, count_col]
        )
    else:
        bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4, color=CATEGORY_GRADIENT).encode(
            y=y, x=x, tooltip=[label_col, count_col]
        )

    numbers = alt.Chart(df).mark_text(align="left", dx=4, fontSize=13, color=LIGHT_TEXT).encode(
        y=y, x=x, text=alt.Text(f"{count_col}:Q", format=number_format)
    )
    return style_chart((bars + numbers).properties(height=height or max(120, 34 * len(df))))


def donut_chart(auto, escalated, centre_text):
    """Handled by the AI versus sent to a human, with the autonomous rate in the middle."""
    df = pd.DataFrame(
        {"who": ["Handled by AI", "Sent to a human"], "count": [auto, escalated]}
    )
    arcs = alt.Chart(df).mark_arc(innerRadius=66, outerRadius=106, stroke="#150f20").encode(
        theta="count:Q",
        color=alt.Color(
            "who:N",
            scale=alt.Scale(
                domain=["Handled by AI", "Sent to a human"],
                range=["#22d3ee", "#a78bfa"],
            ),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        tooltip=["who", "count"],
    )
    centre = alt.Chart(pd.DataFrame({"t": [centre_text]})).mark_text(
        size=34, fontWeight="bold", color="#f5f3ff"
    ).encode(text="t:N")
    return style_chart((arcs + centre).properties(height=270))


@st.fragment(run_every=5)
def overview():
    tickets = load("SELECT id, status, category FROM tickets")
    traces = load(TRACES_QUERY)

    counts = tickets["status"].value_counts()
    auto = int(counts.get("auto_resolved", 0))
    waiting = int(counts.get("pending_human_review", 0))
    approved = int(counts.get("human_approved", 0))
    rejected = int(counts.get("rejected", 0))
    errors = int(counts.get("error", 0))
    legacy = int(counts.get("resolved", 0))
    escalated = waiting + approved + rejected
    finished = auto + escalated

    pipeline_seconds = (
        traces[
            (traces["agent_name"] == "Pipeline")
            & traces["latency_ms"].notna()
            & (traces["ticket_id"] >= FIRST_FAST_TICKET)
        ]["latency_ms"] / 1000
    )
    median_s = f"{pipeline_seconds.median():.1f} s" if len(pipeline_seconds) else "-"
    p95_s = f"{pipeline_seconds.quantile(0.95):.1f} s" if len(pipeline_seconds) else "-"

    with_tokens = traces[traces["input_tokens"].notna()]
    n = with_tokens["ticket_id"].nunique()
    if n:
        tokens_in = with_tokens["input_tokens"].sum() / n
        tokens_out = with_tokens["output_tokens"].fillna(0).sum() / n
        low = (tokens_in * PRICE_LOW[0] + tokens_out * PRICE_LOW[1]) / 1_000_000
        high = (tokens_in * PRICE_HIGH[0] + tokens_out * PRICE_HIGH[1]) / 1_000_000
        tokens_text = f"{tokens_in:,.0f} in / {tokens_out:,.0f} out"
        cost_text = rf"\${low:.4f} - \${high:.4f}"
    else:
        tokens_text = "-"
        cost_text = "-"

    with st.container(key="cards_ai"):
        row1 = st.columns(4)
        row1[0].metric("Finished by the AI", finished)
        row1[1].metric("Autonomous rate", percent(auto, finished))
        row1[2].metric("Escalation rate", percent(escalated, finished))
        row1[3].metric("Errors", errors)

    human_col, speed_col = st.columns([3, 4])

    with human_col:
        with st.container(key="cards_human"):
            inner = st.columns(3)
            inner[0].metric("Awaiting human", waiting)
            inner[1].metric("Approved", approved)
            inner[2].metric("Rejected", rejected)

    with speed_col:
        with st.container(key="cards_speed"):
            inner = st.columns(4)
            inner[0].metric("Median time", median_s)
            inner[1].metric("Slow case (p95)", p95_s)
            inner[2].metric("Tokens per ticket", tokens_text)
            inner[3].metric("Est. cost per ticket", cost_text)

    caption = (
        "Rates reflect the tickets in this database, which include a designed test mix, "
        "so they are not real-world rates. Cost is an estimate at paid-tier prices; "
        "development ran on the free tier."
    )
    if legacy:
        caption += (
            f" {legacy} older ticket(s) with the retired status 'resolved' appear in the "
            "outcomes chart but are not counted in the rates."
        )
    st.caption(caption)

    donut_col, outcomes_col, category_col = st.columns([1, 1.3, 1.3])

    with donut_col:
        st.markdown("**AI versus human**")
        if finished:
            st.altair_chart(
                donut_chart(auto, escalated, percent(auto, finished)),
                width="stretch",
            )
        else:
            st.write("No finished tickets yet.")

    with outcomes_col:
        st.markdown("**Where tickets ended up**")
        outcomes = counts.rename_axis("status").reset_index(name="count")
        if len(outcomes):
            outcomes["label"] = outcomes["status"].map(STATUS_LABELS).fillna(outcomes["status"])
            st.altair_chart(
                bar_chart_with_counts(outcomes, "label", "count", colors=STATUS_COLORS),
                width="stretch",
            )
        else:
            st.write("No tickets yet.")

    with category_col:
        st.markdown("**What customers asked about**")
        categories = (
            tickets["category"].fillna("Unknown").value_counts()
            .rename_axis("category").reset_index(name="count")
        )
        if len(categories):
            st.altair_chart(
                bar_chart_with_counts(categories, "category", "count"),
                width="stretch",
            )
        else:
            st.write("No tickets yet.")


@st.fragment(run_every=5)
def performance():
    traces = load(TRACES_QUERY)
    traces = traces[traces["ticket_id"].notna() & (traces["ticket_id"] >= FIRST_FAST_TICKET)]

    st.caption(
        f"Only tickets from #{FIRST_FAST_TICKET} onward are shown: earlier tickets were run with an "
        "older version that counted server start-up inside every ticket."
    )

    agent_names = list(AGENT_COLORS.keys())

    agent_rows = traces[
        traces["agent_name"].isin(agent_names) & traces["latency_ms"].notna()
    ].copy()
    agent_rows["seconds"] = agent_rows["latency_ms"] / 1000
    per_agent = (
        agent_rows.groupby("agent_name")["seconds"].median().round(3)
        .reset_index().rename(columns={"agent_name": "agent"})
    )

    pipeline = traces[
        (traces["agent_name"] == "Pipeline") & traces["latency_ms"].notna()
    ].copy()
    pipeline["seconds"] = pipeline["latency_ms"] / 1000

    token_rows = traces[traces["agent_name"].isin(agent_names) & traces["input_tokens"].notna()]
    tokens_per_agent = (
        token_rows.groupby("agent_name")[["input_tokens", "output_tokens"]].mean().round(0)
        .reset_index().rename(columns={"agent_name": "agent"})
    )
    tokens_long = tokens_per_agent.melt(
        id_vars="agent",
        value_vars=["input_tokens", "output_tokens"],
        var_name="kind",
        value_name="tokens",
    )
    tokens_long["kind"] = tokens_long["kind"].map(
        {"input_tokens": "Input", "output_tokens": "Output"}
    )

    agent_col, ticket_col, token_col = st.columns(3)

    with agent_col:
        st.markdown("**Where the time goes**")
        if len(per_agent):
            st.altair_chart(
                bar_chart_with_counts(
                    per_agent, "agent", "seconds",
                    colors=AGENT_COLORS, x_title="Seconds (median per agent)",
                    number_format=".3f", height=CHART_HEIGHT,
                ),
                width="stretch",
            )
            agent_total = float(per_agent["seconds"].sum())
            if len(pipeline):
                st.caption(
                    f"The four agents add up to about {agent_total:.2f} s of the "
                    f"{pipeline['seconds'].median():.2f} s typical ticket; the rest is time "
                    "outside the agents' own model calls (for example database and tool calls)."
                )
        else:
            st.write("No timing data yet.")

    with ticket_col:
        st.markdown("**Time per ticket**")
        if len(pipeline):
            median = float(pipeline["seconds"].median())
            p95 = float(pipeline["seconds"].quantile(0.95))
            upper = max(10.0, float(round(p95 * 1.6)))
            x_scale = alt.Scale(
                domain=[float(pipeline["ticket_id"].min()) - 1, float(pipeline["ticket_id"].max()) + 1]
            )

            dots = alt.Chart(pipeline).mark_circle(size=70, color="#f472b6", opacity=0.85, clip=True).encode(
                x=alt.X("ticket_id:Q", title="Ticket number", scale=x_scale, axis=alt.Axis(format="d", tickMinStep=1)),
                y=alt.Y("seconds:Q", title="Seconds", scale=alt.Scale(domain=[0, upper])),
                tooltip=["ticket_id", alt.Tooltip("seconds:Q", format=".2f")],
            )
            median_line = alt.Chart(pd.DataFrame({"m": [median]})).mark_rule(
                strokeDash=[6, 4], color="#fbbf24", size=2
            ).encode(y="m:Q")
            median_label = alt.Chart(
                pd.DataFrame(
                    {"x": [float(pipeline["ticket_id"].max())], "m": [median], "t": [f"median {median:.2f} s"]}
                )
            ).mark_text(align="right", dy=-10, fontSize=13, color="#fbbf24").encode(
                x=alt.X("x:Q", scale=x_scale), y="m:Q", text="t:N"
            )
            st.altair_chart(
                style_chart((dots + median_line + median_label).properties(height=CHART_HEIGHT)),
                width="stretch",
            )

            outliers = pipeline[pipeline["seconds"] > upper]
            if len(outliers):
                listed = ", ".join(
                    f"ticket #{int(r.ticket_id)} took {r.seconds:.0f} s" for r in outliers.itertuples()
                )
                st.caption(f"Off the top of the chart: {listed}.")
            else:
                st.caption("Each dot is one ticket. The dashed line is the median.")
        else:
            st.write("No timing data yet.")

    with token_col:
        st.markdown("**Where the tokens go**")
        if len(tokens_long):
            y = alt.Y("agent:N", sort=agent_names, title=None, axis=alt.Axis(labelOverlap=False))
            x = alt.X("tokens:Q", title="Tokens per call (average)")
            kind_color = alt.Color(
                "kind:N",
                scale=alt.Scale(domain=["Input", "Output"], range=["#22d3ee", "#f472b6"]),
                legend=alt.Legend(orient="bottom", title=None),
            )
            bars = alt.Chart(tokens_long).mark_bar(cornerRadiusEnd=4).encode(
                y=y, x=x, yOffset="kind:N", color=kind_color,
                tooltip=["agent", "kind", "tokens"],
            )
            numbers = alt.Chart(tokens_long).mark_text(
                align="left", dx=4, fontSize=12, color=LIGHT_TEXT
            ).encode(y=y, x=x, yOffset="kind:N", text=alt.Text("tokens:Q", format=",.0f"))
            st.altair_chart(
                style_chart((bars + numbers).properties(height=CHART_HEIGHT)),
                width="stretch",
            )
            st.caption("Input is what the agent reads; output is what it writes. Output costs more per token.")
        else:
            st.write("No token data yet.")


@st.fragment(run_every=5)
def safety():
    tickets = load("SELECT id, status, message FROM tickets")
    traces = load(
        "SELECT ticket_id, agent_name, decision, reasoning FROM traces "
        "WHERE ticket_id IN (SELECT id FROM tickets)"
    )
    traces["ticket_id"] = traces["ticket_id"].astype(int)

    errors = int((tickets["status"] == "error").sum())

    last = traces.drop_duplicates(subset=["ticket_id", "agent_name"], keep="last")
    action = (
        last[last["agent_name"] == "Action"].set_index("ticket_id")["decision"]
        .astype(str).str.strip().str.lower()
    )
    critic = (
        last[last["agent_name"] == "Critic"].set_index("ticket_id")["decision"]
        .astype(str).str.strip().str.lower()
    )
    critic_reason = last[last["agent_name"] == "Critic"].set_index("ticket_id")["reasoning"]
    rule_reason = last[last["agent_name"] == "Rule"].set_index("ticket_id")["reasoning"]

    routes = []
    for ticket_id in tickets["id"].astype(int):
        if ticket_id in rule_reason.index:
            route = ROUTE_RULE
        elif ticket_id in action.index:
            if action[ticket_id] == "auto_resolve":
                route = ROUTE_OVERRULED if critic.get(ticket_id) == "false" else ROUTE_AGREED
            else:
                route = ROUTE_ACTION_ESCALATED
        else:
            continue
        routes.append((ticket_id, route))

    routes_df = pd.DataFrame(routes, columns=["ticket_id", "route"])
    route_counts = routes_df["route"].value_counts()

    agreed = int(route_counts.get(ROUTE_AGREED, 0))
    overruled = int(route_counts.get(ROUTE_OVERRULED, 0))
    by_rule = int(route_counts.get(ROUTE_RULE, 0))
    proposals = agreed + overruled

    st.caption(
        "Three safety layers sit between a customer message and an automatic answer: "
        "(1) the Classifier can flag a message as unclassifiable, and a fixed rule then sends it to a human; "
        "(2) the Critic agent can veto an auto-resolve; "
        "(3) every escalation waits for a human to approve or reject it."
    )

    with st.container(key="cards_safety"):
        cards = st.columns(4)
        cards[0].metric("Critic overruled", overruled)
        cards[1].metric("Of AI auto-resolve proposals", percent(overruled, proposals))
        cards[2].metric("Escalated by the fixed rule", by_rule)
        cards[3].metric("Errors", errors)

    chart_col, table_col = st.columns([1, 1.4])

    with chart_col:
        st.markdown("**How each decision was reached**")
        if len(route_counts):
            chart_df = route_counts.rename_axis("route").reset_index(name="count")
            st.altair_chart(
                bar_chart_with_counts(chart_df, "route", "count", colors=ROUTE_COLORS, height=CHART_HEIGHT),
                width="stretch",
            )
            st.caption(
                f"This counts every ticket that reached the Action step or the fixed rule ({len(routes_df)} in total), "
                "including older, errored and unfinished ones, so it can be larger than "
                "'Finished by the AI' on the Overview tab. A Critic disagreement on a ticket the Action agent "
                "already escalated changes nothing, so only vetoes of auto-resolves are counted as 'overruled'."
            )
        else:
            st.write("No decisions recorded yet.")

    with table_col:
        st.markdown("**Latest tickets the safety layers stopped**")
        stopped = routes_df[routes_df["route"].isin([ROUTE_RULE, ROUTE_OVERRULED])]
        stopped = stopped.sort_values("ticket_id", ascending=False).head(8)
        if len(stopped):
            messages = tickets.set_index("id")["message"]
            lines = ["| # | Stopped by | Message | Reason |", "|---|---|---|---|"]
            for row in stopped.itertuples():
                if row.route == ROUTE_RULE:
                    who = "Fixed rule"
                    reason = rule_reason.get(row.ticket_id, "")
                else:
                    who = "Critic"
                    reason = critic_reason.get(row.ticket_id, "")
                lines.append(
                    f"| {row.ticket_id} | {who} | {md_safe(messages.get(row.ticket_id, ''), 150)} "
                    f"| {md_safe(reason, 600)} |"
                )
            st.markdown("\n".join(lines))
        else:
            st.write("No tickets stopped by a safety layer yet.")


def friendly_decision(agent, decision):
    """Turns the stored decision text into words a person can read."""
    text = str(decision if decision is not None else "").strip()
    lowered = text.lower()
    if agent == "Critic":
        if lowered == "true":
            return "Approved the plan"
        if lowered == "false":
            return "Vetoed the plan"
    if agent == "Policy" and lowered == "reasoning_generated":
        return "Wrote policy reasoning"
    return text


def trace_card(step_number, row):
    """One agent's step as a card. Every piece of text is escaped before it is shown."""
    agent = str(row["agent_name"])
    colour = TRACE_COLORS.get(agent, "#94a3b8")
    seconds = f"{row['latency_ms'] / 1000:.2f} s" if pd.notna(row["latency_ms"]) else "time not recorded"
    if pd.notna(row["input_tokens"]):
        output_tokens = row["output_tokens"] if pd.notna(row["output_tokens"]) else 0
        tokens = f"{int(row['input_tokens'])} in / {int(output_tokens)} out tokens"
    else:
        tokens = "no model call"
    reasoning = html.escape(str(row["reasoning"] if row["reasoning"] is not None else ""))
    return (
        f'<div class="trace-card" style="border-left-color: {colour};">'
        f'<div class="trace-head"><span class="trace-agent">{step_number}. {html.escape(agent)}</span>'
        f'<span class="trace-decision">{html.escape(friendly_decision(agent, row["decision"]))}</span></div>'
        f'<div class="trace-meta">{seconds} · {tokens}</div>'
        f'<div class="trace-reason">{reasoning}</div>'
        f"</div>"
    )


@st.fragment
def trace_explorer():
    tickets = load("SELECT id, status, category, intent, message FROM tickets ORDER BY id DESC")
    if tickets.empty:
        st.write("No tickets yet.")
        return

    info = tickets.set_index("id")
    ticket_ids = [int(i) for i in tickets["id"]]

    def label(ticket_id):
        row = info.loc[ticket_id]
        status = STATUS_LABELS.get(row["status"], row["status"])
        message = str(row["message"]).replace("\n", " ")[:55]
        return f"#{ticket_id} · {status} · {message}"

    selected = st.selectbox("Choose a ticket", ticket_ids, format_func=label, key="trace_ticket")
    ticket = info.loc[selected]

    traces = load(
        "SELECT agent_name, decision, reasoning, latency_ms, input_tokens, output_tokens "
        "FROM traces WHERE ticket_id = ? ORDER BY id",
        params=(int(selected),),
    )
    steps = traces[~traces["agent_name"].isin(["Pipeline", "MCP startup"])]
    pipeline = traces[traces["agent_name"] == "Pipeline"]

    total_seconds = "-"
    if len(pipeline) and pd.notna(pipeline["latency_ms"].iloc[0]):
        total_seconds = f"{pipeline['latency_ms'].iloc[0] / 1000:.2f} s"

    tokens_in = int(steps["input_tokens"].sum()) if len(steps) else 0
    tokens_out = int(steps["output_tokens"].sum()) if len(steps) else 0

    with st.container(key="cards_trace"):
        cards = st.columns(3)
        cards[0].metric("Final status", STATUS_LABELS.get(ticket["status"], ticket["status"]))
        cards[1].metric("Total time", total_seconds)
        cards[2].metric("Tokens (in / out)", f"{tokens_in:,} / {tokens_out:,}")

    category = html.escape(str(ticket["category"] if ticket["category"] is not None else "not classified"))
    intent = html.escape(str(ticket["intent"] if ticket["intent"] is not None else ""))
    st.markdown(
        '<div class="trace-card" style="border-left-color: #a78bfa;">'
        f'<div class="trace-head"><span class="trace-agent">Customer message</span>'
        f'<span class="trace-decision">{category} / {intent}</span></div>'
        f'<div class="trace-reason">{html.escape(str(ticket["message"]))}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    if steps.empty:
        st.info(
            "There are no agent records for this ticket. It was probably created by an early "
            "version or before records were saved, or its records were cleaned up."
        )
        return

    steps_col, time_col = st.columns([1.5, 1])

    with steps_col:
        st.markdown("**What each agent did, in order**")
        for number, (_, row) in enumerate(steps.iterrows(), start=1):
            st.markdown(trace_card(number, row), unsafe_allow_html=True)

    with time_col:
        st.markdown("**Where this ticket's time went**")
        timed = steps[steps["agent_name"].isin(TRACE_COLORS.keys()) & steps["latency_ms"].notna()].copy()
        if len(timed):
            timed["seconds"] = timed["latency_ms"] / 1000
            time_df = timed[["agent_name", "seconds"]].rename(columns={"agent_name": "agent"})
            st.altair_chart(
                bar_chart_with_counts(
                    time_df, "agent", "seconds", colors=TRACE_COLORS,
                    x_title="Seconds", number_format=".2f", height=max(140, 52 * len(time_df)),
                ),
                width="stretch",
            )
        else:
            st.write("No timing recorded for this ticket.")


def review_queue():
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, message, category, intent, status, agent_reasoning "
        "FROM tickets WHERE status = 'pending_human_review'"
    )
    pending_tickets = cursor.fetchall()
    conn.close()

    st.write(f"**{len(pending_tickets)} ticket(s) awaiting review**")

    for ticket in pending_tickets:
        ticket_id, message, category, intent, status, agent_reasoning = ticket

        with st.expander(f"Ticket #{ticket_id} — {category} / {intent}"):
            st.write("**Customer message:**", message)
            st.write("**Agent reasoning:**", agent_reasoning)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Approve", key=f"approve_{ticket_id}"):
                    conn = sqlite3.connect("tickets.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tickets SET status = 'human_approved' WHERE id = ?", (ticket_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Ticket #{ticket_id} approved and resolved.")
                    st.rerun()

            with col2:
                if st.button("❌ Reject", key=f"reject_{ticket_id}"):
                    conn = sqlite3.connect("tickets.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tickets SET status = 'rejected' WHERE id = ?", (ticket_id,))
                    conn.commit()
                    conn.close()
                    st.warning(f"Ticket #{ticket_id} rejected.")
                    st.rerun()


st.markdown("""
<div class="hero">
    <div class="hero-title">Sribhava Retail</div>
    <div class="hero-sub">Multi-agent customer support desk · live operations view</div>
    <span class="live">Live · refreshes every 5 seconds</span>
</div>
""", unsafe_allow_html=True)

tab_dashboard, tab_review = st.tabs(["📊 Dashboard", "🎫 Review queue"])

with tab_dashboard:
    sub_overview, sub_performance, sub_safety, sub_trace = st.tabs(
        ["Overview", "Performance", "Safety", "Trace explorer"]
    )

    with sub_overview:
        overview()

    with sub_performance:
        performance()

    with sub_safety:
        safety()

    with sub_trace:
        trace_explorer()

with tab_review:
    review_queue()