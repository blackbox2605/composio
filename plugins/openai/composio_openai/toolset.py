"""
OpenAI tool spec.
"""

import json
import typing as t

from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from composio.client.enums import Action, App, Tag
from composio.constants import DEFAULT_ENTITY_ID
from composio.tools import ComposioToolSet as BaseComposioToolSet
from composio.tools.schema import OpenAISchema, SchemaType


class ComposioToolSet(BaseComposioToolSet):
    """
    Composio toolset for OpenAI framework.

    Example:
    ```python
        import dotenv
        from composio_openai import App, ComposioToolset
        from openai import OpenAI


        # Load environment variables from .env
        dotenv.load_dotenv()

        # Initialize tools.
        openai_client = OpenAI()
        composio_tools = ComposioToolset()

        # Define task.
        task = "Star a repo SamparkAI/composio_sdk on GitHub"

        # Get GitHub tools that are pre-configured
        actions = composio_toolset.get_tools(tools=[App.GITHUB])

        # Get response from the LLM
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            tools=actions,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": task},
            ],
        )
        print(response)

        # Execute the function calls.
        result = composio_tools.handle_calls(response)
        print(result)
    ```
    """

    def __init__(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        entity_id: str = DEFAULT_ENTITY_ID,
    ) -> None:
        """
        Initialize composio toolset.

        :param api_key: Composio API key
        :param base_url: Base URL for the Composio API server
        :param entity_id: Entity ID for making function calls
        """
        super().__init__(
            api_key,
            base_url,
            runtime="openai",
            entity_id=entity_id,
        )
        self.schema = SchemaType.OPENAI

    def validate_entity_id(self, entity_id: str) -> str:
        """Validate entity ID."""
        if (
            self.entity_id != DEFAULT_ENTITY_ID
            and entity_id != DEFAULT_ENTITY_ID
            and self.entity_id != entity_id
        ):
            raise ValueError(
                "Seperate `entity_id` can not be provided during "
                "intialization and handelling tool calls"
            )
        elif self.entity_id != DEFAULT_ENTITY_ID:
            entity_id = self.entity_id
        return entity_id

    def get_actions(
        self, actions: t.Sequence[Action]
    ) -> t.List[ChatCompletionToolParam]:
        """
        Get composio tools wrapped as OpenAI `ChatCompletionToolParam` objects.

        :param actions: List of actions to wrap
        :return: Composio tools wrapped as `ChatCompletionToolParam` objects
        """
        return [
            ChatCompletionToolParam(
                **t.cast(
                    OpenAISchema,
                    self.schema.format(
                        schema.model_dump(
                            exclude_none=True,
                        )
                    ),
                ).model_dump()
            )
            for schema in self.client.actions.get(actions=actions)
        ]

    def get_tools(
        self,
        apps: t.Sequence[App],
        tags: t.Optional[t.List[t.Union[str, Tag]]] = None,
    ) -> t.Sequence[ChatCompletionToolParam]:
        """
        Get composio tools wrapped as OpenAI `ChatCompletionToolParam` objects.

        :param apps: List of apps to wrap
        :param tags: Filter the apps by given tags
        :return: Composio tools wrapped as `ChatCompletionToolParam` objects
        """
        return [
            ChatCompletionToolParam(
                **t.cast(
                    OpenAISchema,
                    self.schema.format(
                        schema.model_dump(
                            exclude_none=True,
                        )
                    ),
                ).model_dump()
            )
            for schema in self.client.actions.get(apps=apps, tags=tags)
        ]

    def execute_tool_call(
        self,
        tool_call: ChatCompletionMessageToolCall,
        entity_id: str = DEFAULT_ENTITY_ID,
    ) -> t.Dict:
        """
        Execute a tool call.

        :param tool_call: Tool call metadata.
        :param entity_id: Entity ID.
        :return: Object containing output data from the tool call.
        """
        return self.execute_action(
            action=Action.from_action(name=tool_call.function.name),
            params=json.loads(tool_call.function.arguments),
            entity_id=entity_id,
        )

    def handle_tool_calls(
        self,
        response: ChatCompletion,
        entity_id: str = DEFAULT_ENTITY_ID,
    ) -> t.List[t.Dict]:
        """
        Handle tool calls from OpenAI chat completion object.

        :param response: Chat completion object from
                        openai.OpenAI.chat.completions.create function call
        :param entity_id: Entity ID.
        :return: A list of output objects from the function calls.
        """
        entity_id = self.validate_entity_id(entity_id)
        outputs = []
        if response.choices:
            for choice in response.choices:
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        outputs.append(
                            self.execute_tool_call(
                                tool_call=tool_call,
                                entity_id=entity_id,
                            )
                        )
        return outputs