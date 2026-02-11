"""Phase 4 minimal non-Haworth sentinel tests for shared attach contract."""

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
from oasa import render_geometry


#============================================
def _point_in_target_closed(
		point: tuple[float, float],
		target: render_geometry.AttachTarget,
		tol: float = 1e-6) -> bool:
	if target.kind == "box":
		x1, y1, x2, y2 = target.box
		return (x1 - tol) <= point[0] <= (x2 + tol) and (y1 - tol) <= point[1] <= (y2 + tol)
	if target.kind == "circle":
		cx, cy = target.center
		distance = ((point[0] - cx) ** 2 + (point[1] - cy) ** 2) ** 0.5
		return distance <= (float(target.radius) + tol)
	if target.kind == "composite":
		for child in target.targets or ():
			if _point_in_target_closed(point, child, tol=tol):
				return True
		return False
	if target.kind == "segment":
		return False
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def _assert_attach_contract(
		text: str,
		attach_atom: str,
		attach_element: str,
		attach_site: str = "core_center") -> None:
	text_x = 8.0
	text_y = 6.0
	font_size = 16.0
	target = render_geometry.label_attach_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor="start",
		font_size=font_size,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		font_name="Arial",
	)
	full = render_geometry.label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor="start",
		font_size=font_size,
		font_name="Arial",
	)
	target_cx, _target_cy = target.centroid()
	bond_start = (target_cx, text_y - 48.0)
	endpoint = render_geometry.resolve_attach_endpoint(
		bond_start=bond_start,
		target=target,
		interior_hint=target.centroid(),
		constraints=render_geometry.AttachConstraints(direction_policy="line"),
	)
	endpoint = render_geometry.retreat_endpoint_until_legal(
		line_start=bond_start,
		line_end=endpoint,
		line_width=1.0,
		forbidden_regions=[full],
		allowed_regions=[target],
		epsilon=0.5,
	)
	assert _point_in_target_closed(endpoint, target), (
		f"Endpoint must be inside attach target for text={text!r}"
	)
	assert render_geometry.validate_attachment_paint(
		line_start=bond_start,
		line_end=endpoint,
		line_width=1.0,
		forbidden_regions=[full],
		allowed_regions=[target],
		epsilon=0.5,
	), f"Attachment paint should be legal for text={text!r}"


#============================================
def test_phase4_sentinel_ch2oh_attach_to_carbon():
	_assert_attach_contract(
		text="CH2OH",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)


#============================================
def test_phase4_sentinel_ch3_attach_to_carbon():
	_assert_attach_contract(
		text="CH3",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)


#============================================
def test_phase4_sentinel_oh_or_ho_attach_to_oxygen():
	cases = (("OH", "first"), ("HO", "last"))
	for text, attach_atom in cases:
		_assert_attach_contract(
			text=text,
			attach_atom=attach_atom,
			attach_element="O",
			attach_site="core_center",
		)
