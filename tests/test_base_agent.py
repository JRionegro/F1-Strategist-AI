"""
Unit Tests for BaseAgent

Tests the abstract base agent class and its concrete implementations.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

from src.agents.base_agent import (
    BaseAgent,
    AgentConfig,
    AgentContext,
    AgentResponse
)
from src.llm.provider import LLMProvider


# Concrete implementation for testing
class TestAgent(BaseAgent):
    """Concrete agent implementation for testing."""
    
    def get_system_prompt(self) -> str:
        return "You are a test agent for F1 strategy analysis."
    
    def get_available_tools(self) -> List[str]:
        return ["get_race_results", "get_lap_times"]
    
    def validate_query(self, query: str) -> bool:
        # Simple validation: reject empty queries
        return len(query.strip()) > 0


class TestAgentDataClasses:
    """Test agent data classes."""
    
    def test_agent_config_creation(self):
        """Test AgentConfig creation with required fields."""
        mock_llm = Mock(spec=LLMProvider)
        
        config = AgentConfig(
            name="TestAgent",
            description="Test agent for unit tests",
            llm_provider=mock_llm
        )
        
        assert config.name == "TestAgent"
        assert config.description == "Test agent for unit tests"
        assert config.llm_provider == mock_llm
        assert config.temperature == 0.7  # Default
        assert config.max_tokens == 2000  # Default
        assert config.enable_rag is True  # Default
        assert config.enable_tools is True  # Default
    
    def test_agent_config_custom_values(self):
        """Test AgentConfig with custom values."""
        mock_llm = Mock(spec=LLMProvider)
        
        config = AgentConfig(
            name="CustomAgent",
            description="Custom test agent",
            llm_provider=mock_llm,
            temperature=0.5,
            max_tokens=1000,
            enable_rag=False,
            enable_tools=False
        )
        
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.enable_rag is False
        assert config.enable_tools is False
    
    def test_agent_context_creation(self):
        """Test AgentContext creation."""
        context = AgentContext(
            session_type="race",
            year=2024,
            race_name="Monaco Grand Prix"
        )
        
        assert context.session_type == "race"
        assert context.year == 2024
        assert context.race_name == "Monaco Grand Prix"
        assert context.additional_context == {}
    
    def test_agent_context_with_additional_data(self):
        """Test AgentContext with additional context."""
        context = AgentContext(
            session_type="qualifying",
            year=2024,
            race_name="Monaco Grand Prix",
            additional_context={"weather": "dry", "temperature": 25}
        )
        
        assert context.additional_context == {"weather": "dry", "temperature": 25}
    
    def test_agent_response_creation(self):
        """Test AgentResponse creation."""
        response = AgentResponse(
            agent_name="TestAgent",
            query="What is the optimal strategy?",
            response="One-stop strategy recommended",
            confidence=0.85,
            sources=["RAG: Monaco 2023", "Tool: get_race_results"],
            reasoning="Historical data shows one-stop is faster"
        )
        
        assert response.agent_name == "TestAgent"
        assert response.query == "What is the optimal strategy?"
        assert response.response == "One-stop strategy recommended"
        assert response.confidence == 0.85
        assert len(response.sources) == 2
        assert response.reasoning == "Historical data shows one-stop is faster"
        assert response.metadata == {}


class TestBaseAgent:
    """Test BaseAgent abstract class."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        from src.llm.models import LLMResponse
        
        mock_llm = Mock(spec=LLMProvider)
        
        # Create mock response matching LLMResponse structure
        mock_response = LLMResponse(
            content="This is a test response from the LLM.",
            model="test-model",
            provider="test-provider",
            tokens_input=10,
            tokens_output=20,
            cost_input=0.001,
            cost_output=0.002,
            latency_ms=100.0
        )
        
        # Mock async generate method
        async def mock_generate(*args, **kwargs):
            return mock_response
        
        mock_llm.generate = mock_generate
        return mock_llm
    
    @pytest.fixture
    def agent_config(self, mock_llm_provider):
        """Create agent configuration."""
        return AgentConfig(
            name="TestAgent",
            description="Test agent for unit tests",
            llm_provider=mock_llm_provider,
            temperature=0.7,
            max_tokens=2000
        )
    
    @pytest.fixture
    def test_agent(self, agent_config):
        """Create test agent instance."""
        return TestAgent(agent_config)
    
    @pytest.fixture
    def test_context(self):
        """Create test context."""
        return AgentContext(
            session_type="race",
            year=2024,
            race_name="Monaco Grand Prix"
        )
    
    def test_agent_initialization(self, test_agent):
        """Test agent initialization."""
        assert test_agent.config.name == "TestAgent"
        assert test_agent.context is None
        assert test_agent._tools == {}
        assert test_agent._conversation_history == []
    
    def test_set_context(self, test_agent, test_context):
        """Test setting agent context."""
        test_agent.set_context(test_context)
        
        assert test_agent.context == test_context
        assert test_agent.context.session_type == "race"
        assert test_agent.context.year == 2024
        assert test_agent.context.race_name == "Monaco Grand Prix"
    
    def test_register_tool(self, test_agent):
        """Test tool registration."""
        mock_tool = Mock(return_value={"result": "success"})
        
        test_agent.register_tool("test_tool", mock_tool)
        
        assert "test_tool" in test_agent._tools
        assert test_agent._tools["test_tool"] == mock_tool
    
    def test_call_tool_success(self, test_agent):
        """Test successful tool execution."""
        mock_tool = Mock(return_value={"lap_time": "1:23.456"})
        test_agent.register_tool("get_lap_times", mock_tool)
        
        result = test_agent.call_tool("get_lap_times", driver="VER", lap=1)
        
        assert result == {"lap_time": "1:23.456"}
        mock_tool.assert_called_once_with(driver="VER", lap=1)
    
    def test_call_tool_not_registered(self, test_agent):
        """Test calling unregistered tool raises error."""
        with pytest.raises(ValueError, match="not registered"):
            test_agent.call_tool("unknown_tool")
    
    def test_call_tool_when_disabled(self, test_agent):
        """Test calling tool when tools are disabled."""
        test_agent.config.enable_tools = False
        mock_tool = Mock()
        test_agent.register_tool("test_tool", mock_tool)
        
        with pytest.raises(ValueError, match="Tools disabled"):
            test_agent.call_tool("test_tool")
    
    def test_call_tool_execution_error(self, test_agent):
        """Test tool execution error handling."""
        mock_tool = Mock(side_effect=RuntimeError("Tool failed"))
        test_agent.register_tool("failing_tool", mock_tool)
        
        with pytest.raises(RuntimeError, match="Tool failed"):
            test_agent.call_tool("failing_tool")
    
    def test_validate_query_success(self, test_agent):
        """Test query validation success."""
        assert test_agent.validate_query("What is the best strategy?") is True
    
    def test_validate_query_failure(self, test_agent):
        """Test query validation failure."""
        assert test_agent.validate_query("") is False
        assert test_agent.validate_query("   ") is False
    
    def test_conversation_history(self, test_agent):
        """Test conversation history management."""
        test_agent._add_to_history("Query 1", "Response 1")
        test_agent._add_to_history("Query 2", "Response 2")
        
        assert len(test_agent._conversation_history) == 2
        assert test_agent._conversation_history[0]["user"] == "Query 1"
        assert test_agent._conversation_history[0]["assistant"] == "Response 1"
        assert test_agent._conversation_history[1]["user"] == "Query 2"
        assert test_agent._conversation_history[1]["assistant"] == "Response 2"
    
    def test_conversation_history_limit(self, test_agent):
        """Test conversation history keeps only last 10 exchanges."""
        for i in range(15):
            test_agent._add_to_history(f"Query {i}", f"Response {i}")
        
        assert len(test_agent._conversation_history) == 10
        assert test_agent._conversation_history[0]["user"] == "Query 5"
        assert test_agent._conversation_history[-1]["user"] == "Query 14"
    
    def test_clear_history(self, test_agent):
        """Test clearing conversation history."""
        test_agent._add_to_history("Query 1", "Response 1")
        test_agent._add_to_history("Query 2", "Response 2")
        
        test_agent.clear_history()
        
        assert test_agent._conversation_history == []
    
    def test_get_capabilities(self, test_agent):
        """Test getting agent capabilities."""
        capabilities = test_agent.get_capabilities()
        
        assert capabilities["name"] == "TestAgent"
        assert capabilities["description"] == "Test agent for unit tests"
        assert capabilities["tools"] == ["get_race_results", "get_lap_times"]
        assert capabilities["rag_enabled"] is True
        assert capabilities["tools_enabled"] is True
        assert "race" in capabilities["session_types"]
        assert "qualifying" in capabilities["session_types"]
    
    @pytest.mark.asyncio
    async def test_query_without_context(self, test_agent):
        """Test querying without setting context raises error."""
        with pytest.raises(ValueError, match="Context must be set"):
            await test_agent.query("What is the best strategy?")
    
    @pytest.mark.asyncio
    async def test_query_with_invalid_query(self, test_agent, test_context):
        """Test querying with invalid query raises error."""
        test_agent.set_context(test_context)
        
        with pytest.raises(ValueError, match="not suitable"):
            await test_agent.query("")
    
    @pytest.mark.asyncio
    async def test_query_success(self, test_agent, test_context, mock_llm_provider):
        """Test successful query execution."""
        test_agent.set_context(test_context)
        
        response = await test_agent.query("What is the optimal strategy?")
        
        assert isinstance(response, AgentResponse)
        assert response.agent_name == "TestAgent"
        assert response.query == "What is the optimal strategy?"
        assert "test response from the LLM" in response.response
        assert 0.0 <= response.confidence <= 1.0
        
        # Type narrowing for metadata
        assert response.metadata is not None
        metadata = response.metadata
        assert metadata["session_type"] == "race"
        assert metadata["year"] == 2024
        assert metadata["race_name"] == "Monaco Grand Prix"
    
    @pytest.mark.asyncio
    async def test_query_with_context_parameter(self, test_agent, test_context, mock_llm_provider):
        """Test query with context passed as parameter."""
        response = await test_agent.query(
            "What is the optimal strategy?",
            context=test_context
        )
        
        assert isinstance(response, AgentResponse)
        assert test_agent.context == test_context
    
    @pytest.mark.asyncio
    async def test_query_updates_history(self, test_agent, test_context):
        """Test that query updates conversation history."""
        test_agent.set_context(test_context)
        
        await test_agent.query("Query 1")
        await test_agent.query("Query 2")
        
        assert len(test_agent._conversation_history) == 2
        assert test_agent._conversation_history[0]["user"] == "Query 1"
        assert test_agent._conversation_history[1]["user"] == "Query 2"
    
    def test_build_full_prompt_with_context(self, test_agent, test_context):
        """Test prompt building includes context."""
        test_agent.set_context(test_context)
        
        prompt = test_agent._build_full_prompt("What is the strategy?")
        
        assert "Session Type: race" in prompt
        assert "Race: 2024 Monaco Grand Prix" in prompt
        assert "Current Query: What is the strategy?" in prompt
    
    def test_build_full_prompt_with_history(self, test_agent, test_context):
        """Test prompt building includes conversation history."""
        test_agent.set_context(test_context)
        test_agent._add_to_history("Previous query", "Previous response")
        
        prompt = test_agent._build_full_prompt("New query")
        
        assert "Recent Conversation:" in prompt
        assert "User: Previous query" in prompt
        assert "Assistant: Previous response" in prompt
    
    def test_build_full_prompt_limits_history(self, test_agent, test_context):
        """Test prompt includes only last 3 exchanges."""
        test_agent.set_context(test_context)
        
        for i in range(5):
            test_agent._add_to_history(f"Query {i}", f"Response {i}")
        
        prompt = test_agent._build_full_prompt("New query")
        
        # Should only include queries 2, 3, 4 (last 3)
        assert "Query 2" in prompt
        assert "Query 3" in prompt
        assert "Query 4" in prompt
        assert "Query 0" not in prompt
        assert "Query 1" not in prompt
    
    @pytest.mark.asyncio
    async def test_call_llm(self, test_agent, mock_llm_provider):
        """Test LLM calling."""
        system_prompt = "You are a test agent"
        user_prompt = "What is the strategy?"
        
        response = await test_agent._call_llm(system_prompt, user_prompt)
        
        assert response == "This is a test response from the LLM."
        # Verify generate was called with correct parameters
        # (Note: we can't easily assert_called_once on async mock)
    
    def test_build_response(self, test_agent, test_context):
        """Test building structured response."""
        test_agent.set_context(test_context)
        
        response = test_agent._build_response(
            query="Test query",
            llm_response="Test LLM response",
            sources=["source1", "source2"],
            reasoning="Test reasoning"
        )
        
        assert response.agent_name == "TestAgent"
        assert response.query == "Test query"
        assert response.response == "Test LLM response"
        assert response.sources == ["source1", "source2"]
        assert response.reasoning == "Test reasoning"
        assert 0.0 <= response.confidence <= 1.0
        assert response.metadata["session_type"] == "race"


class TestBaseAgentAbstractMethods:
    """Test that abstract methods must be implemented."""
    
    def test_cannot_instantiate_base_agent(self):
        """Test that BaseAgent cannot be instantiated directly."""
        mock_llm = Mock(spec=LLMProvider)
        config = AgentConfig(
            name="Test",
            description="Test",
            llm_provider=mock_llm
        )
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAgent(config)  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
