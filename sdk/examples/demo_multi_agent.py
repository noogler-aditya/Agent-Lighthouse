"""
Demo script showing Agent Lighthouse SDK usage
"""
import time
import random
import os
from agent_lighthouse import trace_agent, trace_tool, trace_llm, get_tracer


# Initialize tracer
tracer = get_tracer(
    base_url="http://localhost:8000",
    framework="demo",
    api_key=os.getenv("LIGHTHOUSE_API_KEY", "local-dev-key"),
)


@trace_tool("Web Search")
def search_web(query: str) -> list[dict]:
    """Simulated web search tool"""
    time.sleep(random.uniform(0.2, 0.5))
    return [
        {"title": f"Result 1 for {query}", "url": "https://example.com/1"},
        {"title": f"Result 2 for {query}", "url": "https://example.com/2"},
    ]


@trace_tool("Calculator")
def calculate(expression: str) -> float:
    """Simulated calculator tool"""
    time.sleep(random.uniform(0.1, 0.2))
    # For demo, just return a random number
    return random.uniform(1, 100)


@trace_llm("GPT-4 Call", model="gpt-4", cost_per_1k_prompt=0.03, cost_per_1k_completion=0.06)
def call_llm(prompt: str) -> dict:
    """Simulated LLM call"""
    time.sleep(random.uniform(0.5, 1.0))
    
    # Simulate token usage
    class Usage:
        prompt_tokens = random.randint(100, 500)
        completion_tokens = random.randint(50, 200)
    
    class Response:
        usage = Usage()
        content = f"LLM response to: {prompt[:50]}..."
    
    return Response()


@trace_agent("Research Agent")
def research_agent(topic: str) -> str:
    """Agent that researches a topic"""
    tracer = get_tracer()
    
    # Update state for inspection
    tracer.update_state(
        memory={"topic": topic, "status": "researching"},
        context={"agent": "research"},
        variables={"step": 1}
    )
    
    # Search for information
    results = search_web(topic)
    
    tracer.update_state(
        memory={"topic": topic, "results": len(results)},
        variables={"step": 2}
    )
    
    # Analyze with LLM
    analysis = call_llm(f"Analyze these results about {topic}: {results}")
    
    return analysis.content


@trace_agent("Writer Agent")
def writer_agent(topic: str, research: str) -> str:
    """Agent that writes content based on research"""
    tracer = get_tracer()
    
    tracer.update_state(
        memory={"topic": topic, "status": "writing"},
        context={"agent": "writer"},
        variables={"word_count": 0}
    )
    
    # Calculate some metric
    metric = calculate(f"quality_score({topic})")
    
    # Generate content
    content = call_llm(f"Write an article about {topic} using this research: {research}")
    
    tracer.update_state(
        variables={"word_count": 500, "quality": metric}
    )
    
    return content.content


@trace_agent("Editor Agent")
def editor_agent(content: str) -> str:
    """Agent that edits and improves content"""
    tracer = get_tracer()
    
    tracer.update_state(
        memory={"status": "editing"},
        context={"agent": "editor"}
    )
    
    # Edit with LLM
    edited = call_llm(f"Edit and improve this content: {content[:200]}")
    
    return edited.content


def run_demo():
    """Run the demo multi-agent workflow"""
    print("🔦 Agent Lighthouse Demo")
    print("=" * 50)
    print("Starting multi-agent workflow...")
    print("Open http://localhost:5173 to see the trace!")
    print("=" * 50)
    
    with tracer.trace(
        name="Content Creation Workflow",
        description="Demo workflow with Research, Writer, and Editor agents",
        metadata={"demo": True, "version": "1.0"}
    ) as trace_info:
        print(f"Trace ID: {trace_info['trace_id']}")
        # Research phase
        print("\n📚 Research Agent working...")
        research = research_agent("Artificial Intelligence trends 2024")
        print(f"   Research complete!")
        
        # Writing phase
        print("\n✍️  Writer Agent working...")
        content = writer_agent("AI Trends", research)
        print(f"   Draft complete!")
        
        # Editing phase
        print("\n📝 Editor Agent working...")
        final = editor_agent(content)
        print(f"   Editing complete!")
    
    print("\n" + "=" * 50)
    print("✅ Workflow complete!")
    print("Check the Agent Lighthouse dashboard to see the trace.")


if __name__ == "__main__":
    run_demo()
