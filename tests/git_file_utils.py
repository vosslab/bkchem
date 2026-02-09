import subprocess
from typing import Optional

DEFAULT_SKIP_DIRS = {"old_shell_folder"}


#============================================
def _run_git(repo_root: str, args: list[str], error_message: str) -> str:
	"""
	Run a git command and return stdout.

	Args:
		repo_root: Repo root used as the working directory.
		args: Git command argument list.
		error_message: Fallback error message.

	Returns:
		str: Command stdout.
	"""
	result = subprocess.run(
		args,
		capture_output=True,
		text=True,
		cwd=repo_root,
	)
	if result.returncode != 0:
		message = result.stderr.strip() or error_message
		raise AssertionError(message)
	return result.stdout


#============================================
def _split_null(output: str) -> list[str]:
	"""
	Split a NUL-separated stdout string into paths.
	"""
	paths = []
	for path in output.split("\0"):
		if not path:
			continue
		paths.append(path)
	return paths


#============================================
def _path_has_skip_dir(path: str, skip_dirs: set[str]) -> bool:
	"""
	Check whether a path includes one of the skipped directories.
	"""
	normalized = path.replace("\\", "/")
	for part in normalized.split("/"):
		if part in skip_dirs:
			return True
	return False


#============================================
def _filter_skip_dirs(paths: list[str], skip_dirs: Optional[set[str]]) -> list[str]:
	"""
	Filter path list by skipped directory names.
	"""
	if skip_dirs is None:
		skip_dirs = DEFAULT_SKIP_DIRS
	if not skip_dirs:
		return paths
	filtered_paths = []
	for path in paths:
		if _path_has_skip_dir(path, skip_dirs):
			continue
		filtered_paths.append(path)
	return filtered_paths


#============================================
def list_tracked_files(
	repo_root: str,
	patterns: Optional[list[str]] = None,
	skip_dirs: Optional[set[str]] = None,
	error_message: Optional[str] = None,
) -> list[str]:
	"""
	List tracked files using git ls-files.
	"""
	if error_message is None:
		error_message = "Failed to list tracked files."
	command = ["git", "ls-files", "-z"]
	if patterns:
		command += ["--"] + patterns
	output = _run_git(repo_root, command, error_message)
	return _filter_skip_dirs(_split_null(output), skip_dirs)


#============================================
def list_changed_files(
	repo_root: str,
	diff_filter: str = "ACMRTUXB",
	skip_dirs: Optional[set[str]] = None,
	error_message: Optional[str] = None,
) -> list[str]:
	"""
	List changed files using git diff and index lists.
	"""
	if error_message is None:
		error_message = "Failed to list changed files."
	commands = [
		["git", "diff", "--name-only", f"--diff-filter={diff_filter}", "-z"],
		["git", "diff", "--name-only", "--cached", f"--diff-filter={diff_filter}", "-z"],
	]
	paths = []
	for command in commands:
		output = _run_git(repo_root, command, error_message)
		paths.extend(_split_null(output))
	return _filter_skip_dirs(paths, skip_dirs)
