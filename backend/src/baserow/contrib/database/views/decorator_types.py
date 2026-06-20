from baserow.contrib.database.views.registries import DecoratorType


class LeftBorderColorDecoratorType(DecoratorType):
    """Renders a colored left border on the row or card."""

    type = "left_border_color"


class BackgroundColorDecoratorType(DecoratorType):
    """Colors the entire background of the row or card."""

    type = "background_color"
