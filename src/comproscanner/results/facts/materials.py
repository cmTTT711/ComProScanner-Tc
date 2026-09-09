# Local material tools restored from the existing variable-normalization path.
from __future__ import annotations
from decimal import Decimal
import re
import unicodedata
from comproscanner.results.facts.processors import MaterialNormalizer
from comproscanner.results.facts.processors import NormalizationResult

_DASHES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"})
_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_ASSIGNMENT = re.compile(r"\b([a-zA-Z])\s*=\s*([0-9]+(?:\.[0-9]+)?)\b")
_ELEMENT_TERM = r"[A-Z][a-z]?(?:\s*(?:\d+(?:\.\d+)?(?:\s*-\s*[a-z])?|[a-z]))?"
_COMPONENT = (
    rf"(?:\(\s*1\s*-\s*[a-z]\s*\)|[a-z]|\d+(?:\.\d+)?)?(?:{_ELEMENT_TERM}\s*){{2,}}"
)
_FORMULA_TOKEN = re.compile(
    rf"(?<![A-Za-z0-9])(?P<formula>{_COMPONENT}(?:\s*[-–−]\s*{_COMPONENT})*)(?![A-Za-z])"
)


class LocalMaterialNormalizer:
    """Normalize harmless formula typography without changing composition."""

    def normalize(self, material: str) -> tuple[str, str]:
        reported = material.strip()
        normalized = (
            unicodedata.normalize("NFKC", reported)
            .translate(_SUBSCRIPTS)
            .translate(_DASHES)
        )
        normalized = re.sub(r"(?<!\d)0\s*:\s*(?=\d)", "0.", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        identity = re.sub(r"\s+", "", normalized)
        return normalized, identity


class VariableCompositionNormalizer:
    """Recover a variable-composition parent formula from same-document Evidence.

    Only explicit single-variable coefficients are evaluated. Unsupported
    expressions remain reviewable instead of being guessed.
    """

    def __init__(self, fallback: MaterialNormalizer | None = None):
        self.fallback = fallback or LocalMaterialNormalizer()

    @staticmethod
    def _assignments(text: str) -> dict[str, str]:
        return {name.casefold(): value for name, value in _ASSIGNMENT.findall(text)}

    @staticmethod
    def _candidate_formula(
        context: str, assignments: dict[str, str], reported_material: str
    ) -> str | None:
        variables = set(assignments)
        assignment_positions = [
            match.start()
            for name, raw in assignments.items()
            for match in re.finditer(
                rf"\b{re.escape(name)}\s*=\s*{re.escape(raw)}\b",
                context,
                flags=re.IGNORECASE,
            )
        ]
        aliases = re.findall(r"[A-Z]{2,}(?:-[A-Z]{2,})+", reported_material.upper())
        alias_positions = [
            match.start()
            for alias in aliases
            for match in re.finditer(re.escape(alias), context, flags=re.IGNORECASE)
        ]
        candidates: list[tuple[float, str]] = []
        for match in _FORMULA_TOKEN.finditer(context):
            formula = re.sub(r"\s+", "", match.group("formula").strip(" .,;:"))
            lowered = formula.casefold()
            covered = sum(
                bool(
                    re.search(
                        rf"\b{re.escape(name)}\b|(?<=\d){re.escape(name)}|{re.escape(name)}(?=\d)",
                        lowered,
                    )
                )
                for name in variables
            )
            variable_occurrences = sum(lowered.count(name) for name in variables)
            element_count = len(re.findall(r"[A-Z][a-z]?", formula))
            oxygenated = bool(re.search(r"O\d", formula))
            if covered and element_count >= 2 and oxygenated:
                distance = min(
                    (
                        abs(match.start() - position)
                        for position in assignment_positions
                    ),
                    default=100000,
                )
                alias_distance = min(
                    (abs(match.end() - position) for position in alias_positions),
                    default=100000,
                )
                # An explicitly reported acronym is a much stronger parent-
                # formula anchor than another sample's nearby x/y assignment.
                anchor_bonus = 2000 - alias_distance / 10 if aliases else 0
                candidates.append(
                    (
                        covered * 1000
                        + variable_occurrences * 100
                        + anchor_bonus
                        + element_count
                        - distance / 1000,
                        formula,
                    )
                )
        return max(candidates, default=(0, ""))[1] or None

    @staticmethod
    def _number(value: Decimal) -> str:
        rendered = format(value.normalize(), "f")
        return "0" if rendered == "-0" else rendered

    @classmethod
    def _substitute(cls, formula: str, assignments: dict[str, str]) -> str | None:
        """Evaluate common solid-solution coefficients such as 1-x and (1-y)."""

        value = unicodedata.normalize("NFKC", formula).translate(_DASHES)
        decimals = {name: Decimal(raw) for name, raw in assignments.items()}

        # Parenthesized leading coefficients, e.g. (1-y)BiFeO3.
        for name, number in decimals.items():
            value = re.sub(
                rf"\(\s*1\s*-\s*{re.escape(name)}\s*\)",
                cls._number(Decimal(1) - number),
                value,
                flags=re.IGNORECASE,
            )
        # Element-site coefficients, e.g. Fe1-x and Ti1-x.
        for name, number in decimals.items():
            value = re.sub(
                rf"1\s*-\s*{re.escape(name)}",
                cls._number(Decimal(1) - number),
                value,
                flags=re.IGNORECASE,
            )
        # Direct variable coefficients: CrxO3, MnxO3, or -yBaTiO3.
        for name, number in decimals.items():
            replacement = cls._number(number)
            value = re.sub(
                rf"\b{re.escape(name)}(?=\s*(?:wt|mol|at)\.?\s*%)", replacement, value
            )
            value = re.sub(
                rf"(?<=[a-z]){re.escape(name)}(?=[A-Z0-9])",
                replacement,
                value,
            )
            value = re.sub(
                rf"(?:(?<=^)|(?<=[+\-])){re.escape(name)}(?=[A-Z])",
                replacement,
                value,
            )
        # Refuse a partial expansion if a declared variable is still used as a
        # coefficient in the resulting formula.
        for name in decimals:
            if re.search(
                rf"(?:1\s*-\s*{re.escape(name)}|\({re.escape(name)}\)|(?<=[a-z]){re.escape(name)}(?=[A-Z0-9])|(?<=[+\-]){re.escape(name)}(?=[A-Z]))",
                value,
            ):
                return None
        return value

    def normalize_with_context(self, material: str, context: str) -> tuple[str, str]:
        reported_assignments = self._assignments(material)
        if not reported_assignments:
            return self.fallback.normalize(material)
        # Only values explicitly tied to this extracted fact may be used. A
        # paper commonly lists many other x/y samples in the same document.
        assignments = reported_assignments
        # Prefer the formula explicitly reported with this fact.
        direct = re.split(r"\s+(?:where\b|\()|\(\s*[a-z]\s*=", material, maxsplit=1)[
            0
        ].strip()
        explicit = bool(
            re.search(r"O\d", direct)
            and len(re.findall(r"[A-Z][a-z]?", direct)) >= 2
            and any(
                re.search(rf"1-{name}|(?<=[a-z]){name}(?=[A-Z0-9])", direct)
                for name in assignments
            )
        )
        formula = (
            direct
            if explicit
            else self._candidate_formula(material, assignments, material)
        )
        if not formula:
            formula = self._candidate_formula(context, assignments, material)
        if not formula:
            return self.fallback.normalize(material)
        expanded = self._substitute(formula, assignments)
        if expanded:
            return self.fallback.normalize(expanded)
        values = ", ".join(
            f"{name}={assignments[name]}" for name in sorted(assignments)
        )
        return self.fallback.normalize(f"{formula} [{values}]")

    def normalize(self, material: str) -> tuple[str, str]:
        return self.fallback.normalize(material)


class ArticleMaterialNormalizer:
    """Expand explicit same-Article definitions, then reuse variable arithmetic.

    No model call or global acronym dictionary. Unresolved identities stay in
    the output with a review issue; sample/process annotations are retained.
    """

    def __init__(self, contexts=None, abbreviations=None, sources=None):
        self.contexts = contexts or {}
        self.abbreviations = abbreviations or {}
        self.sources = sources or {}
        self.local = LocalMaterialNormalizer()
        self.variables = VariableCompositionNormalizer()
        self._definitions = {}

    @staticmethod
    def _chemical(value, require_number=True):
        from pymatgen.core.periodic_table import Element

        value = re.sub(r"(?:wt|mol|at)\.?\s*%", "", value)
        symbols = re.findall(r"[A-Z][a-z]?", value)
        rest = re.sub(r"[A-Z][a-z]?", "", value)
        return (
            len(symbols) >= (2 if require_number else 1)
            and (not require_number or any(c.isdigit() for c in value))
            and all(Element.is_valid_symbol(s) for s in symbols)
            and not re.search(r"[^0-9xyz().\[\]+*/\-\s]", rest)
            and value.count("(") == value.count(")")
            and value.count("[") == value.count("]")
            and not re.search(r"\[\d+\]", value)
        )

    def _index(self, document_id):
        if document_id in self._definitions:
            return self._definitions[document_id]
        text = self.local.normalize(self.contexts.get(document_id, ""))[0]
        text = re.split(r"(?im)^\s*(?:##?\s*)?references\s*$", text)[0]
        definitions = {}

        def add(alias, formula, quote):
            formula = re.sub(r"\s+", "", formula)
            if self._chemical(formula):
                definitions.setdefault(alias, {})[formula] = quote

        for match in re.finditer(
            r"\(\s*([A-Z][A-Z0-9]*(?:\s*-\s*[A-Za-z0-9]+)*)\s*\)", text
        ):
            alias = re.sub(r"\s+", "", match[1])
            if len(alias) < 2:
                continue
            prefix = text[max(0, match.start() - 220) : match.start()].rstrip()
            # A prose sentence boundary is not a decimal point or additive tail.
            prefix = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", prefix)[-1]
            definition_prefix = prefix
            # Accept an explicit variable range between a formula and its alias.
            # Do not strip arbitrary parenthetical prose or formula groups.
            prefix = re.sub(
                r"\s*\(\s*\d+(?:\.\d+)?\s*(?:<=|≤|<)\s*[xyz]\s*"
                r"(?:<=|≤|<)\s*\d+(?:\.\d+)?\s*\)\s*$",
                "", prefix,
            ).rstrip()
            for start in re.finditer(r"(?<![A-Za-z0-9.])(?=[A-Z0-9(])", prefix):
                before = prefix[: start.start()].rstrip()
                if before and (
                    before[-1] in ")]+-%.0123456789" or ord(before[-1]) < 32
                ):
                    continue  # Do not mistake a formula/additive tail for the whole definition.
                formula = re.sub(r"\s+", "", prefix[start.start() :])
                if self._chemical(formula):
                    add(alias, formula, definition_prefix[start.start() :] + match[0])
                    break
        # Legacy composition extraction already emits this mapping. Accept it
        # only when both pieces also occur in this Article, and retain conflicts.
        compact = re.sub(r"\s+", "", text)
        for alias, values in self.abbreviations.get(document_id, {}).items():
            for formula in ([values] if isinstance(values, str) else values):
                if alias in text and re.sub(r"\s+", "", formula) in compact:
                    add(
                        alias,
                        formula,
                        f"Article definition / extracted abbreviations: {alias} = {formula}",
                    )
        # Separator-free spellings are accepted only within this paper. Merge
        # their candidate sets so conflicting definitions remain ambiguous.
        for alias in list(definitions):
            compact_alias = alias.replace("-", "")
            if compact_alias != alias:
                definitions.setdefault(compact_alias, {}).update(definitions[alias])
        self._definitions[document_id] = (text, definitions)
        return text, definitions

    def normalize_fact(self, fact):
        text, definitions = self._index(fact.document_id)
        original = fact.material_reported
        normalized = self.local.normalize(original)[0]
        issues, traces = [], []
        if not text:
            issues.append("material_context_missing")
        for alias in sorted(definitions, key=len, reverse=True):
            pattern = (
                rf"(?:(?<![A-Za-z0-9])|(?<=[-+][xyz])){re.escape(alias)}(?![A-Za-z0-9])"
            )
            if not re.search(pattern, normalized):
                continue
            candidates = definitions[alias]
            if len(candidates) != 1:
                issues.append(f"material_definition_ambiguous: {alias}")
                continue
            formula, quote = next(iter(candidates.items()))
            if f"{formula} ({alias})" in normalized:
                continue
            # Preserve the original sample label alongside the expanded formula.
            normalized = re.sub(pattern, lambda m: formula, normalized)
            traces.append(
                {
                    "tool": "article_abbreviation",
                    "document_id": fact.document_id,
                    "alias": alias,
                    "formula": formula,
                    "source_text": quote,
                }
            )
        assignments = self.variables._assignments(self.local.normalize(original)[0])
        if assignments:
            # The old arithmetic tool is reused only for a directly reported or
            # uniquely defined parent, never a nearest-formula guess.
            formula = None
            direct = re.split(r"\s*[,;]|\s+where\b|\(\s*[xyz]\s*=", normalized)[
                0
            ].strip()
            if self._chemical(direct):
                formula = direct
            if not formula and not re.search(r"[A-Z]{2,}", normalized):
                candidates = set()
                for match in _FORMULA_TOKEN.finditer(text):
                    before = text[: match.start()].rstrip()
                    if before and before[-1] in "[(-+0123456789":
                        continue
                    candidate = re.sub(r"\s+", "", match["formula"])
                    if (
                        self._chemical(candidate)
                        and not re.search(r"1-[xyz]$", candidate)
                        and all(
                            re.search(
                                rf"1-{name}|(?<=[a-z]){name}(?=[A-Z0-9])|(?:^|-){name}(?=[A-Z])",
                                candidate,
                            )
                            for name in assignments
                        )
                    ):
                        candidates.add(candidate)
                if len(candidates) == 1:
                    formula = candidates.pop()
                elif candidates:
                    # Reuse the existing parent recovery tool, but expose this
                    # inferred binding for review instead of claiming certainty.
                    proposed = self.variables._candidate_formula(
                        text, assignments, original
                    )
                    if proposed in candidates:
                        formula = proposed
                        issues.append("material_parent_inferred_review")
                    else:
                        issues.append("material_parent_ambiguous")
            if formula:
                expanded = self.variables._substitute(formula, assignments)
                valid = all(
                    Decimal(value) <= 1 or f"1-{name}" not in formula
                    for name, value in assignments.items()
                )
                if expanded and expanded != formula and valid:
                    if formula in normalized:
                        normalized = normalized.replace(formula, expanded, 1)
                    else:
                        normalized = f"{expanded} [{normalized}]"
                    traces.append(
                        {
                            "tool": "variable_composition",
                            "document_id": fact.document_id,
                            "parent_formula": formula,
                            "assignments": assignments,
                            "source_text": formula,
                            "expanded": expanded,
                        }
                    )
                else:
                    issues.append("material_variables_unresolved")
            else:
                issues.append("material_parent_unresolved")
        # Acronym labels and sample labels must not look silently normalized.
        primary = normalized.split(" [", 1)[0]
        primary = re.sub(r"(?<=[0-9)])\s*\([A-Z][A-Z0-9-]+\)", "", primary)
        if re.search(r"\b[A-Z]{2,}(?:-[A-Z]+)*\b", primary) or (
            not re.search(r"[A-Z][a-z]?\d", primary)
            and not self._chemical(primary, False)
        ):
            issues.append("material_name_unresolved")
        if re.search(r"(?:1-[xyz]|(?<=[a-z])[xyz](?=[A-Z0-9])|\b[xyz]\s*wt)", primary):
            issues.append("material_variables_unresolved")
        if normalized != original and not traces:
            traces.append(
                {"tool": "local_material_typography", "source_text": original}
            )
        for trace in traces:
            trace["context_source"] = self.sources.get(
                fact.document_id, {"document_id": fact.document_id}
            )
        return NormalizationResult(
            normalized, normalized, tuple(dict.fromkeys(issues)), tuple(traces)
        )
