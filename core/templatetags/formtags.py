from django import template

register = template.Library()

@register.filter(name='addclass')
def addclass(field, css_class):
    """Adds a CSS class to a form field's widget. Handles non-BoundField inputs."""
    if hasattr(field, 'field') and hasattr(field.field, 'widget') and hasattr(field.field.widget, 'attrs'):
        current_classes = field.field.widget.attrs.get('class', '')
        if current_classes:
            css_class += ' ' + current_classes
        field.field.widget.attrs['class'] = css_class
        return field
    else: # Handle cases where field is not a BoundField (e.g., just a string)
        return field # Return unchanged


@register.filter(name='invalid')
def invalid(field):
    """Add 'is-invalid' class to form fields with errors."""
    if hasattr(field, 'errors') and field.errors:
        return 'is-invalid'
    return ''