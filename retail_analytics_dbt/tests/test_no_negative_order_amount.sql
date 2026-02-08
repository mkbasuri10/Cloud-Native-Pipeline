select *
from {{ ref('fct_orders') }}
where order_amount < 0
