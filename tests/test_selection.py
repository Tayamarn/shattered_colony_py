"""Tests for Selection — pure world-space logic, no pygame needed."""

import pytest
from selection import Selection
from entity import Entity


def make_entity(x: float, y: float, radius: int = 10) -> Entity:
    return Entity(x=x, y=y, hp=100, speed=50.0, radius=radius)


# ── click_select ──────────────────────────────────────────────────────────────

class TestClickSelect:
    def test_selects_entity_at_exact_centre(self):
        sel, e = Selection(), make_entity(100, 100)
        sel.click_select(100, 100, [e])
        assert e in sel.selected

    def test_selects_entity_within_radius(self):
        sel, e = Selection(), make_entity(100, 100, radius=10)
        sel.click_select(108, 100, [e])   # 8 < 10
        assert e in sel.selected

    def test_misses_entity_outside_radius(self):
        sel, e = Selection(), make_entity(100, 100, radius=10)
        sel.click_select(115, 100, [e])   # 15 > 10
        assert e not in sel.selected

    def test_miss_clears_existing_selection(self):
        sel, e = Selection(), make_entity(100, 100)
        sel.selected = {e}
        sel.click_select(500, 500, [e])
        assert len(sel.selected) == 0

    def test_selects_only_one_when_two_overlap(self):
        sel = Selection()
        e1 = make_entity(100, 100)
        e2 = make_entity(102, 100)   # both contain (100, 100) due to radius
        sel.click_select(100, 100, [e1, e2])
        assert len(sel.selected) == 1

    def test_replaces_existing_selection(self):
        sel = Selection()
        e1, e2 = make_entity(100, 100), make_entity(200, 200)
        sel.selected = {e1}
        sel.click_select(200, 200, [e1, e2])
        assert sel.selected == {e2}

    def test_empty_entity_list_deselects(self):
        sel, e = Selection(), make_entity(100, 100)
        sel.selected = {e}
        sel.click_select(100, 100, [])
        assert len(sel.selected) == 0

    def test_boundary_exactly_on_radius(self):
        # Distance exactly equals radius — should select (≤ not <)
        sel, e = Selection(), make_entity(100, 100, radius=10)
        sel.click_select(110, 100, [e])
        assert e in sel.selected


# ── box_select ────────────────────────────────────────────────────────────────

class TestBoxSelect:
    def test_selects_entity_inside_box(self):
        sel, e = Selection(), make_entity(100, 100)
        sel.box_select(50, 50, 150, 150, [e])
        assert e in sel.selected

    def test_excludes_entity_outside_box(self):
        sel, e = Selection(), make_entity(200, 200)
        sel.box_select(50, 50, 150, 150, [e])
        assert e not in sel.selected

    def test_selects_multiple_entities(self):
        sel = Selection()
        e1, e2, e3 = make_entity(80, 80), make_entity(120, 120), make_entity(300, 300)
        sel.box_select(50, 50, 200, 200, [e1, e2, e3])
        assert sel.selected == {e1, e2}

    def test_inverted_corners_still_work(self):
        # Drag from bottom-right to top-left
        sel, e = Selection(), make_entity(100, 100)
        sel.box_select(150, 150, 50, 50, [e])
        assert e in sel.selected

    def test_degenerate_box_selects_nothing(self):
        sel, e = Selection(), make_entity(100, 100)
        sel.box_select(200, 200, 200, 200, [e])
        assert e not in sel.selected

    def test_replaces_previous_selection(self):
        sel = Selection()
        e1, e2 = make_entity(100, 100), make_entity(300, 300)
        sel.selected = {e1}
        sel.box_select(250, 250, 350, 350, [e1, e2])
        assert sel.selected == {e2}

    def test_entity_on_box_boundary_is_selected(self):
        sel, e = Selection(), make_entity(150, 100)
        sel.box_select(50, 50, 150, 150, [e])
        assert e in sel.selected


# ── deselect_all ─────────────────────────────────────────────────────────────

class TestDeselectAll:
    def test_clears_selection(self):
        sel, e = Selection(), make_entity(100, 100)
        sel.selected = {e}
        sel.deselect_all()
        assert len(sel.selected) == 0

    def test_safe_when_already_empty(self):
        sel = Selection()
        sel.deselect_all()   # must not raise
        assert len(sel.selected) == 0
