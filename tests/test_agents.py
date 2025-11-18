import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base import AgentBase


# Concrete implementation for testing
class TestAgent(AgentBase):
    """Test agent implementation"""
    
    async def handle(self, params):
        """Test implementation of handle"""
        return self._create_success_response(
            result={"test": "data"},
            message="Test successful"
        )


class TestAgentBase:
    """Test cases for AgentBase"""
    
    def test_agent_initialization(self):
        """Test agent can be initialized"""
        agent = TestAgent()
        assert agent.mcp is None
        assert agent.llm is None
    
    def test_agent_initialization_with_clients(self):
        """Test agent initialization with clients"""
        mock_mcp = "mock_mcp_client"
        mock_llm = "mock_llm_client"
        
        agent = TestAgent(mcp_client=mock_mcp, llm_client=mock_llm)
        assert agent.mcp == mock_mcp
        assert agent.llm == mock_llm
    
    @pytest.mark.asyncio
    async def test_handle_method_must_be_implemented(self):
        """Test that handle method must be implemented"""
        
        class IncompleteAgent(AgentBase):
            pass
        
        with pytest.raises(TypeError):
            agent = IncompleteAgent()
    
    @pytest.mark.asyncio
    async def test_handle_returns_dict(self):
        """Test that handle returns a dictionary"""
        agent = TestAgent()
        result = await agent.handle({})
        
        assert isinstance(result, dict)
        assert "status" in result
        assert "result" in result
    
    def test_create_success_response(self):
        """Test creating success response"""
        agent = TestAgent()
        response = agent._create_success_response(
            result={"data": "test"},
            message="Success"
        )
        
        assert response["status"] == "ok"
        assert response["result"] == {"data": "test"}
        assert response["message"] == "Success"
    
    def test_create_success_response_without_message(self):
        """Test creating success response without message"""
        agent = TestAgent()
        response = agent._create_success_response(result="test_data")
        
        assert response["status"] == "ok"
        assert response["result"] == "test_data"
        assert response["message"] == ""
    
    def test_create_error_response(self):
        """Test creating error response"""
        agent = TestAgent()
        response = agent._create_error_response(message="Test error")
        
        assert response["status"] == "error"
        assert response["result"] is None
        assert response["message"] == "Test error"
    
    def test_create_error_response_with_exception(self):
        """Test creating error response with exception"""
        agent = TestAgent()
        test_error = ValueError("Test exception")
        response = agent._create_error_response(
            message="Error occurred",
            error=test_error
        )
        
        assert response["status"] == "error"
        assert response["message"] == "Error occurred"
        assert "error_detail" in response
        assert "Test exception" in response["error_detail"]
    
    def test_get_agent_name(self):
        """Test getting agent name"""
        agent = TestAgent()
        assert agent.get_agent_name() == "TestAgent"
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_without_client(self):
        """Test respond_via_llm without LLM client"""
        agent = TestAgent()
        response = await agent.respond_via_llm("test prompt")
        
        assert response == "LLM client not available"
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_with_client(self):
        """Test respond_via_llm with LLM client"""
        agent = TestAgent(llm_client="mock_llm")
        response = await agent.respond_via_llm("test prompt")
        
        # Should return placeholder for now
        assert "Response for:" in response
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_with_context(self):
        """Test respond_via_llm with context"""
        agent = TestAgent(llm_client="mock_llm")
        context = {"key": "value"}
        response = await agent.respond_via_llm("test prompt", context=context)
        
        assert isinstance(response, str)


class TestAgentBaseAbstract:
    """Test abstract nature of AgentBase"""
    
    def test_cannot_instantiate_base_directly(self):
        """Test that AgentBase cannot be instantiated directly"""
        with pytest.raises(TypeError):
            agent = AgentBase()
    
    def test_subclass_must_implement_handle(self):
        """Test that subclass must implement handle method"""
        
        class BadAgent(AgentBase):
            """Agent without handle implementation"""
            pass
        
        with pytest.raises(TypeError):
            agent = BadAgent()
    
    @pytest.mark.asyncio
    async def test_valid_subclass_can_be_instantiated(self):
        """Test that valid subclass can be instantiated"""
        
        class GoodAgent(AgentBase):
            async def handle(self, params):
                return {"status": "ok", "result": None}
        
        agent = GoodAgent()
        assert isinstance(agent, AgentBase)
        result = await agent.handle({})
        assert result["status"] == "ok"
