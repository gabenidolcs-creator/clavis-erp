"""
Unit tests for the core conditional-color view decoration types (Story 3.15).
These tests run OSS-only: BASEROW_OSS_ONLY=true is enforced by ensuring we
don't import anything from baserow_premium.
"""

import pytest

from baserow.contrib.database.views.decorator_types import (
    BackgroundColorDecoratorType,
    LeftBorderColorDecoratorType,
)
from baserow.contrib.database.views.decorator_value_provider_types import (
    ColorRuleSerializer,
    ConditionalColorConfSerializer,
    ConditionalColorValueProviderType,
)
from baserow.contrib.database.views.models import ViewDecoration
from baserow.contrib.database.views.registries import (
    decorator_type_registry,
    decorator_value_provider_type_registry,
)


# ---------------------------------------------------------------------------
# Decorator types
# ---------------------------------------------------------------------------


def test_left_border_color_decorator_type_registered():
    """LeftBorderColorDecoratorType must be reachable via the registry."""
    dt = decorator_type_registry.get("left_border_color")
    assert isinstance(dt, LeftBorderColorDecoratorType)
    assert dt.type == "left_border_color"


def test_background_color_decorator_type_registered():
    """BackgroundColorDecoratorType must be reachable via the registry."""
    dt = decorator_type_registry.get("background_color")
    assert isinstance(dt, BackgroundColorDecoratorType)
    assert dt.type == "background_color"


def test_conditional_color_value_provider_type_registered():
    """ConditionalColorValueProviderType must be reachable via the registry."""
    vp = decorator_value_provider_type_registry.get("conditional_color")
    assert isinstance(vp, ConditionalColorValueProviderType)
    assert vp.type == "conditional_color"


def test_conditional_color_compatible_with_both_decorator_types():
    """The value provider must declare compatibility with both decorator types."""
    vp = decorator_value_provider_type_registry.get("conditional_color")
    lbc = decorator_type_registry.get("left_border_color")
    bgc = decorator_type_registry.get("background_color")
    assert vp.decorator_is_compatible(lbc)
    assert vp.decorator_is_compatible(bgc)


# ---------------------------------------------------------------------------
# Serializer validation
# ---------------------------------------------------------------------------


def test_conf_serializer_valid_empty_rules():
    ser = ConditionalColorConfSerializer(data={"rules": []})
    assert ser.is_valid(), ser.errors
    assert ser.validated_data["rules"] == []


def test_conf_serializer_valid_single_rule():
    data = {
        "rules": [
            {
                "id": "rule-1",
                "color": "#FF0000",
                "filters": [{"field": 1, "type": "equal", "value": "Trễ"}],
                "filter_groups": [],
                "filter_type": "AND",
            }
        ]
    }
    ser = ConditionalColorConfSerializer(data=data)
    assert ser.is_valid(), ser.errors
    rules = ser.validated_data["rules"]
    assert len(rules) == 1
    assert rules[0]["color"] == "#FF0000"
    assert rules[0]["filter_type"] == "AND"


def test_color_rule_serializer_filter_type_default():
    data = {"id": "r", "color": "#000", "filters": [], "filter_groups": []}
    ser = ColorRuleSerializer(data=data)
    assert ser.is_valid(), ser.errors
    assert ser.validated_data["filter_type"] == "AND"


def test_color_rule_serializer_rejects_invalid_filter_type():
    data = {
        "id": "r",
        "color": "#000",
        "filters": [],
        "filter_groups": [],
        "filter_type": "INVALID",
    }
    ser = ColorRuleSerializer(data=data)
    assert not ser.is_valid()
    assert "filter_type" in ser.errors


# ---------------------------------------------------------------------------
# after_field_delete cleanup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_after_field_delete_removes_matching_filters(data_fixture):
    """Filters referencing the deleted field are purged from value_provider_conf."""
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    view = data_fixture.create_grid_view(table=table)
    field = data_fixture.create_text_field(table=table)
    other_field = data_fixture.create_text_field(table=table)

    conf = {
        "rules": [
            {
                "id": "rule-1",
                "color": "#FF0000",
                "filters": [
                    {"field": field.id, "type": "equal", "value": "Trễ", "group": None},
                    {"field": other_field.id, "type": "equal", "value": "OK", "group": None},
                ],
                "filter_groups": [],
                "filter_type": "AND",
            }
        ]
    }
    decoration = ViewDecoration.objects.create(
        view=view,
        type="left_border_color",
        value_provider_type="conditional_color",
        value_provider_conf=conf,
    )

    vp = ConditionalColorValueProviderType()
    field.delete()
    vp.after_field_delete(field)

    decoration.refresh_from_db()
    rules = decoration.value_provider_conf["rules"]
    assert len(rules) == 1
    # Only the surviving filter remains.
    assert len(rules[0]["filters"]) == 1
    assert rules[0]["filters"][0]["field"] == other_field.id


@pytest.mark.django_db
def test_after_field_delete_drops_empty_rule(data_fixture):
    """A rule whose only filter references the deleted field is removed entirely."""
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    view = data_fixture.create_grid_view(table=table)
    field = data_fixture.create_text_field(table=table)

    conf = {
        "rules": [
            {
                "id": "rule-only",
                "color": "#00FF00",
                "filters": [
                    {"field": field.id, "type": "equal", "value": "Xong", "group": None}
                ],
                "filter_groups": [],
                "filter_type": "AND",
            }
        ]
    }
    decoration = ViewDecoration.objects.create(
        view=view,
        type="background_color",
        value_provider_type="conditional_color",
        value_provider_conf=conf,
    )

    vp = ConditionalColorValueProviderType()
    field.delete()
    vp.after_field_delete(field)

    decoration.refresh_from_db()
    assert decoration.value_provider_conf["rules"] == []


@pytest.mark.django_db
def test_after_field_delete_unrelated_decoration_untouched(data_fixture):
    """Decorations that do not use conditional_color are not modified."""
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    view = data_fixture.create_grid_view(table=table)
    field = data_fixture.create_text_field(table=table)

    # A decoration with a different value_provider_type should not be touched.
    decoration = ViewDecoration.objects.create(
        view=view,
        type="left_border_color",
        value_provider_type="some_other_provider",
        value_provider_conf={"arbitrary": "data"},
    )

    vp = ConditionalColorValueProviderType()
    field.delete()
    vp.after_field_delete(field)

    decoration.refresh_from_db()
    assert decoration.value_provider_conf == {"arbitrary": "data"}


# ---------------------------------------------------------------------------
# export / import round-trip
# ---------------------------------------------------------------------------


def test_set_import_serialized_value_remaps_field_ids():
    """Field IDs embedded in filter rules are remapped during import."""
    vp = ConditionalColorValueProviderType()
    id_mapping = {"database_fields": {10: 99, 20: 88}}

    value = {
        "type": "left_border_color",
        "value_provider_type": "conditional_color",
        "value_provider_conf": {
            "rules": [
                {
                    "id": "r1",
                    "color": "#FF0000",
                    "filters": [
                        {"field": 10, "type": "equal", "value": "x"},
                        {"field": 20, "type": "contains", "value": "y"},
                    ],
                    "filter_groups": [],
                    "filter_type": "AND",
                }
            ]
        },
    }

    result = vp.set_import_serialized_value(value, id_mapping)
    filters = result["value_provider_conf"]["rules"][0]["filters"]
    assert filters[0]["field"] == 99
    assert filters[1]["field"] == 88


def test_set_import_serialized_value_ignores_missing_mapping():
    """Fields without a mapping entry are left unchanged."""
    vp = ConditionalColorValueProviderType()
    id_mapping = {"database_fields": {}}

    value = {
        "value_provider_conf": {
            "rules": [
                {
                    "id": "r1",
                    "color": "#0000FF",
                    "filters": [{"field": 55, "type": "equal", "value": "z"}],
                    "filter_groups": [],
                    "filter_type": "AND",
                }
            ]
        }
    }

    result = vp.set_import_serialized_value(value, id_mapping)
    assert result["value_provider_conf"]["rules"][0]["filters"][0]["field"] == 55


def test_set_import_serialized_value_empty_rules():
    """An empty rules list is handled without error."""
    vp = ConditionalColorValueProviderType()
    value = {"value_provider_conf": {"rules": []}}
    result = vp.set_import_serialized_value(value, {"database_fields": {}})
    assert result["value_provider_conf"]["rules"] == []
