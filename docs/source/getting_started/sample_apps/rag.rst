Retrieval-Augmented Generation (RAG)
====================================

The following section describes how Arch can help you build faster, more smarter Retrieval-Augmented Generation (RAG) applications.

Intent Markers (Multi-Turn Chat)
----------------------------------

Developers struggle to handle follow-up questions, or clarifying questions from users in their AI applications. Specifically, when
users ask for modifications or additions to previous responses, their AI applications often generates entirely new responses instead
of adjusting the previous ones. Developers are facing challenges in maintaining context across interactions, despite using tools like
ConversationBufferMemory and chat_history from Langchain.

There are several documented cases of this issue, `here <https://www.reddit.com/r/ChatGPTPromptGenius/comments/17dzmpy/how_to_use_rag_with_conversation_history_for/?>`_,
`and here <https://www.reddit.com/r/LocalLLaMA/comments/18mqwg6/best_practice_for_rag_with_followup_chat/>`_ and `again here <https://www.reddit.com/r/LangChain/comments/1bajhg8/chat_with_rag_further_questions/>`_.

Arch helps developer with intent detection tracking. Arch uses its lightweight NLI and embedding-based intent detection models to know
if the user's last prompt represents a new intent or not. This way developers can easily build an intent tracker and only use a subset of prompts
to process from the history to improve the retrieval and speed of their applications.

.. literalinclude:: /_include/intent_detection.py
    :language: python
    :linenos:
    :lines: 77-
    :emphasize-lines: 15-22
    :caption: :download:`intent-detection-python-example.py </_include/intent_detection.py>`
