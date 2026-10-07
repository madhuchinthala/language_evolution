import os
import sys
from models import TARGET_PEPS
from parser import fetch_and_parse_all_peps
from graph import KnowledgeGraph

KNOWLEDGE_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_state.json")


def build_knowledge_graph(output_path: str = None) -> KnowledgeGraph:
    if output_path is None:
        output_path = KNOWLEDGE_STATE_PATH

    print("=" * 60)
    print("  Python Typing PEP Knowledge Graph Builder")
    print("=" * 60)

    print("\n[1/4] Fetching and parsing PEPs from GitHub...\n")
    peps, concepts, authors, relationships = fetch_and_parse_all_peps(TARGET_PEPS)

    print("\n[2/4] Constructing knowledge graph...\n")
    graph = KnowledgeGraph()

    for pep in peps:
        graph.add_pep(pep)

    for concept in concepts:
        graph.add_concept(concept)

    for author in authors.values():
        graph.add_author(author)

    for rel in relationships:
        graph.add_relationship(rel)

    print("\n[3/4] Computing graph statistics...\n")
    stats = graph.get_statistics()
    print(f"  PEPs:          {stats['total_peps']}")
    print(f"  Concepts:      {stats['total_concepts']}")
    print(f"  Authors:       {stats['total_authors']}")
    print(f"  Relationships: {stats['total_relationships']}")
    print(f"\n  PEP Status Distribution:")
    for status, count in stats["pep_status_distribution"].items():
        print(f"    {status}: {count}")
    print(f"\n  Most Connected PEPs:")
    for item in stats["most_connected_peps"]:
        pep_id = f"pep-{item['pep']}"
        title = graph.peps[pep_id].title if pep_id in graph.peps else f"PEP {item['pep']}"
        print(f"    PEP {item['pep']} ({title}): {item['connections']} connections")

    print(f"\n[4/4] Serializing knowledge state to {output_path}...\n")
    graph.serialize(output_path)
    file_size = os.path.getsize(output_path)
    print(f"  Knowledge state saved ({file_size:,} bytes)")

    print("\n" + "=" * 60)
    print("  Build complete.")
    print("=" * 60)

    return graph


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else KNOWLEDGE_STATE_PATH
    build_knowledge_graph(output)
