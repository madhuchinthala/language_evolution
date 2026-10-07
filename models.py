from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


class EntityType(Enum):
    PEP = "pep"
    CONCEPT = "concept"
    AUTHOR = "author"


class RelationType(Enum):
    INTRODUCES = "introduces"
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    AUTHORED_BY = "authored_by"
    REFERENCES = "references"
    MOTIVATED_BY = "motivated_by"
    REPLACES = "replaces"
    REQUIRES = "requires"
    COMPANION_TO = "companion_to"


class ConceptCategory(Enum):
    CORE = "core"
    SYNTAX = "syntax"
    ADVANCED = "advanced"
    UTILITY = "utility"
    INFRASTRUCTURE = "infrastructure"
    DATA_STRUCTURES = "data_structures"


@dataclass
class PEPEntity:
    number: int
    title: str
    status: str
    pep_type: str
    authors: List[str]
    created: str
    python_version: str
    requires_peps: List[int]
    replaces_peps: List[int]
    superseded_by: Optional[int]
    abstract: str
    motivation: str
    rationale: str
    rejected_ideas: str
    raw_references: List[int]
    matched_concepts: List[str]
    sections: Dict[str, str]

    def entity_id(self) -> str:
        return f"pep-{self.number}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": EntityType.PEP.value,
            "entity_id": self.entity_id(),
            "number": self.number,
            "title": self.title,
            "status": self.status,
            "pep_type": self.pep_type,
            "authors": self.authors,
            "created": self.created,
            "python_version": self.python_version,
            "requires_peps": self.requires_peps,
            "replaces_peps": self.replaces_peps,
            "superseded_by": self.superseded_by,
            "abstract": self.abstract,
            "motivation": self.motivation,
            "rationale": self.rationale,
            "rejected_ideas": self.rejected_ideas,
            "raw_references": self.raw_references,
            "matched_concepts": self.matched_concepts,
            "sections": self.sections
        }


@dataclass
class ConceptEntity:
    name: str
    display_name: str
    description: str
    keywords: List[str]
    category: str
    depends_on: List[str]
    introduced_in: Optional[int] = None

    def entity_id(self) -> str:
        return f"concept-{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": EntityType.CONCEPT.value,
            "entity_id": self.entity_id(),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "keywords": self.keywords,
            "category": self.category,
            "depends_on": self.depends_on,
            "introduced_in": self.introduced_in
        }


@dataclass
class AuthorEntity:
    name: str
    normalized_name: str
    peps_authored: List[int] = field(default_factory=list)

    def entity_id(self) -> str:
        return f"author-{self.normalized_name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": EntityType.AUTHOR.value,
            "entity_id": self.entity_id(),
            "name": self.name,
            "normalized_name": self.normalized_name,
            "peps_authored": self.peps_authored
        }


@dataclass
class Relationship:
    source_type: str
    source_id: str
    relation: str
    target_type: str
    target_id: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "relation": self.relation,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "weight": self.weight,
            "metadata": self.metadata
        }


TYPING_CONCEPTS = {
    "function_annotations": {
        "display_name": "Function Annotations",
        "description": "Syntax for adding arbitrary metadata annotations to function parameters and return values, foundational to the type hints system",
        "keywords": ["function annotation", "parameter annotation", "return annotation", "annotations", "__annotations__"],
        "category": "core",
        "depends_on": []
    },
    "type_hints": {
        "display_name": "Type Hints",
        "description": "Core system for optional static type checking in Python using annotations",
        "keywords": ["type hint", "type hints", "type annotation", "typing module", "static typing", "type checking", "typing"],
        "category": "core",
        "depends_on": ["function_annotations"]
    },
    "variable_annotations": {
        "display_name": "Variable Annotations",
        "description": "Syntax for annotating variables with types using colon syntax outside of function signatures",
        "keywords": ["variable annotation", "variable annotations"],
        "category": "syntax",
        "depends_on": ["type_hints"]
    },
    "generics": {
        "display_name": "Generics",
        "description": "Parameterized types using TypeVar for writing type-safe generic code that operates on multiple types",
        "keywords": ["generic", "generics", "Generic", "TypeVar", "type variable", "type parameter", "parameterized"],
        "category": "core",
        "depends_on": ["type_hints"]
    },
    "protocols": {
        "display_name": "Protocols (Structural Subtyping)",
        "description": "Structural subtyping through Protocol classes enabling duck-typing compatible static type checking",
        "keywords": ["protocol", "Protocol", "structural subtyping", "structural typing", "duck typing", "runtime_checkable"],
        "category": "advanced",
        "depends_on": ["type_hints", "generics"]
    },
    "union_types": {
        "display_name": "Union Types",
        "description": "Type annotation for values that can be one of several types, including the modern X | Y syntax",
        "keywords": ["union", "Union", "Optional", "X | Y", "pipe operator", "union type", "UnionType"],
        "category": "syntax",
        "depends_on": ["type_hints"]
    },
    "literal_types": {
        "display_name": "Literal Types",
        "description": "Type annotations restricting values to specific literal values known at type-check time",
        "keywords": ["Literal", "literal type", "literal types"],
        "category": "advanced",
        "depends_on": ["type_hints"]
    },
    "typed_dict": {
        "display_name": "TypedDict",
        "description": "Dictionary type with per-key type annotations for structured heterogeneous data",
        "keywords": ["TypedDict", "typed dict", "typed dictionary"],
        "category": "data_structures",
        "depends_on": ["type_hints"]
    },
    "type_aliases": {
        "display_name": "Type Aliases",
        "description": "Mechanism for creating named aliases for complex type expressions to improve readability",
        "keywords": ["TypeAlias", "type alias", "type aliases"],
        "category": "syntax",
        "depends_on": ["type_hints"]
    },
    "type_narrowing": {
        "display_name": "Type Narrowing (TypeGuard/TypeIs)",
        "description": "User-defined type guard functions for narrowing types in conditional branches during static analysis",
        "keywords": ["TypeGuard", "TypeIs", "type guard", "type narrowing", "narrowing", "type narrow"],
        "category": "advanced",
        "depends_on": ["type_hints", "union_types"]
    },
    "variadic_generics": {
        "display_name": "Variadic Generics",
        "description": "Type variable tuples enabling parameterization of generics with a variable number of type arguments",
        "keywords": ["TypeVarTuple", "variadic", "Unpack", "variadic generic", "type variable tuple"],
        "category": "advanced",
        "depends_on": ["generics"]
    },
    "self_type": {
        "display_name": "Self Type",
        "description": "Self annotation for methods that return an instance of their enclosing class, enabling precise return types in inheritance",
        "keywords": ["Self", "self type", "typing.Self"],
        "category": "utility",
        "depends_on": ["type_hints", "generics"]
    },
    "parameter_spec": {
        "display_name": "Parameter Specification Variables",
        "description": "ParamSpec for preserving and forwarding callable parameter types through decorators and higher-order functions",
        "keywords": ["ParamSpec", "parameter specification", "Concatenate", "callable parameter"],
        "category": "advanced",
        "depends_on": ["generics", "callable_types"]
    },
    "final_qualifier": {
        "display_name": "Final Qualifier",
        "description": "Final annotation for declaring that a name or method cannot be reassigned or overridden",
        "keywords": ["Final", "@final", "final method", "final class", "no override", "constant"],
        "category": "utility",
        "depends_on": ["type_hints"]
    },
    "data_classes": {
        "display_name": "Data Classes",
        "description": "Decorator-driven generation of boilerplate special methods for structured data-holding classes",
        "keywords": ["dataclass", "dataclasses", "@dataclass", "data class"],
        "category": "data_structures",
        "depends_on": ["type_hints", "variable_annotations"]
    },
    "dataclass_transforms": {
        "display_name": "Data Class Transforms",
        "description": "Metaclass and decorator protocol for third-party libraries that produce dataclass-like behavior",
        "keywords": ["dataclass_transform", "data class transform", "orm", "attrs", "__dataclass_transform__"],
        "category": "data_structures",
        "depends_on": ["data_classes"]
    },
    "override_decorator": {
        "display_name": "Override Decorator",
        "description": "Explicit decorator for marking methods that intentionally override a parent class method to catch typos and refactoring errors",
        "keywords": ["override", "@override", "typing.override", "method override"],
        "category": "utility",
        "depends_on": ["type_hints"]
    },
    "deprecation_marking": {
        "display_name": "Deprecation via Type System",
        "description": "Using the type system to surface deprecation warnings at type-check time rather than only at runtime",
        "keywords": ["deprecated", "deprecation", "@deprecated", "warnings.deprecated"],
        "category": "utility",
        "depends_on": ["type_hints"]
    },
    "type_param_syntax": {
        "display_name": "Type Parameter Syntax",
        "description": "New compact syntax for declaring type parameters directly on class and function definitions using square brackets",
        "keywords": ["type parameter syntax", "type X", "type statement", "type alias statement"],
        "category": "syntax",
        "depends_on": ["generics", "type_aliases"]
    },
    "type_defaults": {
        "display_name": "Type Parameter Defaults",
        "description": "Default values for type parameters so generic classes can be used without always specifying every type argument",
        "keywords": ["type default", "default type parameter", "default type"],
        "category": "advanced",
        "depends_on": ["generics", "type_param_syntax"]
    },
    "postponed_annotations": {
        "display_name": "Postponed Evaluation of Annotations",
        "description": "Storing annotations as string literals for lazy evaluation, resolving forward reference issues and reducing import-time cost",
        "keywords": ["postponed", "from __future__ import annotations", "string annotation", "forward reference", "lazy evaluation", "PEP 563"],
        "category": "infrastructure",
        "depends_on": ["type_hints", "function_annotations"]
    },
    "stub_files": {
        "display_name": "Stub Files",
        "description": "External .pyi files providing type information for modules that lack inline annotations",
        "keywords": ["stub", ".pyi", "stub file", "type stub", "typeshed"],
        "category": "infrastructure",
        "depends_on": ["type_hints"]
    },
    "type_packaging": {
        "display_name": "Type Information Packaging",
        "description": "Standards for distributing and discovering type information bundled with or alongside Python packages",
        "keywords": ["py.typed", "packaging type", "distributing type", "marker file"],
        "category": "infrastructure",
        "depends_on": ["stub_files"]
    },
    "generic_builtins": {
        "display_name": "Generic Built-in Collections",
        "description": "Allowing built-in container types like list, dict, tuple to be used directly as generic types without importing from typing",
        "keywords": ["builtin generic", "standard collection", "generic alias"],
        "category": "syntax",
        "depends_on": ["generics"]
    },
    "annotated_type": {
        "display_name": "Annotated Type",
        "description": "Wrapper type for attaching arbitrary metadata to type annotations for use by third-party tools and runtime frameworks",
        "keywords": ["Annotated", "typing.Annotated", "annotation metadata", "flexible annotation"],
        "category": "advanced",
        "depends_on": ["type_hints"]
    },
    "literal_string": {
        "display_name": "Literal String Type",
        "description": "Type for strings known to be literal constants at type-check time, primarily for preventing injection vulnerabilities",
        "keywords": ["LiteralString", "literal string", "sql injection", "security typing"],
        "category": "advanced",
        "depends_on": ["literal_types"]
    },
    "readonly_typed_dict": {
        "display_name": "Read-only TypedDict Items",
        "description": "Marking individual TypedDict items as read-only to express immutability contracts in typed dictionary interfaces",
        "keywords": ["ReadOnly", "read-only", "readonly", "immutable typed"],
        "category": "data_structures",
        "depends_on": ["typed_dict"]
    },
    "gradual_typing": {
        "display_name": "Gradual Typing",
        "description": "Design philosophy of incrementally adding type annotations without requiring full program coverage, using Any as an escape hatch",
        "keywords": ["gradual typing", "optional typing", "Any", "dynamic typing", "incremental typing"],
        "category": "core",
        "depends_on": []
    },
    "callable_types": {
        "display_name": "Callable Types",
        "description": "Type annotations for callable objects expressing parameter types and return types of functions, methods, and other callables",
        "keywords": ["Callable", "callable", "callback", "higher-order function"],
        "category": "core",
        "depends_on": ["type_hints"]
    },
    "variance": {
        "display_name": "Type Parameter Variance",
        "description": "Covariance, contravariance, and invariance rules governing subtype relationships in parameterized generic types",
        "keywords": ["covariant", "contravariant", "invariant", "variance", "covariance", "contravariance"],
        "category": "advanced",
        "depends_on": ["generics"]
    },
    "required_not_required": {
        "display_name": "Required/NotRequired TypedDict Keys",
        "description": "Fine-grained per-key control over which TypedDict fields are mandatory versus optional",
        "keywords": ["Required", "NotRequired", "required key", "optional key"],
        "category": "data_structures",
        "depends_on": ["typed_dict"]
    },
    "runtime_typing": {
        "display_name": "Runtime Typing Support",
        "description": "CPython interpreter-level support for the typing module including __class_getitem__ and generic alias machinery",
        "keywords": ["__class_getitem__", "__orig_bases__", "runtime", "get_type_hints"],
        "category": "infrastructure",
        "depends_on": ["type_hints", "generics"]
    }
}


TARGET_PEPS = [
    3107, 484, 526, 544, 557, 560, 561, 563, 585,
    586, 589, 591, 593, 604, 612, 613, 646, 647, 655,
    673, 675, 681, 695, 696, 698, 702, 705, 742
]

PEP_CONCEPT_OVERRIDES = {
    3107: ["function_annotations"],
    484: ["type_hints", "generics", "callable_types", "gradual_typing", "stub_files", "union_types", "variance"],
    526: ["variable_annotations"],
    544: ["protocols"],
    557: ["data_classes"],
    560: ["runtime_typing", "generic_builtins"],
    561: ["type_packaging", "stub_files"],
    563: ["postponed_annotations"],
    585: ["generic_builtins"],
    586: ["literal_types"],
    589: ["typed_dict"],
    591: ["final_qualifier"],
    593: ["annotated_type"],
    604: ["union_types"],
    612: ["parameter_spec", "callable_types"],
    613: ["type_aliases"],
    646: ["variadic_generics"],
    647: ["type_narrowing"],
    655: ["required_not_required", "typed_dict"],
    673: ["self_type"],
    675: ["literal_string", "literal_types"],
    681: ["dataclass_transforms", "data_classes"],
    695: ["type_param_syntax", "generics", "type_aliases"],
    696: ["type_defaults", "generics"],
    698: ["override_decorator"],
    702: ["deprecation_marking"],
    705: ["readonly_typed_dict", "typed_dict"],
    742: ["type_narrowing"]
}

PEP_EVOLUTION_CHAINS = {
    "type_hints_core": [3107, 484, 526, 563, 585, 695],
    "generics_evolution": [484, 560, 585, 646, 695, 696],
    "typed_dict_evolution": [589, 655, 705],
    "type_narrowing_evolution": [647, 742],
    "literal_evolution": [586, 675],
    "callable_evolution": [484, 612],
    "data_structures": [557, 681],
    "type_alias_evolution": [484, 613, 695],
    "union_evolution": [484, 604],
    "utility_decorators": [591, 698, 702]
}
