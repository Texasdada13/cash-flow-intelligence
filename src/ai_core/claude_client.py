"""
Claude API Client for Cash Flow Intelligence

Wrapper for Anthropic's Claude API providing:
- Financial consulting conversations
- Cash flow analysis assistance
- Report generation
- Error handling and retries
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation context"""
    id: str
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str, **metadata) -> Message:
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        return msg

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Format messages for Claude API"""
        return [{"role": m.role, "content": m.content} for m in self.messages]


class ClaudeClient:
    """
    Claude API Client for Cash Flow Intelligence.

    Provides high-level interface for:
    - Financial health conversations
    - Cash flow forecasting assistance
    - Financial KPI analysis
    - Recommendation generation
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    # System prompts for different contexts
    SYSTEM_PROMPTS = {
        "cfo_consultant": """You are an expert Virtual CFO Consultant helping small and medium businesses understand and optimize their cash flow. You work for Patriot Tech Systems Consulting.

Your expertise includes:
- Cash flow analysis and forecasting
- Working capital management
- Financial KPI interpretation
- Liquidity planning
- Accounts receivable/payable optimization
- Burn rate and runway analysis
- Financial health assessment

When advising clients:
1. Be specific and actionable - provide concrete next steps
2. Explain financial metrics in simple terms
3. Consider their current financial position
4. Balance short-term needs with long-term health
5. Highlight cash flow risks and mitigation strategies

You have access to their financial data which will be provided in the context.""",

        "financial_analyst": """You are a financial analyst specializing in SMB cash flow analysis. Analyze the provided financial data and provide insights.

Focus on:
- Identifying cash flow patterns and trends
- Highlighting liquidity strengths and concerns
- Comparing to industry benchmarks
- Prioritizing areas for improvement
- Quantifying potential impact of changes""",

        "report_writer": """You are a professional financial report writer. Create clear, executive-ready content about cash flow and financial health.

Document style guidelines:
- Use clear, professional language
- Include specific metrics and projections
- Structure content with clear headers
- Provide actionable recommendations
- Balance detail with readability"""
    }

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Claude client."""
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.model = model or self.DEFAULT_MODEL
        self.client = None
        self.conversations: Dict[str, Conversation] = {}

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Claude client initialized with model {self.model}")
        else:
            logger.warning("Anthropic SDK not available or no API key - using fallback mode")

    def is_available(self) -> bool:
        """Check if Claude API is available"""
        return self.client is not None

    def create_conversation(
        self,
        conversation_id: str,
        context_type: str = "cfo_consultant",
        custom_context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation with context."""
        system_prompt = self.SYSTEM_PROMPTS.get(context_type, self.SYSTEM_PROMPTS["cfo_consultant"])

        if custom_context:
            context_str = "\n\nFINANCIAL CONTEXT:\n" + json.dumps(custom_context, indent=2, default=str)
            system_prompt += context_str

        conversation = Conversation(
            id=conversation_id,
            system_prompt=system_prompt,
            context=custom_context or {}
        )
        self.conversations[conversation_id] = conversation
        return conversation

    def chat(
        self,
        conversation_id: str,
        user_message: str,
        stream: bool = False
    ) -> str:
        """Send a message and get response."""
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)

        conversation = self.conversations[conversation_id]
        conversation.add_message("user", user_message)

        if not self.is_available():
            response = self._fallback_response(user_message, conversation)
            conversation.add_message("assistant", response)
            return response

        try:
            if stream:
                return self._stream_response(conversation)
            else:
                return self._get_response(conversation)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            response = f"I apologize, but I encountered an error: {str(e)}. Please try again."
            conversation.add_message("assistant", response)
            return response

    def _get_response(self, conversation: Conversation) -> str:
        """Get non-streaming response from Claude"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            system=conversation.system_prompt,
            messages=conversation.get_messages_for_api()
        )

        assistant_message = response.content[0].text
        conversation.add_message("assistant", assistant_message)
        return assistant_message

    def _stream_response(self, conversation: Conversation) -> Generator[str, None, None]:
        """Stream response from Claude"""
        full_response = ""

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            system=conversation.system_prompt,
            messages=conversation.get_messages_for_api()
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield text

        conversation.add_message("assistant", full_response)

    def _fallback_response(self, user_message: str, conversation: Optional[Conversation]) -> str:
        """Generate fallback response when API is unavailable"""
        context = conversation.context if conversation else {}

        if context and 'financial_summary' in context:
            summary = context['financial_summary']
            health_score = summary.get('health_score', 0)
            cash_runway = summary.get('cash_runway_months', 0)

            return f"""Thank you for your question. Based on your financial data:

**Current Position:**
- Financial Health Score: {health_score}/100
- Cash Runway: {cash_runway} months

I'd be happy to provide more specific guidance, but I'm currently operating in offline mode. To get personalized AI-powered recommendations:

1. Ensure your ANTHROPIC_API_KEY environment variable is set
2. Restart the application

In the meantime, here are general recommendations based on your score:
- {"Focus on immediate cash preservation and accelerating collections" if health_score < 40 else ""}
- {"Optimize working capital and review expense timing" if 40 <= health_score < 70 else ""}
- {"Consider growth investments and strategic cash deployment" if health_score >= 70 else ""}

Would you like me to elaborate on any specific area?"""

        return """I'm currently operating in offline mode without access to the Claude API.

To enable full AI-powered financial consulting capabilities:
1. Set your ANTHROPIC_API_KEY environment variable
2. Restart the application

In the meantime, I can still help you with:
- Navigating the dashboard
- Understanding your financial metrics
- Exploring the benchmark comparisons

What would you like to explore?"""

    def analyze_cash_flow(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cash flow data using Claude."""
        conv_id = f"analysis_{datetime.now().timestamp()}"
        self.create_conversation(conv_id, "financial_analyst", {"financial_data": financial_data})

        analysis_prompt = """Analyze this cash flow data and provide:

1. **Key Insights** (3-5 bullet points)
2. **Cash Flow Health Assessment** (Critical/Stressed/Stable/Strong)
3. **Immediate Concerns** requiring attention
4. **Quick Wins** to improve cash position
5. **Recommended Actions** (prioritized)

Format your response as a structured analysis."""

        response = self.chat(conv_id, analysis_prompt)

        return {
            "analysis": response,
            "generated_at": datetime.now().isoformat(),
            "data_snapshot": financial_data
        }


# Singleton instance
_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get or create singleton Claude client"""
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client
