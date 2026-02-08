{% macro usd_to_cents(column) %}
({{ column }} * 100)
{% endmacro %}
