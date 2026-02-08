{{ config(materialized='table') }}

select
  *
from {{ source('raw','customers') }}
where email is not null