select
  order_id,
  customer_id,
  try_to_date(order_date) as order_date,
  status,
  updated_at
from {{ source('raw','orders') }}