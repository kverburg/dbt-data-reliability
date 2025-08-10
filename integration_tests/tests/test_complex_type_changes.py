import pytest
from dbt_project import DbtProject


@pytest.mark.skip_targets(["databricks", "spark", "athena", "trino", "clickhouse"])
def test_get_struct_field_changes_macro(test_id: str, dbt_project: DbtProject):
    """Test the get_struct_field_changes macro directly with various inputs."""

    # Test case 1: Field type change
    query1 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<int age, string name, int id>'", 
        "'struct<float age, string name, int id>'"
    ) }} as result
    """

    result1 = dbt_project.run_query(query1)
    assert len(result1) == 1
    description1 = result1[0]["result"]
    assert "field" in description1.lower()
    assert "age" in description1.lower()
    assert "int" in description1.lower()
    assert "float" in description1.lower()

    # Test case 2: Field added
    query2 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<int age, string name>'", 
        "'struct<int age, string name, string city>'"
    ) }} as result
    """

    result2 = dbt_project.run_query(query2)
    assert len(result2) == 1
    description2 = result2[0]["result"]
    assert "added" in description2.lower()
    assert "city" in description2.lower()

    # Test case 3: Field removed
    query3 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<int age, string name, string city>'",
        "'struct<int age, string name>'"
    ) }} as result
    """

    result3 = dbt_project.run_query(query3)
    assert len(result3) == 1
    description3 = result3[0]["result"]
    assert "removed" in description3.lower()
    assert "city" in description3.lower()

    # Test case 4: Multiple changes
    query4 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<int age, string name>'", 
        "'struct<float age, string name, string city>'"
    ) }} as result
    """

    result4 = dbt_project.run_query(query4)
    assert len(result4) == 1
    description4 = result4[0]["result"]
    assert "age" in description4.lower()
    assert "city" in description4.lower()

    # Test case 5: Non-struct types
    query5 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'varchar(100)'", 
        "'text'"
    ) }} as result
    """

    result5 = dbt_project.run_query(query5)
    assert len(result5) == 1
    description5 = result5[0]["result"]
    assert "struct type changed" in description5.lower()


@pytest.mark.skip_targets(["databricks", "spark", "athena", "trino", "clickhouse"])
def test_complex_type_changes_integration(test_id: str, dbt_project: DbtProject):
    """Test the complete integration of complex type changes in schema changes."""

    # Create a test query that simulates the schema changes logic
    test_query = """
    WITH test_data AS (
        SELECT 
            'test_table' as full_table_name,
            'profile' as column_name,
            'type_changed' as change,
            'struct<int age, string name>' as pre_data_type,
            'struct<float age, string name, string city>' as data_type,
            current_timestamp as detected_at
    ),
    test_results AS (
        SELECT
            'test_id' as data_issue_id,
            current_timestamp as detected_at,
            'test_db' as database_name,
            'test_schema' as schema_name,
            'test_table' as table_name,
            column_name,
            'schema_change' as test_type,
            change as test_sub_type,
            case
                when change = 'column_added'
                    then 'The column "' || column_name || '" was added'
                when change= 'column_removed'
                    then 'The column "' || column_name || '" was removed'
                when change= 'type_changed'
                    then case
                        when length(pre_data_type) > 30 or length(data_type) > 30
                            then case
                                when pre_data_type like 'struct<%' and data_type like 'struct<%'
                                    then 'The type of "' || column_name || '" was changed: ' || 
                                         {{ elementary.get_struct_field_changes('pre_data_type', 'data_type') }}
                                else 'The type of "' || column_name || '" was changed (complex type change)'
                            end
                        else 'The type of "' || column_name || '" was changed from ' || pre_data_type || ' to ' || data_type
                    end
                else NULL
            end as test_results_description
        from test_data
    )
    SELECT * FROM test_results
    """

    result = dbt_project.run_query(test_query)
    assert len(result) == 1

    test_result = result[0]
    assert test_result["test_sub_type"] == "type_changed"
    assert test_result["column_name"] == "profile"

    description = test_result["test_results_description"]
    assert "profile" in description
    assert "changed" in description.lower()
    assert "field" in description.lower()
    assert "age" in description.lower()
    assert "city" in description.lower()


@pytest.mark.skip_targets(["databricks", "spark", "athena", "trino", "clickhouse"])
def test_edge_cases(test_id: str, dbt_project: DbtProject):
    """Test edge cases for the complex type changes functionality."""

    # Test case 1: Empty struct
    query1 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<>'", 
        "'struct<int age>'"
    ) }} as result
    """

    result1 = dbt_project.run_query(query1)
    assert len(result1) == 1
    description1 = result1[0]["result"]
    assert "added" in description1.lower()

    # Test case 2: Very long field names
    query2 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<int very_long_field_name_that_exceeds_normal_length>'", 
        "'struct<float very_long_field_name_that_exceeds_normal_length>'"
    ) }} as result
    """

    result2 = dbt_project.run_query(query2)
    assert len(result2) == 1
    description2 = result2[0]["result"]
    assert "very_long_field_name" in description2.lower()

    # Test case 3: Complex nested types (should fall back to generic message)
    query3 = """
    SELECT {{ elementary.get_struct_field_changes(
        "'struct<array<int> scores, struct<string name, int age> person>'", 
        "'struct<array<float> scores, struct<string name, float age> person>'"
    ) }} as result
    """

    result3 = dbt_project.run_query(query3)
    assert len(result3) == 1
    description3 = result3[0]["result"]
    # Should still parse the top-level fields
    assert "scores" in description3.lower() or "person" in description3.lower()
