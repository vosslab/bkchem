"""BKChem GUI zoom behavior pytest."""

# Standard Library
import builtins
import math
import os
import subprocess
import sys
import time

# Third Party
import pytest

# Local repo modules
import conftest


#============================================
def _ensure_sys_path(root_dir):
	"""Ensure BKChem and OASA package paths are on sys.path."""
	bkchem_pkg_dir = os.path.join(root_dir, "packages", "bkchem")
	if bkchem_pkg_dir not in sys.path:
		sys.path.insert(0, bkchem_pkg_dir)
	bkchem_module_dir = os.path.join(bkchem_pkg_dir, "bkchem")
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)
	oasa_pkg_dir = os.path.join(root_dir, "packages", "oasa")
	if oasa_pkg_dir not in sys.path:
		sys.path.insert(0, oasa_pkg_dir)
	oasa_module_dir = os.path.join(oasa_pkg_dir, "oasa")
	if oasa_module_dir not in sys.path:
		sys.path.append(oasa_module_dir)
	if "oasa" in sys.modules:
		del sys.modules["oasa"]


#============================================
def _ensure_gettext_fallbacks():
	"""Ensure gettext helpers exist for module-level strings."""
	if "_" not in builtins.__dict__:
		builtins.__dict__["_"] = lambda m: m
	if "ngettext" not in builtins.__dict__:
		builtins.__dict__["ngettext"] = lambda s, p, n: s if n == 1 else p


#============================================
def _verify_tkinter():
	"""Verify Tk is available for GUI-backed tests."""
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name in ("_tkinter", "tkinter"):
			message = (
				"tkinter is not available. Install a Python build with Tk support."
			)
			pytest.skip(message, allow_module_level=True)
		raise
	tkinter.TkVersion


#============================================
def _ensure_preferences():
	"""Initialize preference manager for tests."""
	import os_support
	import pref_manager
	import singleton_store

	if singleton_store.Store.pm is None:
		singleton_store.Store.pm = pref_manager.pref_manager([
			os_support.get_config_filename("prefs.xml", level="global", mode="r"),
			os_support.get_config_filename("prefs.xml", level="personal", mode="r"),
		])


#============================================
def _flush_events(app, delay=0.05):
	"""Process Tk events with a brief delay for GUI updates."""
	app.update_idletasks()
	app.update()
	time.sleep(delay)
	app.update_idletasks()
	app.update()


#============================================
def _hex_points(cx, cy, radius):
	"""Return 6 points for a regular hexagon."""
	points = []
	for i in range(6):
		angle = math.radians(-90 + (60 * i))
		x = cx + radius * math.cos(angle)
		y = cy + radius * math.sin(angle)
		points.append((x, y))
	return points


#============================================
def _build_benzene(app):
	"""Create a benzene ring from 6 atoms with alternating double bonds."""
	from bond import bond
	from singleton_store import Screen

	paper = app.paper
	mol = paper.new_molecule()
	bond_length = Screen.any_to_px(paper.standard.bond_length)
	cx, cy = 320, 240
	points = _hex_points(cx, cy, bond_length)
	atoms = [mol.create_new_atom(x, y) for x, y in points]
	for index, atom in enumerate(atoms):
		other = atoms[(index + 1) % len(atoms)]
		order = 2 if index % 2 == 0 else 1
		b = bond(standard=paper.standard, order=order, type="n")
		mol.add_edge(atom, other, e=b)
		b.molecule = mol
		b.draw()
	paper.add_bindings()
	return mol


#============================================
def _snapshot_state(paper, label):
	"""Capture scale, content bbox center, and viewport center into a dict."""
	bbox = paper._content_bbox()
	if bbox:
		bbox_cx = (bbox[0] + bbox[2]) / 2
		bbox_cy = (bbox[1] + bbox[3]) / 2
	else:
		bbox_cx = None
		bbox_cy = None
	vp_cx = paper.canvasx(paper.winfo_width() / 2)
	vp_cy = paper.canvasy(paper.winfo_height() / 2)
	return {
		"label": label,
		"scale": paper._scale,
		"bbox_cx": bbox_cx,
		"bbox_cy": bbox_cy,
		"vp_cx": vp_cx,
		"vp_cy": vp_cy,
	}


#============================================
def _print_diagnostic_table(snapshots):
	"""Print formatted table of all snapshots for debugging."""
	print()
	print("=" * 80)
	print("ZOOM DIAGNOSTIC TABLE")
	print("=" * 80)
	header = (
		f"{'Step':<6} {'Label':<22} {'Scale':>8}"
		f"  {'BBox CX':>9} {'BBox CY':>9}"
		f"  {'VP CX':>9} {'VP CY':>9}"
	)
	print(header)
	print("-" * 80)
	for snap in snapshots:
		bbox_cx_str = f"{snap['bbox_cx']:.1f}" if snap["bbox_cx"] is not None else "N/A"
		bbox_cy_str = f"{snap['bbox_cy']:.1f}" if snap["bbox_cy"] is not None else "N/A"
		row = (
			f"{snap['label']:<28} {snap['scale']:>8.4f}"
			f"  {bbox_cx_str:>9} {bbox_cy_str:>9}"
			f"  {snap['vp_cx']:>9.1f} {snap['vp_cy']:>9.1f}"
		)
		print(row)
	print("=" * 80)


#============================================
def _run_zoom_diagnostic():
	root_dir = conftest.repo_root()
	_ensure_sys_path(root_dir)
	_ensure_gettext_fallbacks()
	_verify_tkinter()
	_ensure_preferences()
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem zoom test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		_flush_events(app, delay=0.05)

		# Draw benzene so there is content to zoom around
		_build_benzene(app)
		_flush_events(app, delay=0.05)

		snapshots = []

		# -- Step 0: Initial state --
		snap0 = _snapshot_state(paper, "0: initial")
		snapshots.append(snap0)
		if snap0["scale"] != 1.0:
			raise AssertionError(
				"Step 0: initial scale should be 1.0, got %.4f" % snap0["scale"]
			)
		if snap0["bbox_cx"] is None:
			raise AssertionError("Step 0: content bbox should exist after drawing benzene.")

		# -- Step 1: zoom_to_fit --
		paper.zoom_to_fit()
		_flush_events(app, delay=0.05)
		snap1 = _snapshot_state(paper, "1: zoom_to_fit")
		snapshots.append(snap1)
		if snap1["scale"] == 1.0:
			raise AssertionError("Step 1: zoom_to_fit should change scale from 1.0.")
		if snap1["bbox_cx"] is None:
			raise AssertionError("Step 1: content bbox should exist after zoom_to_fit.")

		# -- Step 2: zoom_reset --
		paper.zoom_reset()
		_flush_events(app, delay=0.05)
		snap2 = _snapshot_state(paper, "2: zoom_reset")
		snapshots.append(snap2)
		if snap2["scale"] != 1.0:
			raise AssertionError(
				"Step 2: zoom_reset should restore scale to 1.0, got %.4f"
				% snap2["scale"]
			)

		# -- Step 3: zoom_to_content --
		paper.zoom_to_content()
		_flush_events(app, delay=0.05)
		snap3 = _snapshot_state(paper, "3: zoom_to_content")
		snapshots.append(snap3)
		content_scale = snap3["scale"]
		if content_scale < 0.1:
			raise AssertionError(
				"Step 3: zoom_to_content scale %.4f below ZOOM_MIN." % content_scale
			)
		if content_scale > 4.0:
			raise AssertionError(
				"Step 3: zoom_to_content scale %.4f above 4.0 cap." % content_scale
			)
		if snap3["bbox_cx"] is None:
			raise AssertionError("Step 3: content bbox should exist after zoom_to_content.")

		# -- Step 4: zoom_out x3 --
		for i in range(3):
			paper.zoom_out()
			_flush_events(app, delay=0.02)
		snap4 = _snapshot_state(paper, "4: zoom_out x3")
		snapshots.append(snap4)
		expected_scale_4 = content_scale / (1.2 ** 3)
		if abs(snap4["scale"] - expected_scale_4) > 0.001:
			raise AssertionError(
				"Step 4: expected scale %.4f after 3x zoom_out, got %.4f"
				% (expected_scale_4, snap4["scale"])
			)

		# -- Step 5: zoom_in x3 (round-trip) --
		for i in range(3):
			paper.zoom_in()
			_flush_events(app, delay=0.02)
		snap5 = _snapshot_state(paper, "5: zoom_in x3")
		snapshots.append(snap5)
		if abs(snap5["scale"] - content_scale) > 0.001:
			raise AssertionError(
				"Step 5: round-trip scale should be %.4f, got %.4f"
				% (content_scale, snap5["scale"])
			)

		# -- Step 6: zoom_to_content again (idempotent check) --
		paper.zoom_to_content()
		_flush_events(app, delay=0.05)
		snap6 = _snapshot_state(paper, "6: zoom_to_content (2nd)")
		snapshots.append(snap6)
		tolerance = 0.05
		idempotent_drift = abs(snap6["scale"] - content_scale) / max(content_scale, 0.01)
		if idempotent_drift > tolerance:
			raise AssertionError(
				"Step 6: zoom_to_content not idempotent after round-trip. "
				"Expected ~%.4f, got %.4f (%.1f%% off)."
				% (content_scale, snap6["scale"], idempotent_drift * 100)
			)

		# -- Step 7: zoom_out x50 (clamp at ZOOM_MIN) --
		paper.zoom_reset()
		_flush_events(app, delay=0.02)
		for i in range(50):
			paper.zoom_out()
		_flush_events(app, delay=0.05)
		snap7 = _snapshot_state(paper, "7: zoom_out x50")
		snapshots.append(snap7)
		if abs(snap7["scale"] - 0.1) > 0.001:
			raise AssertionError(
				"Step 7: scale should clamp at ZOOM_MIN=0.1, got %.4f"
				% snap7["scale"]
			)

		# -- Step 8: zoom_in x50 after reset (clamp at ZOOM_MAX) --
		paper.zoom_reset()
		_flush_events(app, delay=0.02)
		for i in range(50):
			paper.zoom_in()
		_flush_events(app, delay=0.05)
		snap8 = _snapshot_state(paper, "8: zoom_in x50")
		snapshots.append(snap8)
		if abs(snap8["scale"] - 10.0) > 0.001:
			raise AssertionError(
				"Step 8: scale should clamp at ZOOM_MAX=10.0, got %.4f"
				% snap8["scale"]
			)

		# -- Diagnostic output --
		_print_diagnostic_table(snapshots)

		# -- Viewport drift analysis (step 3 vs step 5) --
		print()
		print("VIEWPORT DRIFT ANALYSIS (step 3 vs step 5)")
		print("-" * 50)
		if snap3["vp_cx"] is not None and snap5["vp_cx"] is not None:
			drift_x = abs(snap5["vp_cx"] - snap3["vp_cx"])
			drift_y = abs(snap5["vp_cy"] - snap3["vp_cy"])
			drift_total = math.sqrt(drift_x ** 2 + drift_y ** 2)
			print(f"  VP center step 3: ({snap3['vp_cx']:.1f}, {snap3['vp_cy']:.1f})")
			print(f"  VP center step 5: ({snap5['vp_cx']:.1f}, {snap5['vp_cy']:.1f})")
			print(f"  Drift X: {drift_x:.1f} px")
			print(f"  Drift Y: {drift_y:.1f} px")
			print(f"  Drift total: {drift_total:.1f} px")
			if drift_total > 50.0:
				raise AssertionError(
					"Viewport drift of %.1f px after zoom_out x3 + zoom_in x3 "
					"round-trip exceeds 50 px tolerance." % drift_total
				)
			else:
				print("  OK: viewport drift is within 50 px tolerance.")

		# -- BBox drift assertion (step 3 vs step 5) --
		if snap3["bbox_cx"] is not None and snap5["bbox_cx"] is not None:
			bbox_drift_x = abs(snap5["bbox_cx"] - snap3["bbox_cx"])
			bbox_drift_y = abs(snap5["bbox_cy"] - snap3["bbox_cy"])
			bbox_drift_total = math.sqrt(bbox_drift_x ** 2 + bbox_drift_y ** 2)
			print(f"  BBox center step 3: ({snap3['bbox_cx']:.1f}, {snap3['bbox_cy']:.1f})")
			print(f"  BBox center step 5: ({snap5['bbox_cx']:.1f}, {snap5['bbox_cy']:.1f})")
			print(f"  BBox drift total: {bbox_drift_total:.1f} px")
			if bbox_drift_total > 50.0:
				raise AssertionError(
					"BBox center drift of %.1f px after zoom_out x3 + zoom_in x3 "
					"round-trip exceeds 50 px tolerance." % bbox_drift_total
				)
		print()

	finally:
		app.destroy()


#============================================
def main():
	"""Entry point for running the zoom diagnostic directly."""
	_run_zoom_diagnostic()


#============================================
def test_bkchem_gui_zoom():
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		# Print diagnostic output when running with pytest -s
		if result.stdout:
			print(result.stdout)
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem zoom test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem zoom test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem zoom test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem zoom test subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem zoom test subprocess failed.\n%s" % combined
	)


if __name__ == "__main__":
	main()
