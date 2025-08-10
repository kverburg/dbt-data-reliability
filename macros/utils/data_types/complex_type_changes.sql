{%- macro get_struct_field_changes(pre_data_type, data_type) -%}
    {{ return(adapter.dispatch('get_struct_field_changes', 'elementary')(pre_data_type, data_type)) }}
{%- endmacro -%}

{% macro default__get_struct_field_changes(pre_data_type, data_type) %}
    {# 
    Default implementation for databases that support standard SQL string functions.
    Compares two struct data types and returns a description of the specific field changes.
    #}
    
    case
        when {{ pre_data_type }} like 'struct<%' and {{ data_type }} like 'struct<%'
        then (
            select string_agg(change_description, ', ')
            from (
                -- Extract and compare struct fields
                with pre_fields as (
                    select 
                        trim(split_part(field, ' ', 1)) as field_type,
                        trim(split_part(field, ' ', 2)) as field_name
                    from (
                        select unnest(string_to_array(
                            substring({{ pre_data_type }} from 'struct<(.+)>' for '#'),
                            ','
                        )) as field
                    )
                ),
                cur_fields as (
                    select 
                        trim(split_part(field, ' ', 1)) as field_type,
                        trim(split_part(field, ' ', 2)) as field_name
                    from (
                        select unnest(string_to_array(
                            substring({{ data_type }} from 'struct<(.+)>' for '#'),
                            ','
                        )) as field
                    )
                )
                select 
                    case
                        when pf.field_name = cf.field_name and pf.field_type != cf.field_type
                            then 'field ''' || pf.field_name || ''' type changed from ' || pf.field_type || ' to ' || cf.field_type
                        when pf.field_name is not null and cf.field_name is null
                            then 'field ''' || pf.field_name || ''' was removed'
                        when pf.field_name is null and cf.field_name is not null
                            then 'field ''' || cf.field_name || ''' was added with type ' || cf.field_type
                    end as change_description
                from pre_fields pf
                full outer join cur_fields cf on pf.field_name = cf.field_name
                where change_description is not null
            )
        )
        else 'struct type changed'
    end
{% endmacro %}

{% macro bigquery__get_struct_field_changes(pre_data_type, data_type) %}
    {# 
    BigQuery implementation using BigQuery-specific string functions.
    #}
    
    case
        when {{ pre_data_type }} like 'struct<%' and {{ data_type }} like 'struct<%'
        then (
            select string_agg(change_description, ', ')
            from (
                -- Extract and compare struct fields
                with pre_fields as (
                    select 
                        trim(split(field, ' ')[offset(0)]) as field_type,
                        trim(split(field, ' ')[offset(1)]) as field_name
                    from (
                        select field
                        from unnest(split(
                            regexp_extract({{ pre_data_type }}, r'struct<(.+)>'),
                            ','
                        )) as field
                    )
                ),
                cur_fields as (
                    select 
                        trim(split(field, ' ')[offset(0)]) as field_type,
                        trim(split(field, ' ')[offset(1)]) as field_name
                    from (
                        select field
                        from unnest(split(
                            regexp_extract({{ data_type }}, r'struct<(.+)>'),
                            ','
                        )) as field
                    )
                )
                select 
                    case
                        when pf.field_name = cf.field_name and pf.field_type != cf.field_type
                            then 'field ''' || pf.field_name || ''' type changed from ' || pf.field_type || ' to ' || cf.field_type
                        when pf.field_name is not null and cf.field_name is null
                            then 'field ''' || pf.field_name || ''' was removed'
                        when pf.field_name is null and cf.field_name is not null
                            then 'field ''' || cf.field_name || ''' was added with type ' || cf.field_type
                    end as change_description
                from pre_fields pf
                full outer join cur_fields cf on pf.field_name = cf.field_name
                where change_description is not null
            )
        )
        else 'struct type changed'
    end
{% endmacro %}
