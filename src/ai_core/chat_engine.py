"""
AI Chat Engine for Cash Flow Intelligence

Sophisticated conversational AI for SMB financial consulting.
Manages conversation state, context injection, and response enhancement.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .claude_client import ClaudeClient, get_claude_client

logger = logging.getLogger(__name__)


class ConversationMode(Enum):
    """Chat conversation modes for Cash Flow Intelligence"""
    GENERAL = "general"
    CASH_FLOW_ANALYSIS = "cash_flow_analysis"
    FORECAST_DISCUSSION = "forecast_discussion"
    WORKING_CAPITAL = "working_capital"
    BENCHMARK_REVIEW = "benchmark_review"
    ACTION_PLANNING = "action_planning"
    REPORT_ASSISTANCE = "report_assistance"


@dataclass
class ChatSession:
    """Active chat session with context"""
    session_id: str
    company_name: str
    mode: ConversationMode = ConversationMode.GENERAL
    financial_summary: Optional[Dict] = None
    industry: str = "general"
    conversation_history: List[Dict] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


class AIChatEngine:
    """
    AI-powered chat engine for SMB financial consulting.

    Features:
    - Context-aware responses based on financial data
    - Multiple conversation modes
    - Suggested questions and prompts
    - Session management
    """

    # Suggested prompts by mode
    SUGGESTED_PROMPTS = {
        ConversationMode.GENERAL: [
            "How healthy is my cash flow right now?",
            "What's the most important thing I should focus on?",
            "How do we compare to other businesses our size?",
            "What's our biggest cash flow risk?"
        ],
        ConversationMode.CASH_FLOW_ANALYSIS: [
            "Walk me through our cash flow trends",
            "Why is our cash position where it is?",
            "What's driving our cash burn?",
            "Where is money getting stuck in our business?"
        ],
        ConversationMode.FORECAST_DISCUSSION: [
            "What does our cash forecast look like?",
            "When might we face a cash crunch?",
            "What assumptions should we adjust?",
            "How accurate have past forecasts been?"
        ],
        ConversationMode.WORKING_CAPITAL: [
            "How can we speed up collections?",
            "Should we extend our payment terms?",
            "How do we optimize our inventory cash?",
            "What's a good cash conversion cycle for us?"
        ],
        ConversationMode.BENCHMARK_REVIEW: [
            "How do our metrics compare to industry averages?",
            "Where are we outperforming peers?",
            "Which KPIs need the most improvement?",
            "What should our targets be?"
        ],
        ConversationMode.ACTION_PLANNING: [
            "Create a 90-day cash flow action plan",
            "What quick wins can we implement this week?",
            "How do we build a cash reserve?",
            "What's our emergency cash plan?"
        ],
        ConversationMode.REPORT_ASSISTANCE: [
            "Help me prepare for a board meeting",
            "Summarize our cash position for investors",
            "What should I tell my banker?",
            "Create a cash flow summary for my team"
        ]
    }

    # Mode-specific system context additions
    MODE_CONTEXTS = {
        ConversationMode.CASH_FLOW_ANALYSIS: """
You are analyzing the company's cash flow situation in detail.
Explain the drivers behind cash position changes, identify patterns,
and help the user understand where cash is going. Use specific numbers
from their data when available.""",

        ConversationMode.FORECAST_DISCUSSION: """
You are discussing cash flow forecasts and projections.
Help interpret forecast data, explain assumptions, discuss scenarios,
and identify potential risks. Be clear about uncertainty in projections.""",

        ConversationMode.WORKING_CAPITAL: """
You are helping optimize working capital management.
Focus on receivables, payables, inventory, and the cash conversion cycle.
Provide actionable advice on accelerating cash and managing timing.""",

        ConversationMode.BENCHMARK_REVIEW: """
You are reviewing financial benchmarks and peer comparisons.
Help interpret KPI comparisons, identify performance gaps,
and suggest realistic improvement targets.""",

        ConversationMode.ACTION_PLANNING: """
You are helping create actionable cash flow improvement plans.
Provide specific, prioritized actions with realistic timeframes.
Consider the company's capacity to implement changes.""",

        ConversationMode.REPORT_ASSISTANCE: """
You are helping prepare financial communications and reports.
Help create clear, professional summaries appropriate for the audience.
Focus on key messages and support with relevant data."""
    }

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        """Initialize chat engine"""
        self.claude = claude_client or get_claude_client()
        self.sessions: Dict[str, ChatSession] = {}

    def create_session(
        self,
        company_name: str,
        industry: str = "general",
        financial_summary: Optional[Dict] = None,
        mode: ConversationMode = ConversationMode.GENERAL
    ) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())

        session = ChatSession(
            session_id=session_id,
            company_name=company_name,
            mode=mode,
            financial_summary=financial_summary,
            industry=industry
        )

        # Build context for Claude
        context = self._build_context(session)
        self.claude.create_conversation(session_id, "cfo_consultant", context)

        self.sessions[session_id] = session
        logger.info(f"Created chat session {session_id} for {company_name}")

        return session

    def _build_context(self, session: ChatSession) -> Dict[str, Any]:
        """Build context dictionary for Claude"""
        context = {
            "company_name": session.company_name,
            "industry": session.industry,
            "conversation_mode": session.mode.value
        }

        if session.financial_summary:
            context["financial_summary"] = {
                "health_score": session.financial_summary.get("health_score"),
                "risk_level": session.financial_summary.get("risk_level"),
                "cash_runway_months": session.financial_summary.get("cash_runway_months"),
                "current_cash": session.financial_summary.get("current_cash"),
                "monthly_burn": session.financial_summary.get("monthly_burn"),
                "dso": session.financial_summary.get("dso"),
                "dpo": session.financial_summary.get("dpo"),
                "key_metrics": session.financial_summary.get("key_metrics"),
                "top_concerns": session.financial_summary.get("top_concerns"),
                "recommendations": session.financial_summary.get("recommendations")
            }

        # Add mode-specific context
        if session.mode in self.MODE_CONTEXTS:
            context["mode_instructions"] = self.MODE_CONTEXTS[session.mode]

        return context

    def chat(
        self,
        session_id: str,
        user_message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Process a chat message."""
        if session_id not in self.sessions:
            return {
                "error": "Session not found",
                "message": "Please start a new conversation."
            }

        session = self.sessions[session_id]
        session.last_activity = datetime.now()

        # Add to conversation history
        session.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # Get response from Claude
        response = self.claude.chat(session_id, user_message, stream=stream)

        # Add assistant response to history
        session.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "message": response,
            "session_id": session_id,
            "mode": session.mode.value,
            "suggested_prompts": self.get_suggested_prompts(session_id),
            "timestamp": datetime.now().isoformat()
        }

    def stream_chat(
        self,
        session_id: str,
        user_message: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a chat response token by token."""
        if session_id not in self.sessions:
            yield {
                "type": "error",
                "content": "Session not found. Please start a new conversation."
            }
            return

        session = self.sessions[session_id]
        session.last_activity = datetime.now()

        # Add user message to history
        session.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # Check if Claude is available
        if not self.claude.is_available():
            fallback = self.claude._fallback_response(
                user_message,
                self.claude.conversations.get(session_id)
            )
            words = fallback.split(' ')
            for i, word in enumerate(words):
                yield {"type": "token", "content": word + (' ' if i < len(words) - 1 else '')}

            session.conversation_history.append({
                "role": "assistant",
                "content": fallback,
                "timestamp": datetime.now().isoformat()
            })

            yield {
                "type": "done",
                "suggested_prompts": self.get_suggested_prompts(session_id)
            }
            return

        # Stream from Claude
        try:
            full_response = ""
            conversation = self.claude.conversations.get(session_id)

            if not conversation:
                context = self._build_context(session)
                conversation = self.claude.create_conversation(session_id, "cfo_consultant", context)

            conversation.add_message("user", user_message)

            with self.claude.client.messages.stream(
                model=self.claude.model,
                max_tokens=self.claude.MAX_TOKENS,
                system=conversation.system_prompt,
                messages=conversation.get_messages_for_api()
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield {"type": "token", "content": text}

            conversation.add_message("assistant", full_response)
            session.conversation_history.append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now().isoformat()
            })

            yield {
                "type": "done",
                "suggested_prompts": self.get_suggested_prompts(session_id)
            }

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "type": "error",
                "content": f"An error occurred: {str(e)}"
            }

    def change_mode(self, session_id: str, new_mode: ConversationMode) -> bool:
        """Change conversation mode for a session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.mode = new_mode

        context = self._build_context(session)
        self.claude.create_conversation(session_id, "cfo_consultant", context)

        for msg in session.conversation_history:
            self.claude.conversations[session_id].add_message(
                msg["role"], msg["content"]
            )

        logger.info(f"Changed session {session_id} to mode {new_mode.value}")
        return True

    def get_suggested_prompts(self, session_id: str) -> List[str]:
        """Get suggested prompts based on current mode and context"""
        if session_id not in self.sessions:
            return self.SUGGESTED_PROMPTS[ConversationMode.GENERAL]

        session = self.sessions[session_id]
        base_prompts = self.SUGGESTED_PROMPTS.get(
            session.mode,
            self.SUGGESTED_PROMPTS[ConversationMode.GENERAL]
        )

        # Add context-aware prompts if we have financial data
        if session.financial_summary and session.mode == ConversationMode.GENERAL:
            health_score = session.financial_summary.get("health_score", 50)
            runway = session.financial_summary.get("cash_runway_months", 12)

            if health_score < 40 or runway < 3:
                base_prompts = [
                    "What should we do right now to preserve cash?",
                    "How do we extend our runway quickly?",
                ] + base_prompts[:2]
            elif health_score >= 70 and runway > 12:
                base_prompts = [
                    "How should we deploy excess cash?",
                    "What growth investments make sense now?",
                ] + base_prompts[:2]

        return base_prompts

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def update_financial_data(self, session_id: str, financial_summary: Dict) -> bool:
        """Update financial data for a session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.financial_summary = financial_summary

        context = self._build_context(session)
        if session_id in self.claude.conversations:
            self.claude.conversations[session_id].context = context

        return True

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of conversation"""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]

        return {
            "session_id": session_id,
            "company_name": session.company_name,
            "industry": session.industry,
            "mode": session.mode.value,
            "message_count": len(session.conversation_history),
            "has_financial_data": session.financial_summary is not None,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }

    def export_conversation(self, session_id: str) -> Dict[str, Any]:
        """Export full conversation for saving/reporting"""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]

        return {
            "session_id": session_id,
            "company_name": session.company_name,
            "industry": session.industry,
            "health_score": session.financial_summary.get("health_score") if session.financial_summary else None,
            "conversation": session.conversation_history,
            "exported_at": datetime.now().isoformat()
        }


# Singleton instance
_engine: Optional[AIChatEngine] = None


def get_chat_engine() -> AIChatEngine:
    """Get or create singleton chat engine"""
    global _engine
    if _engine is None:
        _engine = AIChatEngine()
    return _engine
