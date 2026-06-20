from typing import Any, Dict, List

from rest_framework import serializers

from baserow.contrib.database.fields.field_filters import FILTER_TYPE_AND, FILTER_TYPE_OR
from baserow.contrib.database.views.registries import DecoratorValueProviderType


class ColorRuleFilterSerializer(serializers.Serializer):
    field = serializers.IntegerField(help_text="Field id to filter on.")
    type = serializers.CharField(help_text="View filter type string.")
    value = serializers.CharField(
        default="", allow_blank=True, help_text="Filter value."
    )
    group = serializers.IntegerField(
        allow_null=True, default=None, help_text="Filter group id, or null."
    )


class ColorRuleFilterGroupSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    filter_type = serializers.ChoiceField(
        choices=[FILTER_TYPE_AND, FILTER_TYPE_OR], default=FILTER_TYPE_AND
    )
    parent_group = serializers.IntegerField(allow_null=True, default=None)


class ColorRuleSerializer(serializers.Serializer):
    id = serializers.CharField(help_text="Unique rule identifier (UUID).")
    color = serializers.CharField(
        help_text="CSS color string applied when the rule matches (e.g. '#FF0000')."
    )
    filters = ColorRuleFilterSerializer(
        many=True, default=list, help_text="Ordered list of filters for this rule."
    )
    filter_groups = ColorRuleFilterGroupSerializer(
        many=True, default=list, help_text="Filter groups for nested AND/OR logic."
    )
    filter_type = serializers.ChoiceField(
        choices=[FILTER_TYPE_AND, FILTER_TYPE_OR],
        default=FILTER_TYPE_AND,
        help_text="Root filter combinator for this rule.",
    )


class ConditionalColorConfSerializer(serializers.Serializer):
    """Serializer for the value_provider_conf of ConditionalColorValueProviderType."""

    rules = ColorRuleSerializer(
        many=True,
        default=list,
        help_text=(
            "Ordered list of color rules. The first rule whose filters all match "
            "a row wins. A row matching no rule is left undecorated."
        ),
    )


class ConditionalColorValueProviderType(DecoratorValueProviderType):
    """
    Value provider that evaluates an ordered list of view-filter-style rules and
    returns the color of the first matching rule.  Reuses core view-filter
    evaluation primitives; does not require any premium license.
    """

    type = "conditional_color"
    compatible_decorator_types = ["left_border_color", "background_color"]
    value_provider_conf_serializer_class = ConditionalColorConfSerializer

    # ------------------------------------------------------------------
    # Import / export
    # ------------------------------------------------------------------

    def set_import_serialized_value(
        self, value: Dict[str, Any], id_mapping: Dict[str, Dict[int, Any]]
    ) -> Dict[str, Any]:
        """Remap field ids in filter rules when a view is imported into a new table."""

        database_fields_map: Dict[int, int] = id_mapping.get("database_fields", {})
        conf = value.get("value_provider_conf") or {}
        rules: List[Dict] = conf.get("rules") or []
        for rule in rules:
            for f in rule.get("filters") or []:
                old_id = f.get("field")
                if old_id is not None:
                    new_id = database_fields_map.get(old_id)
                    if new_id is not None:
                        f["field"] = new_id
        return value

    # ------------------------------------------------------------------
    # Lifecycle hooks — keep conf consistent when fields are mutated
    # ------------------------------------------------------------------

    def after_field_delete(self, deleted_field) -> None:
        """
        Remove any filter referencing the deleted field from every
        ConditionalColorValueProviderType decoration.  A rule that loses all its
        filters is also removed (zero-filter rules would match every row, which
        would be surprising behaviour).
        """

        from baserow.contrib.database.views.models import ViewDecoration

        decorations = ViewDecoration.objects.filter(
            value_provider_type=self.type
        ).select_for_update()

        for decoration in decorations:
            conf = decoration.value_provider_conf or {}
            rules = conf.get("rules") or []
            changed = False

            new_rules = []
            for rule in rules:
                original_filters = rule.get("filters") or []
                kept_filters = [
                    f for f in original_filters if f.get("field") != deleted_field.id
                ]
                if len(kept_filters) != len(original_filters):
                    changed = True
                if kept_filters:
                    rule = {**rule, "filters": kept_filters}
                    new_rules.append(rule)
                else:
                    # Rule had filters but all referenced the deleted field — drop it.
                    changed = True

            if changed:
                decoration.value_provider_conf = {**conf, "rules": new_rules}
                decoration.save(update_fields=["value_provider_conf"])

    def after_fields_type_change(self, fields) -> None:
        """
        When a field's type changes some filter types may no longer be valid.
        Remove filters that are no longer compatible with their field type.
        Rules that become empty are dropped.
        """

        from baserow.contrib.database.views.models import ViewDecoration
        from baserow.contrib.database.views.registries import view_filter_type_registry

        changed_field_ids = {f.id for f in fields}
        if not changed_field_ids:
            return

        decorations = ViewDecoration.objects.filter(
            value_provider_type=self.type
        ).select_for_update()

        for decoration in decorations:
            conf = decoration.value_provider_conf or {}
            rules = conf.get("rules") or []
            changed = False

            new_rules = []
            for rule in rules:
                original_filters = rule.get("filters") or []
                kept_filters = []
                for f in original_filters:
                    if f.get("field") not in changed_field_ids:
                        kept_filters.append(f)
                        continue
                    # Check if the filter type is still compatible with the field.
                    field = next(
                        (field for field in fields if field.id == f.get("field")),
                        None,
                    )
                    try:
                        ft = view_filter_type_registry.get(f.get("type", ""))
                        if field and ft.field_is_compatible(field):
                            kept_filters.append(f)
                        else:
                            changed = True
                    except Exception:
                        changed = True

                if len(kept_filters) != len(original_filters):
                    changed = True
                if kept_filters:
                    new_rules.append({**rule, "filters": kept_filters})
                else:
                    changed = True

            if changed:
                decoration.value_provider_conf = {**conf, "rules": new_rules}
                decoration.save(update_fields=["value_provider_conf"])
