select
  order_id,
  product_id,
  quantity,
  price
from {{ source('raw','order_items') }}