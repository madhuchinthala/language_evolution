import re
import os
import time
import requests
from typing import Dict, List, Tuple, Optional
from models import (
    PEPEntity, ConceptEntity, AuthorEntity, Relationship,
    EntityType, RelationType, TYPING_CONCEPTS, TARGET_PEPS,
    PEP_CONCEPT_OVERRIDES
)


RAW_PEP_URL_PATTERNS = [
    "https://raw.githubusercontent.com/python/peps/main/peps/pep-{number:04d}.rst",
    "https://raw.githubusercontent.com/python/peps/main/pep-{number:04d}.txt",
]


def fetch_pep_raw(pep_number: int, cache_dir: str = "data/peps") -> Optional[str]:
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"pep-{pep_number:04d}.txt")

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    for pattern in RAW_PEP_URL_PATTERNS:
        url = pattern.format(number=pep_number)
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                content = resp.text
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return content
        except requests.RequestException:
            continue
        time.sleep(0.3)

    return None


def parse_pep_header(raw_text: str) -> Dict[str, str]:
    headers = {}
    lines = raw_text.split("\n")
    current_key = None
    current_value = []

    for line in lines:
        if line.strip() == "" and current_key:
            headers[current_key] = " ".join(current_value).strip()
            current_key = None
            current_value = []
            continue

        if re.match(r"^[A-Za-z][A-Za-z0-9-]*:\s", line):
            if current_key:
                headers[current_key] = " ".join(current_value).strip()
            parts = line.split(":", 1)
            current_key = parts[0].strip().lower().replace("-", "_")
            current_value = [parts[1].strip()]
        elif current_key and (line.startswith("  ") or line.startswith("\t")):
            current_value.append(line.strip())
        elif line.strip().startswith("===") or line.strip().startswith("---"):
            continue
        elif current_key is None and not headers:
            continue
        else:
            if current_key:
                headers[current_key] = " ".join(current_value).strip()
                current_key = None
                current_value = []
            break

    if current_key:
        headers[current_key] = " ".join(current_value).strip()

    return headers


def extract_sections(raw_text: str) -> Dict[str, str]:
    sections = {}
    section_pattern = re.compile(r"^([A-Z][A-Za-z0-9 /\-:()]+)\s*\n[=\-~^]+\s*$", re.MULTILINE)
    matches = list(section_pattern.finditer(raw_text))

    for i, match in enumerate(matches):
        title = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        body = raw_text[start:end].strip()
        body = re.sub(r"\n[=\-~^]+\s*$", "", body, flags=re.MULTILINE).strip()
        sections[title] = body

    return sections


def extract_pep_references(text: str, own_number: int) -> List[int]:
    patterns = [
        r":pep:`(\d+)`",
        r"PEP\s+(\d+)",
        r"pep-(\d+)",
    ]
    refs = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            num = int(match.group(1))
            if num != own_number and num in TARGET_PEPS:
                refs.add(num)
    return sorted(refs)


def parse_header_list(value: str) -> List[int]:
    if not value:
        return []
    nums = []
    for match in re.finditer(r"\d+", value):
        nums.append(int(match.group()))
    return nums


def normalize_author_name(name: str) -> str:
    name = re.sub(r"<[^>]+>", "", name).strip()
    name = re.sub(r"\([^)]*\)", "", name).strip()
    name = name.strip(",").strip()
    return name


def extract_authors(author_string: str) -> List[str]:
    if not author_string:
        return []
    raw_authors = re.split(r",(?![^<]*>)", author_string)
    authors = []
    for raw in raw_authors:
        cleaned = normalize_author_name(raw)
        if cleaned and len(cleaned) > 1:
            authors.append(cleaned)
    return authors


def match_concepts_from_text(text: str, pep_number: int) -> List[str]:
    if pep_number in PEP_CONCEPT_OVERRIDES:
        return PEP_CONCEPT_OVERRIDES[pep_number]

    text_lower = text.lower()
    matched = []
    for concept_name, concept_data in TYPING_CONCEPTS.items():
        score = 0
        for keyword in concept_data["keywords"]:
            occurrences = text_lower.count(keyword.lower())
            if occurrences > 0:
                score += occurrences
        if score >= 3:
            matched.append(concept_name)

    return matched


def get_section_text(sections: Dict[str, str], possible_names: List[str]) -> str:
    for name in possible_names:
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        for key, value in sections.items():
            if normalized in key or key in normalized:
                return value[:2000]
    return ""


def parse_single_pep(pep_number: int, raw_text: str) -> Optional[PEPEntity]:
    if not raw_text or len(raw_text) < 50:
        return None

    headers = parse_pep_header(raw_text)
    sections = extract_sections(raw_text)

    title = headers.get("title", f"PEP {pep_number}")
    status = headers.get("status", "Unknown")
    pep_type = headers.get("type", "Standards Track")
    created = headers.get("created", "")
    python_version = headers.get("python_version", headers.get("python", ""))
    requires_raw = headers.get("requires", "")
    replaces_raw = headers.get("replaces", "")
    superseded_raw = headers.get("superseded_by", "")
    author_string = headers.get("author", "")

    authors = extract_authors(author_string)
    requires_peps = parse_header_list(requires_raw)
    replaces_peps = parse_header_list(replaces_raw)

    superseded_by = None
    if superseded_raw:
        nums = parse_header_list(superseded_raw)
        superseded_by = nums[0] if nums else None

    abstract = get_section_text(sections, ["abstract", "Abstract"])
    motivation = get_section_text(sections, ["motivation", "Motivation", "rationale_and_goals"])
    rationale = get_section_text(sections, ["rationale", "Rationale", "design_rationale"])
    rejected_ideas = get_section_text(sections, [
        "rejected_ideas", "rejected_alternatives", "rejected",
        "alternatives", "deferred_ideas", "rejected_proposals"
    ])

    raw_references = extract_pep_references(raw_text, pep_number)
    matched_concepts = match_concepts_from_text(raw_text, pep_number)

    return PEPEntity(
        number=pep_number,
        title=title,
        status=status,
        pep_type=pep_type,
        authors=authors,
        created=created,
        python_version=python_version,
        requires_peps=requires_peps,
        replaces_peps=replaces_peps,
        superseded_by=superseded_by,
        abstract=abstract,
        motivation=motivation,
        rationale=rationale,
        rejected_ideas=rejected_ideas,
        raw_references=raw_references,
        matched_concepts=matched_concepts,
        sections=sections
    )


def build_concept_entities() -> List[ConceptEntity]:
    entities = []
    for name, data in TYPING_CONCEPTS.items():
        entities.append(ConceptEntity(
            name=name,
            display_name=data["display_name"],
            description=data["description"],
            keywords=data["keywords"],
            category=data["category"],
            depends_on=data["depends_on"]
        ))
    return entities


def build_author_registry(peps: List[PEPEntity]) -> Dict[str, AuthorEntity]:
    registry = {}
    for pep in peps:
        for author_name in pep.authors:
            normalized = author_name.lower().replace(" ", "_").replace(".", "")
            normalized = re.sub(r"[^a-z0-9_]", "", normalized)
            if normalized not in registry:
                registry[normalized] = AuthorEntity(
                    name=author_name,
                    normalized_name=normalized,
                    peps_authored=[]
                )
            if pep.number not in registry[normalized].peps_authored:
                registry[normalized].peps_authored.append(pep.number)
    return registry


def extract_relationships(pep: PEPEntity, all_pep_numbers: set) -> List[Relationship]:
    relationships = []

    for concept_name in pep.matched_concepts:
        relationships.append(Relationship(
            source_type=EntityType.PEP.value,
            source_id=pep.entity_id(),
            relation=RelationType.INTRODUCES.value,
            target_type=EntityType.CONCEPT.value,
            target_id=f"concept-{concept_name}",
            weight=1.0,
            metadata={"derivation": "concept_match"}
        ))

    for author_name in pep.authors:
        normalized = author_name.lower().replace(" ", "_").replace(".", "")
        normalized = re.sub(r"[^a-z0-9_]", "", normalized)
        relationships.append(Relationship(
            source_type=EntityType.PEP.value,
            source_id=pep.entity_id(),
            relation=RelationType.AUTHORED_BY.value,
            target_type=EntityType.AUTHOR.value,
            target_id=f"author-{normalized}",
            weight=1.0
        ))

    for req_pep in pep.requires_peps:
        if req_pep in all_pep_numbers:
            relationships.append(Relationship(
                source_type=EntityType.PEP.value,
                source_id=pep.entity_id(),
                relation=RelationType.REQUIRES.value,
                target_type=EntityType.PEP.value,
                target_id=f"pep-{req_pep}",
                weight=1.0,
                metadata={"source": "header"}
            ))

    for rep_pep in pep.replaces_peps:
        if rep_pep in all_pep_numbers:
            relationships.append(Relationship(
                source_type=EntityType.PEP.value,
                source_id=pep.entity_id(),
                relation=RelationType.REPLACES.value,
                target_type=EntityType.PEP.value,
                target_id=f"pep-{rep_pep}",
                weight=1.0,
                metadata={"source": "header"}
            ))

    if pep.superseded_by and pep.superseded_by in all_pep_numbers:
        relationships.append(Relationship(
            source_type=EntityType.PEP.value,
            source_id=f"pep-{pep.superseded_by}",
            relation=RelationType.SUPERSEDES.value,
            target_type=EntityType.PEP.value,
            target_id=pep.entity_id(),
            weight=1.0,
            metadata={"source": "header"}
        ))

    for ref_pep in pep.raw_references:
        if ref_pep in all_pep_numbers and ref_pep != pep.number:
            is_structural = ref_pep in pep.requires_peps or ref_pep in pep.replaces_peps
            if not is_structural:
                relationships.append(Relationship(
                    source_type=EntityType.PEP.value,
                    source_id=pep.entity_id(),
                    relation=RelationType.REFERENCES.value,
                    target_type=EntityType.PEP.value,
                    target_id=f"pep-{ref_pep}",
                    weight=0.5,
                    metadata={"source": "body_text"}
                ))

    return relationships


def build_concept_relationships() -> List[Relationship]:
    relationships = []
    for name, data in TYPING_CONCEPTS.items():
        for dep in data["depends_on"]:
            relationships.append(Relationship(
                source_type=EntityType.CONCEPT.value,
                source_id=f"concept-{name}",
                relation=RelationType.DEPENDS_ON.value,
                target_type=EntityType.CONCEPT.value,
                target_id=f"concept-{dep}",
                weight=1.0,
                metadata={"source": "taxonomy"}
            ))
    return relationships


def fetch_and_parse_all_peps(pep_numbers: List[int] = None) -> Tuple[List[PEPEntity], List[ConceptEntity], Dict[str, AuthorEntity], List[Relationship]]:
    if pep_numbers is None:
        pep_numbers = TARGET_PEPS

    peps = []
    failed = []

    for num in pep_numbers:
        print(f"  Fetching PEP {num}...")
        raw = fetch_pep_raw(num)
        if raw:
            parsed = parse_single_pep(num, raw)
            if parsed:
                peps.append(parsed)
                print(f"    Parsed: {parsed.title} [{parsed.status}]")
            else:
                failed.append(num)
                print(f"    Failed to parse PEP {num}")
        else:
            failed.append(num)
            print(f"    Failed to fetch PEP {num}")
        time.sleep(0.2)

    if failed:
        print(f"\n  Warning: Could not process PEPs: {failed}")

    concepts = build_concept_entities()
    authors = build_author_registry(peps)

    all_pep_numbers = {p.number for p in peps}
    relationships = []

    for pep in peps:
        relationships.extend(extract_relationships(pep, all_pep_numbers))

    relationships.extend(build_concept_relationships())

    concept_pep_map = {}
    for pep in peps:
        for concept in pep.matched_concepts:
            if concept not in concept_pep_map:
                concept_pep_map[concept] = []
            concept_pep_map[concept].append(pep.number)

    for concept_name, pep_nums in concept_pep_map.items():
        if pep_nums:
            concept_entity = next((c for c in concepts if c.name == concept_name), None)
            if concept_entity:
                concept_entity.introduced_in = min(pep_nums)

    for concept_name, pep_nums in concept_pep_map.items():
        sorted_nums = sorted(pep_nums)
        for i in range(1, len(sorted_nums)):
            relationships.append(Relationship(
                source_type=EntityType.PEP.value,
                source_id=f"pep-{sorted_nums[i]}",
                relation=RelationType.EXTENDS.value,
                target_type=EntityType.PEP.value,
                target_id=f"pep-{sorted_nums[i-1]}",
                weight=0.8,
                metadata={"shared_concept": concept_name, "source": "inferred"}
            ))

    print(f"\n  Built {len(peps)} PEP entities, {len(concepts)} concept entities, "
          f"{len(authors)} author entities, {len(relationships)} relationships")

    return peps, concepts, authors, relationships
