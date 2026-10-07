import re
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple
from models import TYPING_CONCEPTS, RelationType, PEP_EVOLUTION_CHAINS
from graph import KnowledgeGraph


class Reasoner:

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self._concept_keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, List[str]]:
        index = defaultdict(list)
        for concept_name, data in TYPING_CONCEPTS.items():
            for keyword in data["keywords"]:
                index[keyword.lower()].append(concept_name)
            index[concept_name.replace("_", " ")].append(concept_name)
            index[data["display_name"].lower()].append(concept_name)
        return dict(index)

    def extract_concepts_from_input(self, text: str) -> List[Tuple[str, float]]:
        text_lower = text.lower()
        concept_scores = defaultdict(float)

        for keyword, concept_names in self._concept_keyword_index.items():
            if keyword in text_lower:
                for concept_name in concept_names:
                    length_bonus = len(keyword) / 20.0
                    concept_scores[concept_name] += 1.0 + length_bonus

        pep_mentions = re.findall(r"pep[\s-]*(\d+)", text_lower)
        for pep_num_str in pep_mentions:
            pep_num = int(pep_num_str)
            pep_id = f"pep-{pep_num}"
            if pep_id in self.graph.peps:
                pep = self.graph.peps[pep_id]
                for concept in pep.matched_concepts:
                    concept_scores[concept] += 2.0

        scored = [(name, score) for name, score in concept_scores.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def classify_input(self, text: str) -> str:
        text_lower = text.lower()

        proposal_signals = ["propose", "proposal", "new feature", "add support", "introduce",
                           "what if we", "should python", "why not", "could we add",
                           "i want to add", "feature request", "suggestion"]
        explanation_signals = ["why does", "why can't", "why is", "how come", "reason behind",
                              "explain why", "what happened", "why was", "history of",
                              "decision behind", "rationale"]
        exploration_signals = ["how does", "what is", "tell me about", "explain", "overview",
                              "understand", "learn about", "describe", "evolution of"]
        impact_signals = ["what depends", "impact", "affected by", "consequence",
                         "what would break", "downstream", "what uses"]

        scores = {
            "proposal": sum(1 for s in proposal_signals if s in text_lower),
            "explanation": sum(1 for s in explanation_signals if s in text_lower),
            "exploration": sum(1 for s in exploration_signals if s in text_lower),
            "impact": sum(1 for s in impact_signals if s in text_lower)
        }

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "exploration"
        return best

    def analyze_proposal(self, text: str) -> Dict[str, Any]:
        matched_concepts = self.extract_concepts_from_input(text)
        concept_names = [name for name, _ in matched_concepts[:8]]
        input_type = "proposal"

        related_peps = self.graph.find_related_peps_by_concepts(concept_names)
        top_related = related_peps[:10]

        rejected_ideas = self.graph.get_rejected_ideas_for_concepts(concept_names)

        potential_objections = self._infer_objections(concept_names, rejected_ideas)

        all_related_nums = [num for num, _, _ in top_related]
        reading_order = self.graph.topological_reading_order(all_related_nums)

        dependency_analysis = self._analyze_dependencies(concept_names)

        feasibility = self._assess_feasibility(concept_names, related_peps, rejected_ideas)

        evolution_context = self._build_evolution_context(concept_names)

        similar_patterns = self._find_similar_patterns(text, concept_names)

        return {
            "analysis_type": input_type,
            "input_summary": text[:200],
            "matched_concepts": [
                {
                    "concept": name,
                    "relevance_score": round(score, 2),
                    "display_name": TYPING_CONCEPTS[name]["display_name"],
                    "description": TYPING_CONCEPTS[name]["description"]
                }
                for name, score in matched_concepts[:8]
            ],
            "related_peps": [
                {
                    "pep_number": num,
                    "title": self.graph.peps[f"pep-{num}"].title if f"pep-{num}" in self.graph.peps else f"PEP {num}",
                    "status": self.graph.peps[f"pep-{num}"].status if f"pep-{num}" in self.graph.peps else "unknown",
                    "relevance_score": round(score, 2),
                    "matched_via": matched
                }
                for num, score, matched in top_related
            ],
            "historical_precedent": {
                "rejected_ideas_from_related_peps": rejected_ideas[:5],
                "potential_objections": potential_objections,
                "similar_past_patterns": similar_patterns
            },
            "dependency_analysis": dependency_analysis,
            "feasibility_assessment": feasibility,
            "evolution_context": evolution_context,
            "suggested_reading_order": [
                {
                    "pep_number": num,
                    "title": self.graph.peps[f"pep-{num}"].title if f"pep-{num}" in self.graph.peps else f"PEP {num}"
                }
                for num in reading_order
            ]
        }

    def explore_concept(self, text: str) -> Dict[str, Any]:
        matched_concepts = self.extract_concepts_from_input(text)
        if not matched_concepts:
            return {"analysis_type": "exploration", "error": "No matching concepts found in the knowledge base for the given input."}

        primary_concept = matched_concepts[0][0]
        concept_entity = self.graph.concepts.get(f"concept-{primary_concept}")
        if not concept_entity:
            return {"analysis_type": "exploration", "error": f"Concept '{primary_concept}' not found."}

        timeline = self.graph.get_evolution_timeline(primary_concept)

        peps = self.graph.get_peps_for_concept(primary_concept)
        pep_details = []
        for pep in peps:
            dependents = self.graph.get_pep_dependents(pep.number)
            pep_details.append({
                "pep_number": pep.number,
                "title": pep.title,
                "status": pep.status,
                "python_version": pep.python_version,
                "abstract": pep.abstract[:300] if pep.abstract else "",
                "dependents": dependents
            })

        related_concepts = []
        concept_id = f"concept-{primary_concept}"
        reachable = self.graph.bfs_reachable(concept_id, max_depth=2)
        for entity_id, depth in sorted(reachable.items(), key=lambda x: x[1]):
            if entity_id.startswith("concept-") and entity_id != concept_id:
                rel_concept = self.graph.concepts.get(entity_id)
                if rel_concept:
                    related_concepts.append({
                        "name": rel_concept.display_name,
                        "distance": depth,
                        "category": rel_concept.category,
                        "description": rel_concept.description
                    })

        current_status = self._determine_concept_maturity(primary_concept, peps)

        dependency_tree = self._build_concept_dependency_tree(primary_concept, set())

        return {
            "analysis_type": "exploration",
            "concept": {
                "name": concept_entity.display_name,
                "internal_name": primary_concept,
                "description": concept_entity.description,
                "category": concept_entity.category,
                "maturity": current_status
            },
            "evolution_timeline": timeline,
            "peps_involved": pep_details,
            "related_concepts": related_concepts[:10],
            "dependency_tree": dependency_tree,
            "all_matched_concepts": [
                {"concept": name, "score": round(score, 2)}
                for name, score in matched_concepts[:5]
            ]
        }

    def explain_design(self, text: str) -> Dict[str, Any]:
        matched_concepts = self.extract_concepts_from_input(text)
        concept_names = [name for name, _ in matched_concepts[:5]]

        pep_mentions = re.findall(r"pep[\s-]*(\d+)", text.lower())
        target_peps = [int(n) for n in pep_mentions]

        if not target_peps and concept_names:
            related = self.graph.find_related_peps_by_concepts(concept_names)
            target_peps = [num for num, _, _ in related[:3]]

        explanations = []
        for pep_num in target_peps:
            pep_id = f"pep-{pep_num}"
            if pep_id not in self.graph.peps:
                continue
            pep = self.graph.peps[pep_id]

            deps = self.graph.get_pep_dependency_chain(pep_num)
            dependents = self.graph.get_pep_dependents(pep_num)
            concepts = self.graph.get_concepts_for_pep(pep_num)

            design_context = {
                "pep_number": pep.number,
                "title": pep.title,
                "status": pep.status,
                "authors": pep.authors,
                "python_version": pep.python_version,
                "motivation": pep.motivation[:500] if pep.motivation else "Not available in parsed data",
                "rationale": pep.rationale[:500] if pep.rationale else "Not available in parsed data",
                "rejected_alternatives": pep.rejected_ideas[:500] if pep.rejected_ideas else "None documented",
                "depends_on_peps": [
                    {"number": d, "title": self.graph.peps[f"pep-{d}"].title}
                    for d in deps if f"pep-{d}" in self.graph.peps
                ],
                "influenced_peps": [
                    {"number": d, "title": self.graph.peps[f"pep-{d}"].title}
                    for d in dependents if f"pep-{d}" in self.graph.peps
                ],
                "concepts_introduced": [
                    {"name": c.display_name, "description": c.description}
                    for c in concepts
                ]
            }
            explanations.append(design_context)

        tradeoff_analysis = self._analyze_tradeoffs(target_peps, concept_names)

        return {
            "analysis_type": "explanation",
            "query": text[:200],
            "matched_concepts": [{"concept": n, "score": round(s, 2)} for n, s in matched_concepts[:5]],
            "design_explanations": explanations,
            "tradeoff_analysis": tradeoff_analysis
        }

    def analyze_impact(self, text: str) -> Dict[str, Any]:
        pep_mentions = re.findall(r"pep[\s-]*(\d+)", text.lower())
        matched_concepts = self.extract_concepts_from_input(text)
        concept_names = [name for name, _ in matched_concepts[:5]]

        impact_map = defaultdict(lambda: {"direct": [], "transitive": []})

        for pep_num_str in pep_mentions:
            pep_num = int(pep_num_str)
            pep_id = f"pep-{pep_num}"
            if pep_id not in self.graph.peps:
                continue

            direct_dependents = self.graph.get_pep_dependents(pep_num)
            impact_map[pep_num]["direct"] = direct_dependents

            transitive = set()
            for dep in direct_dependents:
                further = self.graph.get_pep_dependents(dep)
                transitive.update(further)
            transitive -= set(direct_dependents)
            transitive.discard(pep_num)
            impact_map[pep_num]["transitive"] = sorted(transitive)

        concept_impact = {}
        for concept_name in concept_names:
            peps = self.graph.get_peps_for_concept(concept_name)
            concept_impact[concept_name] = {
                "peps_count": len(peps),
                "peps": [{"number": p.number, "title": p.title, "status": p.status} for p in peps],
                "dependent_concepts": [
                    dep_name for dep_name, dep_data in TYPING_CONCEPTS.items()
                    if concept_name in dep_data["depends_on"]
                ]
            }

        return {
            "analysis_type": "impact",
            "query": text[:200],
            "pep_impact": {
                str(num): {
                    "pep_title": self.graph.peps[f"pep-{num}"].title if f"pep-{num}" in self.graph.peps else f"PEP {num}",
                    "directly_affected": data["direct"],
                    "transitively_affected": data["transitive"],
                    "total_reach": len(data["direct"]) + len(data["transitive"])
                }
                for num, data in impact_map.items()
            },
            "concept_impact": concept_impact
        }

    def reason(self, text: str) -> Dict[str, Any]:
        input_type = self.classify_input(text)

        if input_type == "proposal":
            return self.analyze_proposal(text)
        elif input_type == "explanation":
            return self.explain_design(text)
        elif input_type == "impact":
            return self.analyze_impact(text)
        else:
            return self.explore_concept(text)

    def _infer_objections(self, concept_names: List[str], rejected_ideas: List[Dict]) -> List[Dict[str, str]]:
        objections = []
        objection_patterns = {
            "complexity": ["complex", "complicated", "hard to understand", "confusing", "difficult"],
            "backward_compatibility": ["backward", "breaking change", "incompatible", "migration"],
            "runtime_performance": ["performance", "overhead", "slow", "runtime cost", "memory"],
            "redundancy": ["already possible", "duplicate", "redundant", "alternative exists"],
            "scope_creep": ["scope", "too broad", "too many changes", "incremental"],
            "readability": ["readable", "readability", "clarity", "ugly syntax", "pythonic"]
        }

        for item in rejected_ideas:
            text_lower = item.get("rejected_ideas_excerpt", "").lower()
            for obj_type, keywords in objection_patterns.items():
                if any(kw in text_lower for kw in keywords):
                    objections.append({
                        "objection_type": obj_type,
                        "source_pep": item["pep_number"],
                        "context": f"Related objection found in PEP {item['pep_number']} ({item['pep_title']})"
                    })

        seen_types = set()
        deduped = []
        for obj in objections:
            key = (obj["objection_type"], obj["source_pep"])
            if key not in seen_types:
                seen_types.add(key)
                deduped.append(obj)

        return deduped

    def _analyze_dependencies(self, concept_names: List[str]) -> Dict[str, Any]:
        established = []
        missing = []

        for concept_name in concept_names:
            concept_id = f"concept-{concept_name}"
            if concept_id in self.graph.concepts:
                concept = self.graph.concepts[concept_id]
                peps = self.graph.get_peps_for_concept(concept_name)
                has_final = any(p.status in ["Final", "Accepted"] for p in peps)
                if has_final:
                    established.append(concept.display_name)
                else:
                    missing.append(concept.display_name)
            else:
                missing.append(concept_name)

        prerequisite_concepts = set()
        for concept_name in concept_names:
            if concept_name in TYPING_CONCEPTS:
                for dep in TYPING_CONCEPTS[concept_name]["depends_on"]:
                    if dep not in concept_names:
                        prerequisite_concepts.add(dep)

        return {
            "established_foundations": established,
            "potentially_missing": missing,
            "prerequisite_concepts": [
                {
                    "concept": TYPING_CONCEPTS[dep]["display_name"],
                    "status": "established" if any(
                        p.status in ["Final", "Accepted"]
                        for p in self.graph.get_peps_for_concept(dep)
                    ) else "in_progress"
                }
                for dep in prerequisite_concepts if dep in TYPING_CONCEPTS
            ]
        }

    def _assess_feasibility(self, concept_names: List[str], related_peps: List, rejected_ideas: List) -> Dict[str, Any]:
        positive_signals = []
        negative_signals = []

        for concept_name in concept_names:
            peps = self.graph.get_peps_for_concept(concept_name)
            accepted = [p for p in peps if p.status in ["Final", "Accepted"]]
            rejected = [p for p in peps if p.status in ["Rejected", "Withdrawn"]]

            if accepted:
                positive_signals.append(f"Active development in '{TYPING_CONCEPTS.get(concept_name, {}).get('display_name', concept_name)}' area with {len(accepted)} accepted PEP(s)")
            if rejected:
                negative_signals.append(f"Previous rejections in '{TYPING_CONCEPTS.get(concept_name, {}).get('display_name', concept_name)}' area: {len(rejected)} rejected PEP(s)")

        dep_analysis = self._analyze_dependencies(concept_names)
        if dep_analysis["established_foundations"]:
            positive_signals.append(f"Prerequisites already established: {', '.join(dep_analysis['established_foundations'][:3])}")
        if dep_analysis["potentially_missing"]:
            negative_signals.append(f"Some foundations may need work: {', '.join(dep_analysis['potentially_missing'][:3])}")

        if rejected_ideas:
            negative_signals.append(f"Found {len(rejected_ideas)} related rejected idea(s) in past PEPs to be aware of")

        total_signals = len(positive_signals) + len(negative_signals)
        if total_signals == 0:
            score = 0.5
        else:
            score = len(positive_signals) / total_signals

        return {
            "feasibility_score": round(score, 2),
            "positive_signals": positive_signals,
            "negative_signals": negative_signals,
            "assessment": "likely_feasible" if score >= 0.6 else "needs_careful_consideration" if score >= 0.3 else "significant_challenges"
        }

    def _build_evolution_context(self, concept_names: List[str]) -> List[Dict[str, Any]]:
        context = []
        for concept_name in concept_names[:3]:
            timeline = self.graph.get_evolution_timeline(concept_name)
            if timeline:
                context.append({
                    "concept": TYPING_CONCEPTS.get(concept_name, {}).get("display_name", concept_name),
                    "evolution_steps": len(timeline),
                    "timeline": timeline
                })
        return context

    def _find_similar_patterns(self, text: str, concept_names: List[str]) -> List[Dict[str, str]]:
        patterns = []
        text_lower = text.lower()

        syntax_keywords = ["syntax", "operator", "symbol", "shorthand", "sugar"]
        safety_keywords = ["safe", "safety", "prevent", "error", "catch", "validate"]
        ergonomic_keywords = ["convenient", "ergonomic", "easier", "simpler", "less boilerplate"]

        for chain_name, chain_peps in PEP_EVOLUTION_CHAINS.items():
            chain_concepts_overlap = False
            for concept_name in concept_names:
                if concept_name in chain_name or any(
                    concept_name in (self.graph.peps.get(f"pep-{pn}", None) or type('X', (), {'matched_concepts': []})).matched_concepts
                    for pn in chain_peps
                ):
                    chain_concepts_overlap = True
                    break

            if chain_concepts_overlap:
                pattern_type = "related_evolution"
                if any(kw in text_lower for kw in syntax_keywords):
                    pattern_type = "syntax_evolution"
                elif any(kw in text_lower for kw in safety_keywords):
                    pattern_type = "safety_improvement"
                elif any(kw in text_lower for kw in ergonomic_keywords):
                    pattern_type = "ergonomic_improvement"

                patterns.append({
                    "pattern_type": pattern_type,
                    "chain": chain_name,
                    "peps_in_chain": chain_peps,
                    "description": f"Evolution chain '{chain_name}' follows a similar trajectory"
                })

        return patterns[:5]

    def _determine_concept_maturity(self, concept_name: str, peps: list) -> str:
        if not peps:
            return "theoretical"
        statuses = [p.status for p in peps]
        if all(s == "Final" for s in statuses):
            return "stable"
        if any(s == "Final" for s in statuses):
            return "established_and_evolving"
        if any(s in ["Accepted", "Provisional"] for s in statuses):
            return "recently_accepted"
        if any(s == "Draft" for s in statuses):
            return "under_development"
        return "historical"

    def _build_concept_dependency_tree(self, concept_name: str, visited: Set[str]) -> Dict[str, Any]:
        if concept_name in visited:
            return {"name": concept_name, "circular_reference": True}
        visited.add(concept_name)

        concept_data = TYPING_CONCEPTS.get(concept_name, {})
        children = []
        for dep in concept_data.get("depends_on", []):
            children.append(self._build_concept_dependency_tree(dep, visited.copy()))

        dependents = [
            name for name, data in TYPING_CONCEPTS.items()
            if concept_name in data.get("depends_on", [])
        ]

        return {
            "name": concept_data.get("display_name", concept_name),
            "internal_name": concept_name,
            "category": concept_data.get("category", "unknown"),
            "foundations": children,
            "enables": [TYPING_CONCEPTS[d]["display_name"] for d in dependents]
        }

    def _analyze_tradeoffs(self, pep_numbers: List[int], concept_names: List[str]) -> List[Dict[str, str]]:
        tradeoffs = []

        for pep_num in pep_numbers:
            pep_id = f"pep-{pep_num}"
            if pep_id not in self.graph.peps:
                continue
            pep = self.graph.peps[pep_id]

            if pep.rejected_ideas:
                tradeoffs.append({
                    "pep": pep_num,
                    "type": "alternatives_considered",
                    "detail": f"PEP {pep_num} considered and rejected alternatives documented in the PEP"
                })

            dependents = self.graph.get_pep_dependents(pep_num)
            if len(dependents) > 2:
                tradeoffs.append({
                    "pep": pep_num,
                    "type": "high_influence",
                    "detail": f"PEP {pep_num} influenced {len(dependents)} subsequent PEPs, indicating foundational design decisions"
                })

            deps = self.graph.get_pep_dependency_chain(pep_num)
            if len(deps) > 3:
                tradeoffs.append({
                    "pep": pep_num,
                    "type": "deep_dependency",
                    "detail": f"PEP {pep_num} has a deep dependency chain of {len(deps)} PEPs, showing evolutionary complexity"
                })

        return tradeoffs
