from typing import Any, Dict, List, Optional, Sequence, Tuple

from transformers import PreTrainedTokenizer


class KFCTemplate:
    def __init__(self, handler) -> None:
        self.handler = handler

    def encode_oneturn(
        self,
        tokenizer: "PreTrainedTokenizer",
        messages: Sequence[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[List[int], List[int]]:
        r"""
        Returns a single pair of token ids representing prompt and response respectively.
        """
        encoded_messages = self._encode(tokenizer, messages, tools)
        prompt_ids = []
        for encoded_ids in encoded_messages[:-1]:
            prompt_ids += encoded_ids

        answer_ids = encoded_messages[-1]
        return prompt_ids, answer_ids

    def encode_multiturn(
        self,
        tokenizer: "PreTrainedTokenizer",
        messages: Sequence[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Tuple[List[int], List[int]]]:
        r"""
        Returns multiple pairs of token ids representing prompts and responses respectively.
        """
        encoded_messages = self._encode(tokenizer, messages, tools)
        return [(encoded_messages[i], encoded_messages[i + 1]) for i in range(0, len(encoded_messages), 2)]

    def _encode(
        self,
        tokenizer: "PreTrainedTokenizer",
        messages: Sequence[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> List[List[int]]:
        r"""
        Encodes formatted inputs to pairs of token ids.
        Turn 0: system + query          resp
        Turn t: sep + query             resp
        """
        encoded_messages = []
        for i, message in enumerate(messages):
            elements = []

            if i == 0 and tools is not None:
                elements += self.handler._format_system(tools)

            if message.role == "user":
                elements += self.handler._format_user(content=message.content)
            elif message.role == "assistant":
                elements += self.handler._format_assistant(content=message.content)
            elif message.role == "observation":
                elements += self.handler._format_observation(content=message.content)
            elif message.role == "function_call":
                elements += self.handler._format_function(content=message.content)
            else:
                raise NotImplementedError("Unexpected role: {}".format(message.role))

            encoded_messages.append(self._convert_elements_to_ids(tokenizer, elements))

        return encoded_messages

    def _convert_elements_to_ids(self, tokenizer: "PreTrainedTokenizer", elements: List[List[int]]) -> List[int]:
        r"""
        Converts elements to token ids.
        """
        token_ids = []
        for elem in elements:
            if isinstance(elem, str):
                if len(elem) != 0:
                    token_ids += tokenizer.encode(elem, add_special_tokens=False)
            elif isinstance(elem, dict):
                token_ids += [tokenizer.convert_tokens_to_ids(elem.get("token"))]
            elif isinstance(elem, set):
                if "bos_token" in elem and tokenizer.bos_token_id is not None:
                    token_ids += [tokenizer.bos_token_id]
                elif "eos_token" in elem and tokenizer.eos_token_id is not None:
                    token_ids += [tokenizer.eos_token_id]
            else:
                raise ValueError("Input must be string, set[str] or dict[str, str], got {}".format(type(elem)))

        return token_ids
