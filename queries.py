"""
sql/queries.py
All SQL strings used by the analytics system, organised by category.
Keeping SQL separate from Python logic maximises readability and testability.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. WINDOW FUNCTIONS – salary ranking
# ═══════════════════════════════════════════════════════════════════════════════

SALARY_RANKING = """
SELECT
    e.employee_id,
    e.name,
    e.department,
    e.salary,
    RANK()         OVER dept_salary AS rank_salary,
    DENSE_RANK()   OVER dept_salary AS dense_rank_salary,
    ROW_NUMBER()   OVER dept_salary AS row_num_salary,
    ROUND(AVG(e.salary) OVER (PARTITION BY e.department), 2) AS dept_avg_salary,
    SUM(e.salary)  OVER (
        PARTITION BY e.department
        ORDER BY e.salary DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total_salary
FROM employees e
WINDOW dept_salary AS (PARTITION BY e.department ORDER BY e.salary DESC);
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 2. LAG / LEAD – performance trend
# ═══════════════════════════════════════════════════════════════════════════════

PERFORMANCE_TREND = """
SELECT
    p.employee_id,
    e.name,
    e.department,
    p.review_date,
    p.rating,
    LAG(p.rating)  OVER emp_time AS prev_rating,
    LEAD(p.rating) OVER emp_time AS next_rating,
    p.rating - LAG(p.rating) OVER emp_time AS rating_delta
FROM performance p
JOIN employees e ON e.employee_id = p.employee_id
WINDOW emp_time AS (PARTITION BY p.employee_id ORDER BY p.review_date);
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 3. CTE – top performers per department
# ═══════════════════════════════════════════════════════════════════════════════

TOP_PERFORMERS_PER_DEPT = """
WITH latest_reviews AS (
    -- Most recent review per employee
    SELECT
        employee_id,
        MAX(review_date) AS latest_date
    FROM performance
    GROUP BY employee_id
),
latest_ratings AS (
    -- Pair each employee with their most recent rating
    SELECT p.employee_id, p.rating
    FROM performance p
    JOIN latest_reviews lr
      ON p.employee_id = lr.employee_id
     AND p.review_date = lr.latest_date
),
ranked AS (
    -- Rank within department by latest rating then salary
    SELECT
        e.employee_id,
        e.name,
        e.department,
        e.salary,
        lr.rating AS latest_rating,
        RANK() OVER (
            PARTITION BY e.department
            ORDER BY lr.rating DESC, e.salary DESC
        ) AS dept_rank
    FROM employees e
    JOIN latest_ratings lr ON lr.employee_id = e.employee_id
)
SELECT *
FROM ranked
WHERE dept_rank = 1
ORDER BY department;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 4. RECURSIVE CTE – employee hierarchy
# ═══════════════════════════════════════════════════════════════════════════════

EMPLOYEE_HIERARCHY = """
WITH RECURSIVE org_tree AS (
    -- Anchor: top-level employees (no manager)
    SELECT
        employee_id,
        name,
        department,
        manager_id,
        0              AS level,
        CAST(name AS TEXT) AS path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive: join subordinates
    SELECT
        e.employee_id,
        e.name,
        e.department,
        e.manager_id,
        ot.level + 1,
        ot.path || ' → ' || e.name
    FROM employees e
    JOIN org_tree ot ON e.manager_id = ot.employee_id
)
SELECT
    employee_id,
    name,
    department,
    level,
    CASE level
        WHEN 0 THEN '👑 ' || name
        WHEN 1 THEN '  ├─ ' || name
        ELSE        '      └─ ' || name
    END AS hierarchy_display,
    path
FROM org_tree
ORDER BY path;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 5. Aggregate vs window-based avg salary comparison
# ═══════════════════════════════════════════════════════════════════════════════

AVG_SALARY_COMPARISON = """
WITH agg_avg AS (
    SELECT department, ROUND(AVG(salary), 2) AS agg_dept_avg
    FROM employees
    GROUP BY department
)
SELECT
    e.employee_id,
    e.name,
    e.department,
    e.salary,
    aa.agg_dept_avg,
    ROUND(AVG(e.salary) OVER (PARTITION BY e.department), 2) AS window_dept_avg,
    ROUND(e.salary - aa.agg_dept_avg, 2)                      AS diff_from_avg
FROM employees e
JOIN agg_avg aa ON aa.department = e.department
ORDER BY e.department, e.salary DESC;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 6. Attendance summary per employee
# ═══════════════════════════════════════════════════════════════════════════════

ATTENDANCE_SUMMARY = """
SELECT
    e.employee_id,
    e.name,
    e.department,
    COUNT(CASE WHEN a.status = 'Present' THEN 1 END) AS present_days,
    COUNT(CASE WHEN a.status = 'Absent'  THEN 1 END) AS absent_days,
    COUNT(CASE WHEN a.status = 'Leave'   THEN 1 END) AS leave_days,
    COUNT(*) AS total_records,
    ROUND(
        100.0 * COUNT(CASE WHEN a.status = 'Present' THEN 1 END) / COUNT(*), 1
    ) AS attendance_pct
FROM employees e
JOIN attendance a ON a.employee_id = e.employee_id
GROUP BY e.employee_id, e.name, e.department
ORDER BY attendance_pct DESC;
"""