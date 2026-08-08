"""
TradingAgents — LangGraph stock analysis system.

Loop stack:
1. Agent loop (model + tools)
2. Verification loop (grader + retry)
3. Event-driven self-driving loop (interval price tracking)
"""

__version__ = "2.0.0"
