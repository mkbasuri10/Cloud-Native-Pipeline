{{ config(materialized='table') }}

select
  customer_id,
  upper(first_name) as first_name,
  upper(last_name) as last_name,
  lower(email) as email,
  city,
  state,
  try_to_date(signup_date) as signup_date
from {{ source('raw','customers') }}