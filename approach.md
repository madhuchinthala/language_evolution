# Approach: Language Evolution (Python Typing)

## The Chosen Data Subset
I chose to model the evolution of **Python's Static Typing System**. I selected a focused subset of 28 key PEPs, starting from PEP 3107 (Function Annotations) up to PEP 742 (TypeIs). 

I chose this specific subset because:
1. **High Interconnectivity**: The typing system was not designed in a single PEP. It evolved iteratively over 10+ years. Later PEPs constantly patch, extend, or replace earlier ones.
2. **Clear Concepts**: Typing introduces very clear conceptual entities (Generics, Unions, TypedDicts) that can be mapped across multiple proposals.
3. **Rich "Why" Data**: The typing PEPs contain extensive "Rejected Ideas" and "Rationale" sections because adding static types to a highly dynamic language is controversial and requires defending trade-offs.

## Entities and Relationships Modeled

I rejected using NLP libraries or LLMs to automatically extract a fuzzy knowledge graph. Instead, I manually modeled a rigid schema with three Entity types and ten Relationship types.

### Entities
1. **PEP**: Represents a physical proposal document (e.g., PEP 484).
2. **Concept**: A hand-crafted taxonomy of 31 typing concepts (e.g., `generics`, `typed_dict`, `type_narrowing`). These are independent of any single PEP.
3. **Author**: A person who contributed to a PEP.

### Relationships
- `INTRODUCES`: A PEP formally specifies a Concept.
- `REQUIRES` / `EXTENDS` / `REPLACES` / `SUPERSEDES`: Structural connections between PEPs indicating the evolution chain.
- `REFERENCES`: A weak connection where one PEP mentions another in its body text.
- `DEPENDS_ON`: A structural dependency between Concepts (e.g., `variadic_generics` depends on `generics`).
- `AUTHORED_BY`: Links PEPs to Authors.

### Reasoning Behind the Model
A pure document-to-document graph (PEP references PEP) is just a citation network, not a knowledge base. By introducing a curated set of **Concepts** as first-class entities in the middle, the graph becomes semantic. If PEP 655 modifies how TypedDicts work, and PEP 589 introduced them, they are linked not just by citations, but by the shared `typed_dict` concept. This allows the system to trace the history of an *idea* even if the documents don't explicitly link to each other.

## How the Knowledge Base Was Built

1. **Manual Taxonomy**: I defined the 31 core concepts and their dependencies in `models.py`.
2. **Data Ingestion**: A script (`build.py` / `parser.py`) downloads the raw `.txt`/`.rst` files for the target PEPs from GitHub.
3. **Parsing**: The parser extracts structural metadata from the headers (Requires, Replaces), and parses the text body to split out sections like "Abstract", "Rationale", and "Rejected Ideas".
4. **Linking**: The script scans the PEP text for keywords associated with the 31 Concepts to establish `INTRODUCES` relationships. It also extracts inline `PEP XXX` references to build the citation graph.
5. **Graph Construction**: The extracted data is loaded into a custom in-memory directed graph (`graph.py`) with adjacency list representations.
6. **Serialization**: The entire graph state is dumped to a standalone `knowledge_state.json` file.

**Tradeoffs**: By not using an NLP extraction tool, the concept mapping relies on simple keyword counting and manual overrides. It is less "smart" in edge cases but completely deterministic, perfectly debuggable, and strictly adheres to the rule of not automating the knowledge structuring itself.

## How the System Operates on New Inputs

When the system receives a new, unseen input (e.g., "I want to add a new generic type feature"):

1. **Classification**: It scores the input against signal words to determine if the user is making a `proposal`, asking for an `explanation`, exploring a concept (`exploration`), or asking about downstream `impact`.
2. **Concept Extraction**: It extracts recognized concepts from the user's input.
3. **Graph Traversal (No LLMs)**: Based on the extracted concepts, it traverses the graph. For a `proposal`:
    - It finds all historical PEPs related to those concepts.
    - It extracts "Rejected Ideas" from those specific past PEPs to build a list of *Historical Precedents* and *Potential Objections*.
    - It analyzes the `DEPENDS_ON` relations in the concept taxonomy to tell the user if their proposed feature relies on foundations that are still in "Draft" state.
    - It computes a topological reading order of the relevant PEPs so the user knows what to read first to understand the context.
4. **Structured Output**: It returns a rich JSON payload (not a flat text string) containing this reasoned data, which a UI could render into a dashboard.

## Next Steps

With more time, I would build:
1. **More Sophisticated Concept Matching**: Replace keyword counting with a better heuristic or embedding-based retrieval to map PEP text to Concepts, without sacrificing the rigid Entity schema.
2. **Time-Series Analysis**: The graph contains creation dates. I would add reasoning to answer questions like "How has the acceptance rate of typing PEPs changed over time?"
3. **Richer Author Impact**: Analyze which authors successfully push through breaking changes vs additive features.
