WITH

cost_unit_map AS (
    -- parse cost_unit mapping to categories from json to sql table
    SELECT
        top.key AS cost_unit,
        level_1.key AS source,
        level_2.value AS category
    FROM
        json_each(:cost_units) top,
        json_each(top.value) level_1,
        json_each(level_1.value) level_2
    WHERE level_1.key != 'label'  
),

mapped_events AS (
    -- map event categories to cost unit according to cost unit map
    SELECT
        e.*, array.value AS mapped_category, m.cost_unit,
        ((unixepoch(e.end) - unixepoch(e.start)) / 60) AS event_duration_minutes,
        DATE(start) as date
    FROM
        events e,
        json_each(e.categories) AS array
    JOIN cost_unit_map as m
        ON e.source = m.source AND array.value = m.category
    WHERE DATE(e.start) BETWEEN :from_date AND :to_date
),

mapped_events_aggregated AS (
    -- agg_time_by_cost_unit event times by date and cost unit
    SELECT
        DATE(start) as date,
        cost_unit,
        SUM((unixepoch(end) - unixepoch(start)) / 60) AS event_time_in_cost_unit
    FROM mapped_events
    GROUP BY date, cost_unit
),

ezeit_with_aggregated_events AS (
    -- join ezeit data with aggregated event times
    SELECT * FROM ezeit_days e
    LEFT JOIN mapped_events_aggregated m ON m.date = e.date
    WHERE e.date BETWEEN :from_date AND :to_date
), 

ezeit_non_work_days_to_zero AS(
	-- set minutes allocated in ezeit and event times to 0 when date was not a work day
    SELECT
		date,
		day_category,
		cost_unit,
		(CASE WHEN day_category = 'on_work' THEN booked_minutes ELSE 0 END) AS booked_minutes,
		(CASE WHEN day_category = 'on_work' THEN event_time_in_cost_unit ELSE 0 END) AS event_time_in_cost_unit
	FROM ezeit_with_aggregated_events
),

ezeit_pivoted AS (  
	-- pivot table structure: each cost unit becomes its own column
    SELECT 
		date, day_category, booked_minutes, 
		{sql_pivot_statements}
	FROM ezeit_non_work_days_to_zero
	GROUP BY date
),

ezeit_event_totals AS (
	-- derive a new column summing minutes spent in events across all events 
    SELECT *, {sql_sum_columns} AS 'event_minutes' 
	FROM ezeit_pivoted e
)

-- add columns indicating minutes not allocated to events as well as the default cost unit including unallocated times
SELECT
	*,
    e.booked_minutes < e.event_minutes AS 'event_minutes_exceed_booked_minutes',
	e.booked_minutes - e.event_minutes AS 'non_event_minutes',
	e.default_cost_unit + e.booked_minutes - e.event_minutes AS 'default_cost_unit_inkl_non_event_minutes'
FROM ezeit_event_totals e;