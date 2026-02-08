select
  o.order_id,
  o.customer_id,
  o.order_date,
  o.status,
  sum(oi.quantity * oi.price) as order_amount,
  sum({{ usd_to_cents('oi.quantity * oi.price') }}) as order_amount_cents
from {{ ref('stg_orders') }} o
join {{ ref('stg_order_items') }} oi
  on o.order_id = oi.order_id
group by 1,2,3,4
