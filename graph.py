import json
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple, Any
from models import (
    PEPEntity, ConceptEntity, AuthorEntity, Relationship,
    EntityType, RelationType, PEP_EVOLUTION_CHAINS
)


class KnowledgeGraph:

    def __init__(self):
        self.peps: Dict[str, PEPEntity] = {}
        self.concepts: Dict[str, ConceptEntity] = {}
        self.authors: Dict[str, AuthorEntity] = {}
        self.relationships: List[Relationship] = []
        self.adjacency: Dict[str, List[Tuple[str, Relationship]]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[Tuple[str, Relationship]]] = defaultdict(list)

    def add_pep(self, pep: PEPEntity):
        self.peps[pep.entity_id()] = pep

    def add_concept(self, concept: ConceptEntity):
        self.concepts[concept.entity_id()] = concept

    def add_author(self, author: AuthorEntity):
        self.authors[author.entity_id()] = author

    def add_relationship(self, rel: Relationship):
        self.relationships.append(rel)
        self.adjacency[rel.source_id].append((rel.target_id, rel))
        self.reverse_adjacency[rel.target_id].append((rel.source_id, rel))

    def get_entity(self, entity_id: str) -> Optional[Any]:
        if entity_id in self.peps:
            return self.peps[entity_id]
        if entity_id in self.concepts:
            return self.concepts[entity_id]
        if entity_id in self.authors:
            return self.authors[entity_id]
        return None

    def get_neighbors(self, entity_id: str, relation_filter: str = None) -> List[Tuple[str, Relationship]]:
        neighbors = self.adjacency.get(entity_id, [])
        if relation_filter:
            return [(tid, r) for tid, r in neighbors if r.relation == relation_filter]
        return neighbors

    def get_incoming(self, entity_id: str, relation_filter: str = None) -> List[Tuple[str, Relationship]]:
        incoming = self.reverse_adjacency.get(entity_id, [])
        if relation_filter:
            return [(sid, r) for sid, r in incoming if r.relation == relation_filter]
        return incoming

    def get_peps_for_concept(self, concept_name: str) -> List[PEPEntity]:
        concept_id = f"concept-{concept_name}"
        pep_ids = set()
        for source_id, rel in self.get_incoming(concept_id):
            if rel.relation in [RelationType.INTRODUCES.value, RelationType.MOTIVATED_BY.value]:
                pep_ids.add(source_id)
        return [self.peps[pid] for pid in sorted(pep_ids) if pid in self.peps]

    def get_concepts_for_pep(self, pep_number: int) -> List[ConceptEntity]:
        pep_id = f"pep-{pep_number}"
        concept_ids = set()
        for target_id, rel in self.get_neighbors(pep_id):
            if rel.relation == RelationType.INTRODUCES.value and target_id.startswith("concept-"):
                concept_ids.add(target_id)
        return [self.concepts[cid] for cid in sorted(concept_ids) if cid in self.concepts]

    def get_pep_dependency_chain(self, pep_number: int) -> List[int]:
        pep_id = f"pep-{pep_number}"
        visited = set()
        chain = []
        queue = deque([pep_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            if current != pep_id and current in self.peps:
                chain.append(self.peps[current].number)

            for target_id, rel in self.get_neighbors(current):
                if rel.relation in [RelationType.REQUIRES.value, RelationType.EXTENDS.value]:
                    if target_id not in visited and target_id in self.peps:
                        queue.append(target_id)

        return sorted(chain)

    def get_pep_dependents(self, pep_number: int) -> List[int]:
        pep_id = f"pep-{pep_number}"
        dependents = set()

        for source_id, rel in self.get_incoming(pep_id):
            if rel.relation in [RelationType.REQUIRES.value, RelationType.EXTENDS.value,
                                RelationType.REFERENCES.value]:
                if source_id in self.peps:
                    dependents.add(self.peps[source_id].number)

        return sorted(dependents)

    def bfs_reachable(self, start_id: str, max_depth: int = 3, relation_filter: Set[str] = None) -> Dict[str, int]:
        visited = {}
        queue = deque([(start_id, 0)])

        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited[current] = depth

            for target_id, rel in self.get_neighbors(current):
                if relation_filter and rel.relation not in relation_filter:
                    continue
                if target_id not in visited:
                    queue.append((target_id, depth + 1))

            for source_id, rel in self.get_incoming(current):
                if relation_filter and rel.relation not in relation_filter:
                    continue
                if source_id not in visited:
                    queue.append((source_id, depth + 1))

        del visited[start_id]
        return visited

    def find_shortest_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
        if start_id == end_id:
            return [start_id]

        visited = {start_id}
        queue = deque([(start_id, [start_id])])

        while queue:
            current, path = queue.popleft()

            all_connected = []
            for tid, _ in self.get_neighbors(current):
                all_connected.append(tid)
            for sid, _ in self.get_incoming(current):
                all_connected.append(sid)

            for next_id in all_connected:
                if next_id == end_id:
                    return path + [next_id]
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))

        return None

    def get_evolution_timeline(self, concept_name: str) -> List[Dict[str, Any]]:
        timeline = []

        for chain_name, chain_peps in PEP_EVOLUTION_CHAINS.items():
            if concept_name in chain_name:
                for pep_num in chain_peps:
                    pep_id = f"pep-{pep_num}"
                    if pep_id in self.peps:
                        pep = self.peps[pep_id]
                        timeline.append({
                            "pep_number": pep.number,
                            "title": pep.title,
                            "status": pep.status,
                            "created": pep.created,
                            "python_version": pep.python_version,
                            "chain": chain_name
                        })

        peps_for_concept = self.get_peps_for_concept(concept_name)
        seen_nums = {t["pep_number"] for t in timeline}
        for pep in peps_for_concept:
            if pep.number not in seen_nums:
                timeline.append({
                    "pep_number": pep.number,
                    "title": pep.title,
                    "status": pep.status,
                    "created": pep.created,
                    "python_version": pep.python_version,
                    "chain": "direct_association"
                })

        timeline.sort(key=lambda x: x["pep_number"])
        return timeline

    def compute_pep_centrality(self) -> Dict[int, float]:
        scores = {}
        for pep_id, pep in self.peps.items():
            outgoing = len(self.adjacency.get(pep_id, []))
            incoming = len(self.reverse_adjacency.get(pep_id, []))
            scores[pep.number] = outgoing + incoming * 1.5
        return scores

    def find_related_peps_by_concepts(self, concept_names: List[str], exclude_peps: Set[int] = None) -> List[Tuple[int, float, List[str]]]:
        if exclude_peps is None:
            exclude_peps = set()

        pep_scores = defaultdict(lambda: {"score": 0.0, "matched": []})

        for concept_name in concept_names:
            peps = self.get_peps_for_concept(concept_name)
            for pep in peps:
                if pep.number not in exclude_peps:
                    pep_scores[pep.number]["score"] += 1.0
                    pep_scores[pep.number]["matched"].append(concept_name)

            concept_id = f"concept-{concept_name}"
            if concept_id in self.concepts:
                concept = self.concepts[concept_id]
                for dep in concept.depends_on:
                    dep_peps = self.get_peps_for_concept(dep)
                    for pep in dep_peps:
                        if pep.number not in exclude_peps:
                            pep_scores[pep.number]["score"] += 0.4
                            if dep not in pep_scores[pep.number]["matched"]:
                                pep_scores[pep.number]["matched"].append(f"{dep}(transitive)")

        results = [(num, data["score"], data["matched"]) for num, data in pep_scores.items()]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_rejected_ideas_for_concepts(self, concept_names: List[str]) -> List[Dict[str, Any]]:
        rejected_ideas = []
        for concept_name in concept_names:
            peps = self.get_peps_for_concept(concept_name)
            for pep in peps:
                if pep.rejected_ideas and len(pep.rejected_ideas.strip()) > 20:
                    rejected_ideas.append({
                        "pep_number": pep.number,
                        "pep_title": pep.title,
                        "concept": concept_name,
                        "rejected_ideas_excerpt": pep.rejected_ideas[:800]
                    })
        return rejected_ideas

    def topological_reading_order(self, pep_numbers: List[int]) -> List[int]:
        pep_set = set(pep_numbers)
        in_degree = defaultdict(int)
        adj = defaultdict(list)

        for num in pep_numbers:
            pep_id = f"pep-{num}"
            for target_id, rel in self.get_neighbors(pep_id):
                if rel.relation in [RelationType.REQUIRES.value, RelationType.EXTENDS.value]:
                    target_num = int(target_id.split("-")[1]) if target_id.startswith("pep-") else None
                    if target_num and target_num in pep_set:
                        adj[target_num].append(num)
                        in_degree[num] += 1

        for num in pep_numbers:
            if num not in in_degree:
                in_degree[num] = 0

        queue = deque([n for n in pep_numbers if in_degree[n] == 0])
        queue = deque(sorted(queue))
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)
            for neighbor in sorted(adj[current]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        remaining = [n for n in pep_numbers if n not in result]
        result.extend(sorted(remaining))
        return result

    def get_statistics(self) -> Dict[str, Any]:
        status_counts = defaultdict(int)
        for pep in self.peps.values():
            status_counts[pep.status] += 1

        category_counts = defaultdict(int)
        for concept in self.concepts.values():
            category_counts[concept.category] += 1

        relation_counts = defaultdict(int)
        for rel in self.relationships:
            relation_counts[rel.relation] += 1

        centrality = self.compute_pep_centrality()
        top_peps = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_peps": len(self.peps),
            "total_concepts": len(self.concepts),
            "total_authors": len(self.authors),
            "total_relationships": len(self.relationships),
            "pep_status_distribution": dict(status_counts),
            "concept_category_distribution": dict(category_counts),
            "relationship_type_distribution": dict(relation_counts),
            "most_connected_peps": [{"pep": num, "connections": score} for num, score in top_peps]
        }

    def serialize(self, filepath: str):
        state = {
            "metadata": {
                "description": "Knowledge graph of Python's type system evolution through PEPs",
                "domain": "Python typing PEPs",
                "subset": "28 PEPs covering the evolution of Python's type annotation system from PEP 3107 to PEP 742",
                "statistics": self.get_statistics()
            },
            "entities": {
                "peps": {pid: p.to_dict() for pid, p in self.peps.items()},
                "concepts": {cid: c.to_dict() for cid, c in self.concepts.items()},
                "authors": {aid: a.to_dict() for aid, a in self.authors.items()}
            },
            "relationships": [r.to_dict() for r in self.relationships],
            "evolution_chains": PEP_EVOLUTION_CHAINS
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    @classmethod
    def deserialize(cls, filepath: str) -> "KnowledgeGraph":
        with open(filepath, "r", encoding="utf-8") as f:
            state = json.load(f)

        graph = cls()

        for pid, pdata in state["entities"]["peps"].items():
            pep = PEPEntity(
                number=pdata["number"],
                title=pdata["title"],
                status=pdata["status"],
                pep_type=pdata["pep_type"],
                authors=pdata["authors"],
                created=pdata["created"],
                python_version=pdata["python_version"],
                requires_peps=pdata["requires_peps"],
                replaces_peps=pdata["replaces_peps"],
                superseded_by=pdata["superseded_by"],
                abstract=pdata["abstract"],
                motivation=pdata["motivation"],
                rationale=pdata["rationale"],
                rejected_ideas=pdata["rejected_ideas"],
                raw_references=pdata["raw_references"],
                matched_concepts=pdata["matched_concepts"],
                sections=pdata.get("sections", {})
            )
            graph.add_pep(pep)

        for cid, cdata in state["entities"]["concepts"].items():
            concept = ConceptEntity(
                name=cdata["name"],
                display_name=cdata["display_name"],
                description=cdata["description"],
                keywords=cdata["keywords"],
                category=cdata["category"],
                depends_on=cdata["depends_on"],
                introduced_in=cdata.get("introduced_in")
            )
            graph.add_concept(concept)

        for aid, adata in state["entities"]["authors"].items():
            author = AuthorEntity(
                name=adata["name"],
                normalized_name=adata["normalized_name"],
                peps_authored=adata["peps_authored"]
            )
            graph.add_author(author)

        for rdata in state["relationships"]:
            rel = Relationship(
                source_type=rdata["source_type"],
                source_id=rdata["source_id"],
                relation=rdata["relation"],
                target_type=rdata["target_type"],
                target_id=rdata["target_id"],
                weight=rdata.get("weight", 1.0),
                metadata=rdata.get("metadata", {})
            )
            graph.add_relationship(rel)

        return graph
