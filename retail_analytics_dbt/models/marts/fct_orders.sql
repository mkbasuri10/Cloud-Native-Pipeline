{{ config(
   materialized='incremental',
   unique_key='order_id',
   incremental_strategy='merge'
) }}

select
  i.order_id,
  i.customer_id,
  i.order_date,
  i.status,
  i.order_amount
from {{ ref('int_order_enriched') }} i

{% if is_incremental() %}
where i.order_date >= (select coalesce(max(order_date), '1900-01-01') from {{ this }})
{% endif %}
