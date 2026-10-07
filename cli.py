import sys
import json
from reasoner import Reasoner
from graph import KnowledgeGraph
import build


def main():
    print("Loading Knowledge Base...")
    try:
        graph = KnowledgeGraph.deserialize(build.KNOWLEDGE_STATE_PATH)
        print(f"Loaded {len(graph.peps)} PEPs and {len(graph.concepts)} concepts.")
    except FileNotFoundError:
        print(f"Knowledge state not found at {build.KNOWLEDGE_STATE_PATH}.")
        print("Please run 'python build.py' first to build the knowledge graph.")
        return

    reasoner = Reasoner(graph)

    print("\n" + "=" * 60)
    print("  Python Typing System Evolution - Knowledge Reasoner")
    print("=" * 60)
    print("Try asking questions like:")
    print("  - I want to add a new generic type feature for variables")
    print("  - Why did we reject making annotations evaluated eagerly?")
    print("  - Explain the evolution of type dictionaries")
    print("  - What would break if I change how Protocols work in PEP 544?")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("\nQuery > ")
            if user_input.strip().lower() in ["exit", "quit"]:
                break
            if not user_input.strip():
                continue

            print("\nReasoning over knowledge graph...\n")
            result = reasoner.reason(user_input)

            print(json.dumps(result, indent=2))

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error reasoning over input: {e}")

    print("Goodbye!")


if __name__ == "__main__":
    main()
