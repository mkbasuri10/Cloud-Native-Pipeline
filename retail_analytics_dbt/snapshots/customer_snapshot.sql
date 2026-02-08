{% snapshot customer_snapshot %}
{{
  config(
    target_schema='SNAPSHOTS',
    unique_key='customer_id',
    strategy='check',
    check_cols=['email','city','state'],
    dbt_valid_to = '9999-12-31 00:00:00'
  )
}}

select *
from {{ source('raw','customers') }}

{% endsnapshot %}
