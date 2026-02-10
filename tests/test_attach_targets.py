"""Unit tests for Phase A attachment target primitives and wrappers."""

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
from oasa import render_geometry


#============================================
def _is_on_circle_boundary(point, center, radius, tol=1e-6):
	distance = ((point[0] - center[0]) ** 2 + (point[1] - center[1]) ** 2) ** 0.5
	return abs(distance - radius) <= tol


#============================================
def test_attach_target_centroid_box_circle_composite():
	box = render_geometry.make_box_target((0.0, 2.0, 10.0, 12.0))
	circle = render_geometry.make_circle_target((5.0, -4.0), 3.0)
	composite = render_geometry.make_composite_target((circle, box))
	assert box.centroid() == pytest.approx((5.0, 7.0))
	assert circle.centroid() == pytest.approx((5.0, -4.0))
	assert composite.centroid() == pytest.approx(circle.centroid())


#============================================
def test_attach_target_contains_box_and_circle():
	box = render_geometry.make_box_target((0.0, 0.0, 10.0, 10.0))
	circle = render_geometry.make_circle_target((0.0, 0.0), 5.0)
	assert box.contains((5.0, 5.0))
	assert not box.contains((0.0, 5.0))
	assert circle.contains((1.0, 1.0))
	assert not circle.contains((5.0, 0.0))


#============================================
def test_attach_target_boundary_intersection_circle():
	target = render_geometry.make_circle_target((0.0, 0.0), 5.0)
	endpoint = target.boundary_intersection(bond_start=(-20.0, 0.0))
	assert _is_on_circle_boundary(endpoint, (0.0, 0.0), 5.0, tol=1e-6)
	assert endpoint[0] < 0.0


#============================================
def test_resolve_attach_endpoint_box_vertical_lock():
	target = render_geometry.make_box_target((0.0, 0.0, 10.0, 10.0))
	constraints = render_geometry.AttachConstraints(vertical_lock=True)
	endpoint = render_geometry.resolve_attach_endpoint(
		bond_start=(5.0, -10.0),
		target=target,
		interior_hint=(5.0, 5.0),
		constraints=constraints,
	)
	assert endpoint == pytest.approx((5.0, 0.0))


#============================================
def test_validate_attachment_paint_circle_legality_boundary_then_penetration():
	target = render_geometry.make_circle_target((0.0, 0.0), 5.0)
	boundary_endpoint = render_geometry.resolve_attach_endpoint(
		bond_start=(-12.0, 0.0),
		target=target,
		interior_hint=target.centroid(),
		constraints=render_geometry.AttachConstraints(direction_policy="line"),
	)
	assert _is_on_circle_boundary(boundary_endpoint, (0.0, 0.0), 5.0, tol=1e-6)
	assert render_geometry.validate_attachment_paint(
		line_start=(-12.0, 0.0),
		line_end=boundary_endpoint,
		line_width=1.0,
		forbidden_regions=[target],
		allowed_regions=[],
		epsilon=0.5,
	)
	assert not render_geometry.validate_attachment_paint(
		line_start=(-12.0, 0.0),
		line_end=(boundary_endpoint[0] + 0.8, boundary_endpoint[1]),
		line_width=1.0,
		forbidden_regions=[target],
		allowed_regions=[],
		epsilon=0.5,
	)


#============================================
def test_validate_attachment_paint_long_segment_circle_false_negative_regression():
	forbidden = render_geometry.make_circle_target((0.5, 0.0), 0.2)
	assert not render_geometry.validate_attachment_paint(
		line_start=(0.0, 0.0),
		line_end=(1000.0, 0.0),
		line_width=1.0,
		forbidden_regions=[forbidden],
		allowed_regions=[],
		epsilon=0.0,
	)


#============================================
def test_resolve_attach_endpoint_composite_uses_fallback_children():
	invalid_primary = render_geometry.AttachTarget(kind="unknown")
	fallback_box = render_geometry.make_box_target((0.0, 0.0, 10.0, 10.0))
	composite = render_geometry.make_composite_target((invalid_primary, fallback_box))
	endpoint = render_geometry.resolve_attach_endpoint(
		bond_start=(-5.0, 5.0),
		target=composite,
		interior_hint=(5.0, 5.0),
		constraints=render_geometry.AttachConstraints(direction_policy="line"),
	)
	assert endpoint == pytest.approx((0.0, 5.0))


#============================================
@pytest.mark.parametrize(
	("bond_start", "bond_end", "box"),
	(
		((-5.0, 5.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0)),
		((20.0, 5.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0)),
		((5.0, -10.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0)),
	),
)
def test_clip_bond_to_bbox_wrapper_parity_with_legacy(bond_start, bond_end, box):
	wrapper_point = render_geometry.clip_bond_to_bbox(bond_start, bond_end, box)
	legacy_point = render_geometry._clip_bond_to_bbox_legacy(bond_start, bond_end, box)
	assert wrapper_point == pytest.approx(legacy_point)


#============================================
def test_directional_attach_line_policy_matches_legacy_clip():
	box = (0.0, 0.0, 10.0, 10.0)
	start = (-10.0, 2.0)
	target = (5.0, 5.0)
	line_policy = render_geometry.directional_attach_edge_intersection(
		bond_start=start,
		attach_bbox=box,
		attach_target=target,
		direction_policy="line",
	)
	legacy = render_geometry._clip_bond_to_bbox_legacy(start, target, box)
	assert line_policy == pytest.approx(legacy)


#============================================
@pytest.mark.parametrize(
	("text", "anchor", "x", "y", "font_size", "expected"),
	(
		("O", "middle", 10.0, 20.0, 16.0, (4.0, 14.0, 16.0, 28.0)),
		("OH", "start", 10.0, 8.0, 12.0, (6.25, 3.5, 24.25, 14.0)),
		("NH3+", "end", -5.0, 4.0, 16.0, (-53.0, -2.0, -5.0, 12.0)),
	),
)
def test_label_target_legacy_geometry_values(text, anchor, x, y, font_size, expected):
	target = render_geometry.label_target(x, y, text, anchor, font_size)
	legacy = render_geometry.label_bbox(x, y, text, anchor, font_size)
	assert target.kind == "box"
	assert target.box == pytest.approx(expected)
	assert legacy == pytest.approx(expected)


#============================================
def test_label_attach_target_legacy_geometry_values():
	target = render_geometry.label_attach_target(
		0.0,
		0.0,
		"CH2OH",
		"start",
		16.0,
		attach_atom="last",
	)
	legacy = render_geometry.label_attach_bbox(
		0.0,
		0.0,
		"CH2OH",
		"start",
		16.0,
		attach_atom="last",
	)
	expected = (31.0, -6.0, 55.0, 8.0)
	assert target.kind == "box"
	assert target.box == pytest.approx(expected)
	assert legacy == pytest.approx(expected)


#============================================
def test_label_attach_selector_precedence_uses_element_before_attach_atom():
	with_element = render_geometry.label_attach_bbox(
		0.0,
		0.0,
		"COOH",
		"start",
		16.0,
		attach_atom="first",
		attach_element="O",
	)
	default_first = render_geometry.label_attach_bbox(
		0.0,
		0.0,
		"COOH",
		"start",
		16.0,
		attach_atom="first",
	)
	assert with_element[0] > default_first[0]


#============================================
def test_label_attach_invalid_attach_atom_raises_even_with_attach_element():
	with pytest.raises(ValueError, match=r"Invalid attach_atom value: 'frist'"):
		render_geometry.label_attach_bbox(
			0.0,
			0.0,
			"COOH",
			"start",
			16.0,
			attach_atom="frist",
			attach_element="O",
		)
