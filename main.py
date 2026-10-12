
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

load_dotenv()


# Define the structure of the research output
class ResearchResult(BaseModel):
    topic: str = Field(description="The research topic")
    summary: str = Field(description="A detailed research summary")
    sources: list[str] = Field(description="Sources used for research")
    tools_used: list[str] = Field(description="Tools used by the agent")


# Initialize the language model
llm = ChatOpenAI(model="gpt-4o", temperature=0)


# Create the research agent
agent = create_agent(
    model=llm,
    tools=[],
    system_prompt="""
    You are a research assistant that helps generate research papers.

    Your responsibilities:
    - Understand the user's research topic.
    - Generate an informative, well-structured research summary.
    - Include sources only when they can be verified.
    - Record which tools were used.
    - Never invent citations or claim to have used tools that are unavailable.
    """,
    response_format=ResearchResult,
)


# Run the agent
response = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Write a research summary on the impact of AI on society."
        }
    ]
})


# Extract structured output
result = response["structured_response"]

print("\nTopic:", result.topic)
print("\nSummary:", result.summary)
print("\nSources:", result.sources)
print("\nTools Used:", result.tools_used)
