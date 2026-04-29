"""
Simulated HR Agent for TrustLLM agent evaluation.

Selects a tool based on keywords present in the user query.
No external API calls are made — this is deterministic and
designed for use in the agentic testing engine.
"""

import re


# Keyword → tool routing table.
# Keywords are matched with a leading word-boundary (\b) so that, e.g.,
# "pto" does NOT accidentally match inside "laptop".
_TOOL_ROUTING = [
    # Workday: PTO / leave-balance queries
    (["pto", "leave balance", "vacation", "time off", "days off"], "workday_api"),
    # ServiceNow: support tickets / incidents / hardware issues
    (["ticket", "incident", "laptop", "keyboard", "hardware", "support request"], "servicenow_api"),
    # Policy retriever: policy / procedure / handbook lookup
    (["policy", "guideline", "rule", "handbook", "procedure", "regulation", "paid leave"], "policy_retriever"),
]

# Canned responses per tool
_TOOL_RESPONSES = {
    "workday_api": "Your PTO balance is 12 days.",
    "servicenow_api": "A support ticket has been created (INC0012345).",
    "policy_retriever": "Here is the relevant company policy section.",
    "unknown": "I could not determine the appropriate tool for your query.",
}


class HRAgent:
    """Simple simulated HR agent for agentic evaluation."""

    def run(self, query: str) -> dict:
        """
        Accept a user query, select the best tool, and return a response.

        Returns:
            dict with keys:
                tool_used (str): the tool selected by the agent
                response  (str): a canned reply from that tool
        """
        query_lower = query.lower()
        tool = self._select_tool(query_lower)
        return {
            "tool_used": tool,
            "response": _TOOL_RESPONSES.get(tool, _TOOL_RESPONSES["unknown"]),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_tool(self, query_lower: str) -> str:
        for keywords, tool in _TOOL_ROUTING:
            for kw in keywords:
                # \b anchors to a word boundary so "pto" won't match inside
                # "laptop", and "procedure" will still match "procedures".
                if re.search(r"\b" + re.escape(kw), query_lower):
                    return tool
        return "unknown"
