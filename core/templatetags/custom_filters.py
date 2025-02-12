from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='addclass')
def addclass(field, css_class):
    # Ensure the field has attrs if it doesn't already
    if 'attrs' not in field.field.widget.attrs:
        field.field.widget.attrs['class'] = css_class
    else:
        field.field.widget.attrs['class'] += ' ' + css_class
    return field

@register.filter(name='set_type')
def set_type(field, input_type):
    field.field.widget.input_type = input_type
    return field

@register.filter(name='addclass_and_type')
def addclass_and_type(field, args):
    arg_list = [arg.strip() for arg in args.split(',')]
    css_class = arg_list[0]
    input_type = arg_list[1]

    # Update the widget attributes directly
    if 'attrs' not in field.field.widget.attrs:
        field.field.widget.attrs['class'] = css_class
    else:
        field.field.widget.attrs['class'] += ' ' + css_class

    field.field.widget.input_type = input_type
    return field

@register.filter
def mul(value, arg):
    """Multiplies two numbers."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0  # Return 0 if multiplication fails