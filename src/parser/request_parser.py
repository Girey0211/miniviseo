import json
from openai import AsyncOpenAI
from .schemas import ParsedRequest
from ..config import OPENAI_API_KEY, OPENAI_MODEL, PARSER_PROMPT_PATH


class RequestParser:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load prompt template from file"""
        try:
            with open(PARSER_PROMPT_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback prompt if file not found
            return """You are a JSON extractor. Input: {input_text}
Return exactly one JSON object: {{"intent":"", "agent":"", "params":{{}}}}
Valid intents: list_files, read_file, write_note, list_notes, calendar_list, calendar_add, web_search, unknown"""
    
    async def parse_request(self, text: str) -> ParsedRequest:
        """
        Parse natural language text into structured ParsedRequest
        
        Args:
            text: User input text
            
        Returns:
            ParsedRequest object with intent, agent, and params
        """
        try:
            # Format prompt with user input
            prompt = self.prompt_template.format(input_text=text)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured data from text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract response content
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            parsed_data = json.loads(content)
            
            # Validate and create ParsedRequest
            parsed_request = ParsedRequest(
                intent=parsed_data.get("intent", "unknown"),
                agent=parsed_data.get("agent", "FallbackAgent"),
                params=parsed_data.get("params", {}),
                raw_text=text
            )
            
            return parsed_request
            
        except json.JSONDecodeError as e:
            # JSON parsing failed - return fallback
            return ParsedRequest(
                intent="unknown",
                agent="FallbackAgent",
                params={},
                raw_text=text
            )
        except Exception as e:
            # Any other error - return fallback
            return ParsedRequest(
                intent="unknown",
                agent="FallbackAgent",
                params={"error": str(e)},
                raw_text=text
            )


# Convenience function for direct usage
async def parse_request(text: str) -> ParsedRequest:
    """Parse user request text into structured format"""
    parser = RequestParser()
    return await parser.parse_request(text)
