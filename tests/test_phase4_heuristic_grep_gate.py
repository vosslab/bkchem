"""Regression grep gates for Phase 4 heuristic-branch bans."""

# Standard Library
import pathlib
import re

# local repo modules
from get_repo_root import get_repo_root


_REPO_ROOT = pathlib.Path(get_repo_root())
_RENDERER_PATH = _REPO_ROOT / "packages" / "oasa" / "oasa" / "haworth" / "renderer.py"
_ARCHIVE_TOOL_PATH = _REPO_ROOT / "tools" / "archive_matrix_summary.py"


#============================================
def _find_heuristic_matches(path: pathlib.Path, patterns: list[re.Pattern]) -> list[str]:
	"""Return human-readable pattern matches with line references."""
	matches = []
	for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
		for pattern in patterns:
			if not pattern.search(line):
				continue
			matches.append(
				f"{path}:{line_number}: {pattern.pattern} :: {line.strip()}"
			)
	return matches


#============================================
def test_renderer_has_no_text_or_op_id_heuristic_conditionals():
	"""Renderer must not reintroduce text/op-id conditional heuristics."""
	patterns = [
		re.compile(r"\bif\s+text\s*=="),
		re.compile(r"\bif\s+str\(text\)\s*=="),
		re.compile(r"\bif\s+.*\bop_id\b.*\b(in|startswith|endswith)\b"),
	]
	matches = _find_heuristic_matches(_RENDERER_PATH, patterns)
	assert not matches, "\n".join(matches)


#============================================
def test_archive_tool_has_no_sugar_or_text_policy_conditionals():
	"""Archive summary tool must not own sugar/text geometry policy."""
	patterns = [
		re.compile(r"\bif\s+.*\bsugar_name\b\s*(==|!=| in | not in )"),
		re.compile(r"\bif\s+text\s*=="),
		re.compile(r"\bif\s+str\(text\)\s*=="),
	]
	matches = _find_heuristic_matches(_ARCHIVE_TOOL_PATH, patterns)
	assert not matches, "\n".join(matches)
