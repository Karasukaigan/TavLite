# ./src/llm_client.py
import openai
import threading
from typing import List, Dict, Optional, Generator

class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str = ""):
        """
        Initialize LLM client
        
        Args:
            base_url (str): API base URL, e.g., http://localhost:11434/v1
            api_key (str): API key
            model (str): Default model name
        """
        self.base_url = base_url or ""
        self.api_key = api_key or ""
        self.model = model or ""
        self.client = None
        if not self.api_key:
            for keyword in ['localhost', '127.0.0.1', '11434']:
                if keyword in self.base_url:
                    self.api_key = "no_api_key_required"
        if self.base_url:
            try: 
                self.client = openai.OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=60.0
                )
            except Exception:
                pass

    def new(self, base_url: str, api_key: str):
        """Create new client configuration"""
        self.base_url = base_url or ""
        self.api_key = api_key or ""
        if not self.base_url:
            return False
        if not self.api_key:
            for keyword in ['localhost', '127.0.0.1', '11434']:
                if keyword in self.base_url:
                    self.api_key = "no_api_key_required"
        try:
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=60.0
            )
            return True
        except Exception:
            return False

    def test_connection(self) -> bool:
        """Test connection"""
        try:
            self.client.models.list(timeout=10)
            return True
        except Exception:
            return False

    def get_model_list(self) -> List[str]:
        """
        Get model list

        Returns:
            List[str]: Model name list
        """
        try:
            models = self.client.models.list(timeout=10)
            return [model.id for model in models.data]
        except Exception:
            return []

    def chat(
        self,
        user_message: str,
        model: Optional[str] = None,
        image_base64: Optional[str] = None,
        system_prompt: str = "",
        context_messages: Optional[List[Dict]] = None,
        temperature: float = 1,
        num_predict: int = 32000,
        think: bool = True,
        stop_event: Optional[threading.Event] = None,
    ) -> Generator[str, None, None]:
        """
        Chat conversation

        Yields:
            str: Each time returns a token or special marker
        """
        if not think:
            user_message += "/no_think"

        # Build message list
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context_messages:
            messages.extend(context_messages)

        # Build user message
        if image_base64:
            user_content = [
                {"type": "text", "text": user_message},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }
            ]
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})

        selected_model = model or self.model
        if not selected_model:
            yield "__ERROR__ No model specified."
            return

        try:
            stream = self.client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=num_predict,
                stream=True,
                stream_options={
                    "include_usage": True
                },
                extra_body={
                    "think": think,
                    "enable_thinking": think
                }
            )

            is_thinking = True
            think_tag = True

            for chunk in stream:
                if stop_event and stop_event.is_set():
                    # Try to close the stream to immediately release LLM connection
                    if hasattr(stream, 'close'):
                        try:
                            stream.close()
                        except:
                            pass
                    break
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    reasoning = getattr(delta, 'reasoning', None)
                    content = getattr(delta, 'content', None)

                    if is_thinking and reasoning:
                        yield reasoning.replace("\n\n", "\n")

                    token = ""
                    if content:
                        if "<think>" in content:
                            think_tag = False
                        if "</think>" in content:
                            think_tag = True
                        if is_thinking and think_tag:
                            token += "__THINKING_FINISHED__"
                            is_thinking = False
                        token += content.replace("\n\n", "\n")
                        yield token

        except openai.APIConnectionError as e:
            yield f"__ERROR__ Connection failed: {e}"
        except openai.AuthenticationError as e:
            yield f"__ERROR__ Authentication failed: {e}"
        except openai.RateLimitError as e:
            yield f"__ERROR__ Rate limit exceeded: {e}"
        except openai.APIStatusError as e:
            yield f"__ERROR__ API error ({e.status_code}): {e.message}"
        except Exception as e:
            yield f"__ERROR__ Unexpected error: {e}"

if __name__ == '__main__':
    pass