# USER METRICS

## Number of unique users in Customers
unique_users_in_customers_count = '''
SELECT
    COUNT(DISTINCT CustomerActionCustomerIdsMindboxId) AS unique_users_customers
FROM
    customers;
'''

## Number of unique users in Orders
unique_users_in_orders_count = '''
SELECT
    COUNT(DISTINCT OrderCustomerIdsMindboxId) AS unique_users_orders
FROM
    orders;
'''    

## Find non-matching user IDs and create a view to review these IDs
view_non_matched_ids = '''
CREATE VIEW v_non_matched_ids AS
-- User identifiers that are present only in the 'customers' table
SELECT
    CustomerActionCustomerIdsMindboxId AS unique_user_id
FROM
    customers
WHERE
    CustomerActionCustomerIdsMindboxId NOT IN (SELECT OrderCustomerIdsMindboxId FROM orders)

UNION ALL

-- User identifiers that are present only in the 'orders' table
SELECT
    OrderCustomerIdsMindboxId AS unique_user_id
FROM
    orders
WHERE
    OrderCustomerIdsMindboxId NOT IN (SELECT CustomerActionCustomerIdsMindboxId FROM customers);
'''

## Find the number of users whose IDs do not match in both datasets
non_matched_users_count = '''
-- Unique users from the 'customers' table who are not present in 'orders', grouped by year
WITH unique_customers AS (
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS order_year,
        COUNT(DISTINCT CustomerActionCustomerIdsMindboxId) AS unique_user_count
    FROM
        customers c
    LEFT JOIN
        orders o ON c.CustomerActionCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    WHERE
        o.OrderCustomerIdsMindboxId IS NULL -- только те, кто в customers, но не в orders
    GROUP BY
        order_year
),
-- Unique users from the 'orders' table who are not present in 'customers', grouped by year
unique_orders AS (
    SELECT
        strftime('%Y', OrderFirstActionDateTimeUtc) AS order_year,
        COUNT(DISTINCT OrderCustomerIdsMindboxId) AS unique_user_count
    FROM
        orders
    LEFT JOIN
        customers c ON c.CustomerActionCustomerIdsMindboxId = orders.OrderCustomerIdsMindboxId
    WHERE
        c.CustomerActionCustomerIdsMindboxId IS NULL -- только те, кто в orders, но не в customers
    GROUP BY
        order_year
)
-- Combine the results
SELECT
    order_year,
    SUM(unique_user_count) AS unique_user_count,
    'customers_only' AS source
FROM
    unique_customers
GROUP BY
    order_year

UNION ALL

SELECT
    order_year,
    SUM(unique_user_count) AS unique_user_count,
    'orders_only' AS source
FROM
    unique_orders
GROUP BY
    order_year
ORDER BY
    order_year, source;
'''

# New Year Promotion

## Take a look at the dates of the New Year promotion
new_years_action_date = '''
SELECT
    MIN(OrderFirstActionDateTimeUtc) AS newyear_start,
    MAX(OrderFirstActionDateTimeUtc) AS newyear_end
FROM
    orders
WHERE
    OrderCustomFieldsNewyear = True;
'''

## Count the number of unique users participating in the New Year promotion
unique_new_years_users_count = '''
SELECT
    COUNT(DISTINCT OrderCustomerIdsMindboxId) AS user_count_newyear
FROM
    orders
WHERE
    OrderCustomFieldsNewyear = True;
'''

## Calculate the percentage of participants out of the total number of user
percent_participated_newyear = '''
SELECT
    ROUND((CAST(COUNT(DISTINCT OrderCustomerIdsMindboxId) AS FLOAT) /
           (SELECT COUNT(DISTINCT OrderCustomerIdsMindboxId) FROM orders) * 100), 2) AS percent_participated_newyear
FROM
    orders
WHERE
    OrderCustomFieldsNewyear = True;
'''

## Calculate the number of unique users participating in the New Year's promotion by the year of their first activity,
## as well as the total amount of expected contributions, the amount of paid contributions, and the payment capability 
## in percentage
active_new_year_users_cnt_by_year = '''
WITH newyear_users AS (
    SELECT
        DISTINCT o.OrderCustomerIdsMindboxId
    FROM
        orders o
    WHERE
        o.OrderCustomFieldsNewyear = True
),
first_activity AS (
    SELECT
        c.CustomerActionCustomerIdsMindboxId,
        MIN(c.CustomerActionDateTimeUtc) AS first_active_date
    FROM
        customers c
    JOIN
        newyear_users nu ON c.CustomerActionCustomerIdsMindboxId = nu.OrderCustomerIdsMindboxId
    GROUP BY
        c.CustomerActionCustomerIdsMindboxId
)
SELECT
    strftime('%Y', fa.first_active_date) AS active_year,
    COUNT(DISTINCT fa.CustomerActionCustomerIdsMindboxId) AS user_count,
    SUM(o.OrderTotalPrice) AS total_planned_donations,
    SUM(
        CASE WHEN o.OrderLineStatusIdsExternalId = 'Paid' THEN o.OrderTotalPrice ELSE 0 END) AS paid_donations,
    CASE
        WHEN SUM(o.OrderTotalPrice) > 0 THEN
        ROUND((SUM(CASE WHEN o.OrderLineStatusIdsExternalId = 'Paid' THEN o.OrderTotalPrice ELSE 0 END) * 100.0 /
               SUM(o.OrderTotalPrice)), 2)
        ELSE
            0
    END AS total_donations_percentage
FROM
    first_activity fa
JOIN
    orders o ON o.OrderCustomerIdsMindboxId = fa.CustomerActionCustomerIdsMindboxId
GROUP BY
    active_year
ORDER BY
    active_year;
'''

## Count users who participated in the New Year's promotion returned after it
cnt_returned_after_ny_users = '''
WITH newyear_users AS (
    -- Select all users who participated in the New Year promotion
    SELECT
        DISTINCT OrderCustomerIdsMindboxId,
        MIN(OrderFirstActionDateTimeUtc) AS first_newyear_activity
    FROM
        orders
    WHERE
        OrderCustomFieldsNewyear = True
    GROUP BY
        OrderCustomerIdsMindboxId
),
post_newyear_users AS (
    -- Select users who performed at least one action after the New Year promotion
    SELECT
        DISTINCT o.OrderCustomerIdsMindboxId
    FROM
        orders o
    JOIN
        newyear_users nu ON o.OrderCustomerIdsMindboxId = nu.OrderCustomerIdsMindboxId
    WHERE
        o.OrderFirstActionDateTimeUtc > nu.first_newyear_activity
)
SELECT
    COUNT(*) AS post_newyear_user_count
FROM
    post_newyear_users;
'''

## Count users who showed their first activity during the New Year's promotion and made their first donation 
## specifically for it
cnt_users_donated_first_time_during_ny_action = '''
WITH newyear_activity_period AS (
    -- Define the minimum and maximum dates of the New Year promotion
    SELECT
        MIN(OrderFirstActionDateTimeUtc) AS min_newyear_activity_date,
        MAX(OrderFirstActionDateTimeUtc) AS max_newyear_activity_date
    FROM
        orders
    WHERE
        OrderCustomFieldsNewyear = True
),
users_first_activity AS (
    -- Define the first activity date of each user
    SELECT
        o.OrderCustomerIdsMindboxId,
        MIN(o.OrderFirstActionDateTimeUtc) AS first_order_date
    FROM
        orders o
    GROUP BY
        o.OrderCustomerIdsMindboxId
),
newyear_users AS (
    -- Select users whose first activity occurred during the New Year promotion period
    -- and that activity is associated with the New Year promotion
    SELECT
        u.OrderCustomerIdsMindboxId
    FROM
        users_first_activity u
    JOIN
        orders o ON u.OrderCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    WHERE
        u.first_order_date BETWEEN (SELECT min_newyear_activity_date FROM newyear_activity_period)
                              AND (SELECT max_newyear_activity_date FROM newyear_activity_period)
        AND o.OrderCustomFieldsNewyear = True  -- первая активность - новогодняя акция
)
SELECT
    COUNT(*) AS newyear_user_count
FROM
    newyear_users;
'''

## Count how many of them returned with a repeat payment
cnt_returned_users_donated_first_time_during_ny_action = '''
WITH newyear_activity_period AS (
    -- Define the minimum and maximum dates of the New Year promotion
    SELECT
        MIN(OrderFirstActionDateTimeUtc) AS min_newyear_activity_date,
        MAX(OrderFirstActionDateTimeUtc) AS max_newyear_activity_date
    FROM
        orders
    WHERE
        OrderCustomFieldsNewyear = TRUE
),
users_first_activity AS (
    -- Define the first activity date for each user
    SELECT
        o.OrderCustomerIdsMindboxId,
        MIN(o.OrderFirstActionDateTimeUtc) AS first_order_date
    FROM
        orders o
    GROUP BY
        o.OrderCustomerIdsMindboxId
),
newyear_users AS (
    -- Select users whose first activity occurred during the New Year promotion period
    -- and that activity is associated with the New Year promotion
    SELECT
        u.OrderCustomerIdsMindboxId
    FROM
        users_first_activity u
    JOIN
        orders o ON u.OrderCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    WHERE
        u.first_order_date BETWEEN (SELECT min_newyear_activity_date FROM newyear_activity_period)
                              AND (SELECT max_newyear_activity_date FROM newyear_activity_period)
        AND o.OrderCustomFieldsNewyear = TRUE  -- первая активность - новогодняя акция
),
repeat_payment_users AS (
    -- Select users who made a repeat payment after the New Year promotion
    SELECT
        DISTINCT o.OrderCustomerIdsMindboxId
    FROM
        orders o
    JOIN
        newyear_users nu ON o.OrderCustomerIdsMindboxId = nu.OrderCustomerIdsMindboxId
    WHERE
        o.OrderFirstActionDateTimeUtc > (SELECT max_newyear_activity_date FROM newyear_activity_period)
)
SELECT
    COUNT(*) AS users_with_repeat_payment
FROM
    repeat_payment_users;
'''

# Recurring Users and Repeat Payments

## Count the number of recurring users
unique_recurrents_count = '''
SELECT
    COUNT(DISTINCT(OrderCustomerIdsMindboxId)) AS recurrents_count
FROM
    orders
WHERE
    OrderCustomFieldsRecurrent = True;
'''

## Count the number of recurring users by year
unique_recurrents_users_cnt_by_year = '''
WITH recurrent_orders AS (
    -- Select users with recurrent payments and the first date of their activity
    SELECT
        DISTINCT OrderCustomerIdsMindboxId,
        MIN(OrderFirstActionDateTimeUtc) AS first_payment_date
    FROM
        orders
    WHERE
        OrderCustomFieldsRecurrent = True
    GROUP BY
        OrderCustomerIdsMindboxId
)
-- Calculate the number of recurrent users by the year of their first activity
SELECT
    strftime('%Y', first_payment_date) AS first_payment_year,
    COUNT(*) AS recurrent_users_count
FROM
    recurrent_orders
GROUP BY
    first_payment_year
ORDER BY
    first_payment_year;
'''

## Count the number of users who made more than one payment, excluding recurring users
users_count_more_than_one_order_without_recurrents = '''
WITH paid_users AS (
    -- Select all users with at least one paid order
    SELECT
        DISTINCT OrderCustomerIdsMindboxId
    FROM
        orders
    WHERE
        OrderLineStatusIdsExternalId = 'Paid' AND OrderCustomFieldsRecurrent = FALSE -- исключаем рекуррентов
),
second_payment AS (
    -- Determine if the user made a repeat payment after the first one
    SELECT
        pu.OrderCustomerIdsMindboxId,
        COUNT(DISTINCT o.OrderFirstActionIdsMindboxId) AS order_count
    FROM
        paid_users pu
    JOIN
        orders o ON pu.OrderCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    GROUP BY
        pu.OrderCustomerIdsMindboxId
)
SELECT
    COUNT(*) AS users_with_repeat_payment
FROM
    second_payment
WHERE
    order_count > 1;
'''

## Calculate the average number of days between payments for users who made more than one payment but are not 
## recurring users
avg_days_between_orders_without_recurrents = '''
WITH paid_users AS (
    -- Select all users with at least one paid order
    SELECT
        DISTINCT OrderCustomerIdsMindboxId
    FROM
        orders
    WHERE
        OrderLineStatusIdsExternalId = 'Paid'
        AND OrderCustomFieldsRecurrent = FALSE  -- исключаем рекуррентов
),
user_payments AS (
    -- Select all payments for these users
    SELECT
        o.OrderCustomerIdsMindboxId,
        o.OrderFirstActionDateTimeUtc AS payment_date
    FROM
        orders o
    JOIN
        paid_users pu ON pu.OrderCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    ORDER BY
        o.OrderCustomerIdsMindboxId, o.OrderFirstActionDateTimeUtc
),
payment_differences AS (
    -- Calculate the difference between consecutive payments
    SELECT
        up.OrderCustomerIdsMindboxId,
        up.payment_date,
        LAG(up.payment_date) OVER (PARTITION BY up.OrderCustomerIdsMindboxId ORDER BY up.payment_date) AS previous_payment_date
    FROM
        user_payments up
),
days_between_payments AS (
    -- Calculate the number of days between payments
    SELECT
        OrderCustomerIdsMindboxId,
        (julianday(payment_date) - julianday(previous_payment_date)) AS days_between
    FROM
        payment_differences
    WHERE
        previous_payment_date IS NOT NULL  -- убираем первый платеж, т.к. у него нет предыдущего
),
average_days AS (
    -- Calculate the average number of days between payments for each user
    SELECT
        OrderCustomerIdsMindboxId,
        AVG(days_between) AS avg_days_between_payments
    FROM
        days_between_payments
    GROUP BY
        OrderCustomerIdsMindboxId
)
-- Calculate the overall average for all users
SELECT
    ROUND(AVG(avg_days_between_payments), 2) AS overall_avg_days_between_payments
FROM
    average_days;
'''

## Calculate the number of users who made at least one payment based on their source of arrival to the fund
cnt_paid_users_by_source = '''
WITH first_activity AS (
    -- Define the first activity date for each user
    SELECT
        CustomerActionCustomerIdsMindboxId,
        MIN(CustomerActionDateTimeUtc) AS first_action_date
    FROM
        customers
    GROUP BY
        CustomerActionCustomerIdsMindboxId
),
users_per_year AS (
    -- Group by the source and year of the first activity
    SELECT
        c.CustomerActionChannelName AS user_source,
        strftime('%Y', fa.first_action_date) AS first_action_year,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS users_count
    FROM
        customers c
    JOIN
        first_activity fa ON c.CustomerActionCustomerIdsMindboxId = fa.CustomerActionCustomerIdsMindboxId
    JOIN
        orders o ON o.OrderCustomerIdsMindboxId = c.CustomerActionCustomerIdsMindboxId
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
        AND c.CustomerActionDateTimeUtc = fa.first_action_date  -- cчитаем только первое действие пользователя
    GROUP BY
        c.CustomerActionChannelName, strftime('%Y', fa.first_action_date)
)
-- Final table with a breakdown by year and a total column
SELECT
    user_source,
    SUM(CASE WHEN first_action_year = '2021' THEN users_count ELSE 0 END) AS "2021",
    SUM(CASE WHEN first_action_year = '2022' THEN users_count ELSE 0 END) AS "2022",
    SUM(CASE WHEN first_action_year = '2023' THEN users_count ELSE 0 END) AS "2023",
    SUM(CASE WHEN first_action_year = '2024' THEN users_count ELSE 0 END) AS "2024",
    SUM(CASE WHEN first_action_year IN ('2021', '2022', '2023', '2024') THEN users_count ELSE 0 END) AS total
FROM
    users_per_year
GROUP BY
    user_source
ORDER BY
    total DESC;
'''

## Find the average number of days between users' repeat payments
avg_days_between_repeated_orders = '''
WITH non_recurrent_users AS (
    -- Select users who do not have recurrent payments and their first payment date
    SELECT
        OrderCustomerIdsMindboxId,
        MIN(OrderFirstActionDateTimeUtc) AS first_payment_date
    FROM
        orders
    WHERE
        OrderCustomFieldsRecurrent = False AND OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        OrderCustomerIdsMindboxId
),
returning_payments AS (
    -- For each user, find subsequent payments after their first payment date
    SELECT
        nru.OrderCustomerIdsMindboxId,
        MIN(o.OrderFirstActionDateTimeUtc) AS second_payment_date
    FROM
        non_recurrent_users nru
    JOIN
        orders o ON nru.OrderCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    WHERE
        o.OrderFirstActionDateTimeUtc > nru.first_payment_date
    GROUP BY
        nru.OrderCustomerIdsMindboxId
),
days_between_payments AS (
    -- Calculate the number of days between the first and second payments
    SELECT
        nru.OrderCustomerIdsMindboxId,
        JULIANDAY(second_payment_date) - JULIANDAY(first_payment_date) AS days_diff
        -- EXTRACT(DAY FROM (rp.second_payment_date - nru.first_payment_date)) AS days_diff
    FROM
        non_recurrent_users nru
    JOIN
        returning_payments rp ON nru.OrderCustomerIdsMindboxId = rp.OrderCustomerIdsMindboxId
)
-- Calculate the average number of days between the first and second payments
SELECT
    CAST(ROUND(AVG(days_diff)) AS INTEGER) AS avg_days_between_1_and_2_payments
FROM
    days_between_payments;
'''

# Unpaid Payments and Payment Errors

## Count the number of payments by payment status
count_orders_by_status = '''
SELECT
    OrderLineStatusIdsExternalId AS payment_status,
    COUNT(*) AS count_payments
FROM
    orders
GROUP BY
    payment_status
ORDER BY
    count_payments DESC;
'''

## Count the number of payments by payment status, broken down by year
count_orders_by_status_per_year = '''
SELECT
    OrderLineStatusIdsExternalId AS payment_status,
    SUM(CASE WHEN strftime('%Y', OrderFirstActionDateTimeUtc) = '2021' THEN 1 ELSE 0 END) AS "2021",
    SUM(CASE WHEN strftime('%Y', OrderFirstActionDateTimeUtc) = '2022' THEN 1 ELSE 0 END) AS "2022",
    SUM(CASE WHEN strftime('%Y', OrderFirstActionDateTimeUtc) = '2023' THEN 1 ELSE 0 END) AS "2023",
    SUM(CASE WHEN strftime('%Y', OrderFirstActionDateTimeUtc) = '2024' THEN 1 ELSE 0 END) AS "2024"
FROM
    orders
WHERE
    strftime('%Y', OrderFirstActionDateTimeUtc) IN ('2021', '2022', '2023', '2024')
GROUP BY
    payment_status
ORDER BY
    payment_status;
'''

## Count the number of unique users by payment status
unique_users_cnt_by_payment_status = '''
SELECT
    o.OrderLineStatusIdsExternalId AS payment_status,
    COUNT(DISTINCT c.CustomerActionCustomerIdsMindboxId) AS unique_user_count
FROM
    customers c
JOIN
    orders o ON o.OrderCustomerIdsMindboxId = c.CustomerActionCustomerIdsMindboxId
GROUP BY
    payment_status
ORDER BY
    unique_user_count DESC;
'''

## Look for intersections in user groups by payment status
intersections_users_cnt_by_payment_status = '''
WITH user_status AS (
    -- Get unique users with their payment statuses
    SELECT
        c.CustomerActionCustomerIdsMindboxId AS customer_id,
        o.OrderLineStatusIdsExternalId AS order_status
    FROM
        customers c
    JOIN
        orders o ON o.OrderCustomerIdsMindboxId = c.CustomerActionCustomerIdsMindboxId
),
status_counts AS (
    -- Count the number of unique statuses for each user
    SELECT
        customer_id,
        COUNT(DISTINCT order_status) AS status_count
    FROM
        user_status
    GROUP BY
        customer_id
)
-- Count the number of users by the number of statuses
SELECT
    status_count,
    COUNT(*) AS user_count
FROM
    status_counts
GROUP BY
    status_count
ORDER BY
    status_count;
'''

## Count the number of unique users by payment status, broken down by year
unique_users_cnt_by_payment_status_per_year = '''
SELECT
    o.OrderLineStatusIdsExternalId AS payment_status,
    COUNT(DISTINCT CASE WHEN strftime('%Y', o.OrderFirstActionDateTimeUtc) = '2021' THEN c.CustomerActionCustomerIdsMindboxId END) AS "2021",
    COUNT(DISTINCT CASE WHEN strftime('%Y', o.OrderFirstActionDateTimeUtc) = '2022' THEN c.CustomerActionCustomerIdsMindboxId END) AS "2022",
    COUNT(DISTINCT CASE WHEN strftime('%Y', o.OrderFirstActionDateTimeUtc) = '2023' THEN c.CustomerActionCustomerIdsMindboxId END) AS "2023",
    COUNT(DISTINCT CASE WHEN strftime('%Y', o.OrderFirstActionDateTimeUtc) = '2024' THEN c.CustomerActionCustomerIdsMindboxId END) AS "2024"
FROM
    customers c
JOIN
    orders o ON o.OrderCustomerIdsMindboxId = c.CustomerActionCustomerIdsMindboxId
WHERE
    strftime('%Y', o.OrderFirstActionDateTimeUtc) IN ('2021', '2022', '2023', '2024')
GROUP BY
    payment_status
ORDER BY
    payment_status;
'''

## Look at the total estimated amount, the amount of paid orders, unpaid orders, and payment errors by year
revenue_by_payment_status_and_total_revenue = '''
SELECT
    strftime('%Y', OrderFirstActionDateTimeUtc) AS financial_year,
    SUM(OrderTotalPrice) AS total_amount,
    SUM(CASE WHEN OrderLineStatusIdsExternalId = 'Paid' THEN OrderTotalPrice ELSE 0 END) AS total_paid,
    SUM(CASE WHEN OrderLineStatusIdsExternalId = 'notpaid' THEN OrderTotalPrice ELSE 0 END) AS total_not_paid,
    SUM(CASE WHEN OrderLineStatusIdsExternalId = 'fail' THEN OrderTotalPrice ELSE 0 END) AS total_failed
FROM
    orders
GROUP BY
    financial_year
ORDER BY
    financial_year;
'''

## Look at the maximum donation amount, the maximum paid and unpaid amounts
max_sum_donated = '''
SELECT
    MAX(OrderTotalPrice) AS max_order_amount,
    MAX(CASE WHEN OrderLineStatusIdsExternalId = 'Paid' THEN OrderTotalPrice ELSE NULL END) AS max_paid_order_amount,
    MAX(CASE WHEN OrderLineStatusIdsExternalId = 'notpaid' THEN OrderTotalPrice ELSE NULL END) AS max_not_paid_order_amount
FROM orders;
'''

## Count how many payments were above the average of 500 rubles and below the maximum of 200,000 rubles
cnt_payment_500_200000 = '''
SELECT
    COUNT(*) AS paid_orders_count
FROM
    orders
WHERE
    OrderLineStatusIdsExternalId = 'Paid' AND (OrderTotalPrice > 500 AND OrderTotalPrice < 200000);
'''

## Count how many unpaid payments were above the average of 500 rubles and below the maximum of 200,000 rubles
cnt_not_paid_order_500_200000 = '''
SELECT
    COUNT(*) AS paid_orders_count
FROM
    orders
WHERE
    OrderLineStatusIdsExternalId = 'notpaid' AND (OrderTotalPrice > 500 AND OrderTotalPrice < 200000);
'''

# Channels of Acquisition

## Find the top 5 user acquisition channels by year among the data that has information available
top_5_channels_by_year = '''
WITH ranked_sources AS (
    SELECT
        c.CustomerActionChannelUtmSource AS source,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count,
        strftime('%Y', c.CustomerActionDateTimeUtc) AS year,
        ROW_NUMBER() OVER (PARTITION BY strftime('%Y', c.CustomerActionDateTimeUtc)
                           ORDER BY COUNT(DISTINCT o.OrderCustomerIdsMindboxId) DESC) AS rank
    FROM
        customers c
    JOIN
        orders o ON o.OrderCustomerIdsMindboxId = c.CustomerActionCustomerIdsMindboxId
    WHERE
        -- Исключаем NULL и "none"
        c.CustomerActionChannelUtmSource IS NOT NULL AND c.CustomerActionChannelUtmSource <> 'none'
    GROUP BY
        year, source
)
SELECT
    source,
    SUM(CASE WHEN year = '2021' THEN user_count ELSE 0 END) AS "2021",
    SUM(CASE WHEN year = '2022' THEN user_count ELSE 0 END) AS "2022",
    SUM(CASE WHEN year = '2023' THEN user_count ELSE 0 END) AS "2023",
    SUM(CASE WHEN year = '2024' THEN user_count ELSE 0 END) AS "2024"
FROM
    ranked_sources
WHERE
    rank <= 5  -- Получаем топ-5 для каждого года
GROUP BY
    source
ORDER BY
    source;
'''

## Count how many payments were made through each of these channels and calculate the average check per user
cnt_orders_by_channel = '''
WITH ranked_sources AS (
    SELECT
        strftime('%Y', c.CustomerActionDateTimeUtc) AS year,
        c.CustomerActionChannelUtmSource AS source,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count,
        -- количество оплаченных заказов
        COUNT(CASE WHEN o.OrderLineStatusIdsExternalId = 'Paid' THEN 1 END) AS total_paid_orders,
        -- средний чек
        ROUND(AVG(CASE WHEN o.OrderLineStatusIdsExternalId = 'Paid' THEN o.OrderTotalPrice END), 2) AS avg_check_per_user,
        ROW_NUMBER() OVER (PARTITION BY strftime('%Y', c.CustomerActionDateTimeUtc)
                           ORDER BY COUNT(DISTINCT o.OrderCustomerIdsMindboxId) DESC) AS rank
    FROM
        customers c
    JOIN
        orders o ON o.OrderCustomerIdsMindboxId = c.CustomerActionCustomerIdsMindboxId
    WHERE
        c.CustomerActionChannelUtmSource IS NOT NULL AND c.CustomerActionChannelUtmSource <> 'None'
    GROUP BY
        year, source
)
SELECT
    year,
    source,
    user_count,
    total_paid_orders,
    avg_check_per_user
FROM
    ranked_sources
WHERE
    rank <= 5
ORDER BY
    year, avg_check_per_user DESC;
'''

# Analysis of DAU, MAU, WAU, sticky factor

## Analyze DAU, MAU, WAU, weekly and monthly sticky factor by year
dau_wau_mau_sticky_by_year = '''
WITH daily_users AS (
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS year,
        DATE(o.OrderFirstActionDateTimeUtc) AS action_date,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count
    FROM
        orders o
    GROUP BY
        year, action_date
),
weekly_users AS (
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS year,
        strftime('%W', o.OrderFirstActionDateTimeUtc) AS week,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count
    FROM
        orders o
    GROUP BY
        year, week
),
monthly_users AS (
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS year,
        strftime('%m', o.OrderFirstActionDateTimeUtc) AS month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count
    FROM
        orders o
    GROUP BY
        year, month
),
summary AS (
    SELECT
        'Total' AS year,
        AVG(daily_users.user_count) AS avg_dau,
        (SELECT AVG(wu.user_count) FROM weekly_users wu) AS avg_wau,
        (SELECT AVG(mu.user_count) FROM monthly_users mu) AS avg_mau,
        (AVG(daily_users.user_count) * 1.0 / NULLIF((SELECT AVG(mu.user_count) FROM monthly_users mu), 0)) * 100 AS sticky_factor_mau,
        (AVG(daily_users.user_count) * 1.0 / NULLIF((SELECT AVG(wu.user_count) FROM weekly_users wu), 0)) * 100 AS sticky_factor_wau
    FROM
        daily_users
)
SELECT
    mu.year,
    ROUND(AVG(daily_users.user_count), 2) AS avg_dau,
    (SELECT ROUND(AVG(wu.user_count), 2) FROM weekly_users wu WHERE wu.year = mu.year) AS avg_wau,
    (SELECT ROUND(AVG(mus.user_count), 2) FROM monthly_users mus WHERE mus.year = mu.year) AS avg_mau,
    ROUND((AVG(daily_users.user_count) * 1.0 / NULLIF(AVG(mu.user_count), 0)) * 100, 2) AS sticky_factor_mau,
    ROUND((AVG(daily_users.user_count) * 1.0 / NULLIF((SELECT AVG(wu.user_count) FROM weekly_users wu WHERE wu.year = mu.year), 0)) * 100, 2) AS sticky_factor_wau
FROM
    monthly_users mu
LEFT JOIN
    daily_users ON mu.year = daily_users.year
GROUP BY
    mu.year

UNION ALL

SELECT
    'Total' AS year,
    ROUND(AVG(daily_users.user_count), 2) AS avg_dau,
    (SELECT ROUND(AVG(wu.user_count), 2) FROM weekly_users wu) AS avg_wau,
    (SELECT ROUND(AVG(mu.user_count), 2) FROM monthly_users mu) AS avg_mau,
    ROUND((AVG(daily_users.user_count) * 1.0 / NULLIF((SELECT AVG(mu.user_count) FROM monthly_users mu), 0)) * 100, 2) AS sticky_factor_mau,
    ROUND((AVG(daily_users.user_count) * 1.0 / NULLIF((SELECT AVG(wu.user_count) FROM weekly_users wu), 0)) * 100, 2) AS sticky_factor_wau
FROM
    daily_users
ORDER BY
    year;
'''

## Analyze DAU, MAU, and WAU dynamics by month
dau_wau_mau_sticky_by_month = '''
WITH daily_users AS (
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS month,
        DATE(o.OrderFirstActionDateTimeUtc) AS action_date,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count
    FROM
        orders o
    GROUP BY
        month, action_date
),
weekly_users AS (
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS month,
        strftime('%W', o.OrderFirstActionDateTimeUtc) AS week,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count
    FROM
        orders o
    GROUP BY
        month, week
),
monthly_users AS (
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS user_count
    FROM
        orders o
    GROUP BY
        month
)
-- Main query for aggregating metrics by months
SELECT
    mu.month,
    ROUND(AVG(daily_users.user_count), 2) AS avg_dau,  -- Average DAU for the month
    (SELECT ROUND(AVG(wu.user_count), 2) FROM weekly_users wu WHERE wu.month = mu.month) AS avg_wau,  -- Average WAU for the month
    (SELECT ROUND(AVG(mus.user_count), 2) FROM monthly_users mus WHERE mus.month = mu.month) AS avg_mau,  -- Average MAU for the month
    ROUND((AVG(daily_users.user_count) * 1.0 / NULLIF(AVG(mu.user_count), 0)) * 100, 2) AS sticky_factor_mau,  -- Sticky factor for MAU
    ROUND((AVG(daily_users.user_count) * 1.0 / NULLIF((SELECT AVG(wu.user_count) FROM weekly_users wu WHERE wu.month = mu.month), 0)) * 100, 2) AS sticky_factor_wau  -- Sticky factor for WAU
FROM
    monthly_users mu
LEFT JOIN
    daily_users ON mu.month = daily_users.month
GROUP BY
    mu.month
ORDER BY
    mu.month;
'''

# MARKETING METRICS

# Analysis of CR (Conversion Rate)

## Calculate the Conversion Rate from user to customer

cr_user_to_customer = '''
WITH total_users AS (
    -- Counting the total number of unique users
    SELECT
        COUNT(DISTINCT c.CustomerActionCustomerIdsMindboxId) AS unique_users
    FROM
        customers c
),
paying_users AS (
    -- Counting the number of unique users who made a payment
    SELECT
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS paying_users_count
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
)
SELECT
    tu.unique_users,
    pu.paying_users_count,
    ROUND((pu.paying_users_count * 100.0 / tu.unique_users), 2) AS conversion_rate
FROM
    total_users tu, paying_users pu;
'''

## Calculate the Conversion Rate from user to customer by month
cr_user_to_customer_by_month = '''
WITH monthly_users AS (
    -- Counting the total number of unique users by month
    SELECT
        strftime('%Y-%m', c.CustomerActionDateTimeUtc) AS month,
        COUNT(DISTINCT c.CustomerActionCustomerIdsMindboxId) AS unique_users
    FROM
        customers c
    GROUP BY
        month
),
monthly_paying_users AS (
    -- Counting the number of unique users who made a payment by month
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS paying_users_count
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        month
)
SELECT
    mu.month,
    COALESCE(mu.unique_users, 0) AS unique_users,
    COALESCE(mp.paying_users_count, 0) AS paying_users_count,
    ROUND((COALESCE(mp.paying_users_count, 0) * 100.0 / NULLIF(mu.unique_users, 0)), 2) AS conversion_rate
FROM
    monthly_users mu
LEFT JOIN
    monthly_paying_users mp ON mu.month = mp.month
ORDER BY
    mu.month;
'''

## Calculate the average conversion rate from users to customers, excluding months with a CR of 100%
cr_user_to_customer_without_100 = '''
WITH total_users AS (
    -- Counting the total number of unique users by month
    SELECT
        strftime('%Y-%m', c.CustomerActionDateTimeUtc) AS month,
        COUNT(DISTINCT c.CustomerActionCustomerIdsMindboxId) AS unique_users
    FROM
        customers c
    GROUP BY
        month
),
paying_users AS (
    -- Counting the number of unique users who made a payment by month
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS paying_users_count
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        month
),
conversion_rates AS (
    -- Calculating the conversion rate for each month
    SELECT
        tu.month,
        ROUND((COALESCE(pu.paying_users_count, 0) * 100.0 / tu.unique_users), 2) AS conversion_rate
    FROM
        total_users tu
    LEFT JOIN
        paying_users pu ON tu.month = pu.month
)
-- Calculating the average conversion rate, excluding months with a 100% conversion rate
SELECT
    ROUND(AVG(conversion_rate), 2) AS average_conversion_rate
FROM
    conversion_rates
WHERE
    conversion_rate < 100;
'''

# CLV (Customer Lifetime Value) Analysis

## Calculate the average Customer Lifetime Value of customers by year
avg_clv_users_by_year = '''
WITH customer_metrics AS (
    SELECT
        o.OrderCustomerIdsMindboxId,
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS order_year,
        AVG(o.OrderTotalPrice) AS average_order_value,
        COUNT(o.OrderIdsWebsiteID) AS total_orders,
        (JULIANDAY(MAX(o.OrderFirstActionDateTimeUtc)) - JULIANDAY(MIN(o.OrderFirstActionDateTimeUtc))) / 30 AS customer_ltv_months
    FROM
        orders o
    GROUP BY
        o.OrderCustomerIdsMindboxId, order_year
),
clv_calculation AS (
    SELECT
        order_year,
        SUM(average_order_value * total_orders) / NULLIF(SUM(customer_ltv_months), 0) AS clv
    FROM
        customer_metrics
    GROUP BY
        order_year
)
SELECT
    order_year,
    ROUND(AVG(clv), 2) AS average_clv
FROM
    clv_calculation
GROUP BY
    order_year
ORDER BY
    order_year;
'''

# COMMERCIAL METRICS

# Total Revenue

## Calculate the total amount of donations
total_donate = '''
SELECT
    SUM(OrderTotalPrice) AS total_donate
FROM
    orders
WHERE
    OrderLineStatusIdsExternalId = 'Paid';
'''

## Calculate the total amount of donations for each year
total_donate_by_year = '''
SELECT
    strftime('%Y', OrderFirstActionDateTimeUtc) AS financial_year,
    SUM(OrderTotalPrice) AS total_donate
FROM
    orders
WHERE
    OrderLineStatusIdsExternalId = 'Paid'
GROUP BY
    financial_year
ORDER BY
    financial_year DESC;
'''

# ARPU (Average Revenue per User)

## Calculate ARPU by year
arpu_by_year = '''
WITH yearly_revenue AS (
    -- Summing the total revenue by year
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS year,
        SUM(o.OrderTotalPrice) AS total_income
    FROM
        orders o
    WHERE
        OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        year
),
user_count AS (
    -- Counting the total number of users by year
    SELECT
        strftime('%Y', c.CustomerActionDateTimeUtc) AS year,
        COUNT(DISTINCT c.CustomerActionCustomerIdsMindboxId) AS total_users
    FROM
        customers c
    GROUP BY
        year
)
SELECT
    u.year,
    COALESCE(r.total_income, 0) AS total_income,
    COALESCE(u.total_users, 0) AS total_users,
    (COALESCE(r.total_income, 0) / NULLIF(u.total_users, 0)) AS arpu
FROM
    user_count u
LEFT JOIN
    yearly_revenue r ON u.year = r.year
ORDER BY
    u.year;
'''

# Calculate ARPU monthly by year
arpu_by_month_per_year = '''
WITH monthly_revenue AS (
    -- Summing the total revenue by month
    SELECT
        strftime('%Y-%m', o."OrderFirstActionDateTimeUtc") AS year_month,
        SUM(o."OrderTotalPrice") AS total_income
    FROM
        orders o
    WHERE
        o."OrderLineStatusIdsExternalId" = 'Paid'
    GROUP BY
        year_month
),
user_count AS (
    -- Counting the total number of users by month
    SELECT
        strftime('%Y-%m', c."CustomerActionDateTimeUtc") AS year_month,
        COUNT(DISTINCT c."CustomerActionCustomerIdsMindboxId") AS total_users
    FROM
        customers c
    GROUP BY
        year_month
)
SELECT
    u.year_month,
    COALESCE(r.total_income, 0) AS total_income,
    COALESCE(u.total_users, 0) AS total_users,
    (COALESCE(r.total_income, 0) / NULLIF(u.total_users, 0)) AS arpu
FROM
    user_count u
LEFT JOIN
    monthly_revenue r ON u.year_month = r.year_month
ORDER BY
    u.year_month;
'''

# ARPRU (Average Revenue per Paying User)

## Calculate ARPPU by year
arppu_by_year = '''
WITH yearly_revenue AS (
    -- Summing the total revenue from paying users by year
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS year,
        -- DATE_TTUNC('year', o.OrderFirstActionDateTimeUtc) AS year,
        SUM(o.OrderTotalPrice) AS total_income
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        year
),
paying_users AS (
    -- Counting the number of unique paying users by year
    SELECT
        strftime('%Y', o.OrderFirstActionDateTimeUtc) AS year,
        -- DATE_TRUNC('year', o.OrderFirstActionDateTimeUtc) AS year,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS paying_users_count
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        year
)
SELECT
    pu.year,
    COALESCE(r.total_income, 0) AS total_income,
    COALESCE(pu.paying_users_count, 0) AS paying_users_count,
    (COALESCE(r.total_income, 0) / NULLIF(pu.paying_users_count, 0)) AS arppu
FROM
    paying_users pu
LEFT JOIN
    yearly_revenue r ON pu.year = r.year
ORDER BY
    pu.year;
'''

## Calculate ARPPU monthly by year
arppy_by_month_per_year = '''
WITH monthly_revenue AS (
    -- Summing the total revenue from paying users by month
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS year_month,
        SUM(o.OrderTotalPrice) AS total_income
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        year_month
),
paying_users AS (
    -- Counting the number of unique paying users by month
    SELECT
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS year_month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS paying_users_count
    FROM
        orders o
    WHERE
        o.OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        year_month
)
SELECT
    pu.year_month,
    COALESCE(r.total_income, 0) AS total_income,
    COALESCE(pu.paying_users_count, 0) AS paying_users_count,
    (COALESCE(r.total_income, 0) / NULLIF(pu.paying_users_count, 0)) AS arppu
FROM
    paying_users pu
LEFT JOIN
    monthly_revenue r ON pu.year_month = r.year_month
ORDER BY
    pu.year_month;
'''

# Average Check

## Calculate the average check by year
avg_check_by_year = '''
WITH paid_orders AS (
    SELECT
        strftime('%Y', OrderFirstActionDateTimeUtc) AS year,
        OrderTotalPrice
    FROM orders
    WHERE OrderLineStatusIdsExternalId = 'Paid'
)
SELECT
    year,
    ROUND(AVG(OrderTotalPrice), 2) AS average_check
FROM paid_orders
GROUP BY year

UNION ALL

SELECT
    'Total' AS year,
    ROUND(AVG(OrderTotalPrice), 2) AS average_check
FROM paid_orders;
'''

## Сalculate how much time passes for users between the first and last payment, and the average number of payments 
## per user
avg_orders_by_user_avg_time = '''
WITH user_payments AS (
    SELECT
        OrderCustomerIdsMindboxId,
        MIN(OrderFirstActionDateTimeUtc) AS first_payment_date,
        MAX(OrderFirstActionDateTimeUtc) AS last_payment_date,
        COUNT(*) AS total_payments
    FROM
        orders
    WHERE
        OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        OrderCustomerIdsMindboxId
)
SELECT
    ROUND(AVG(julianday(last_payment_date) - julianday(first_payment_date)), 2) AS avg_days_between_first_last_pay,
    ROUND(AVG(total_payments), 2) AS average_payments_per_user
FROM
    user_payments;
'''

## Calculate the average check per day across all data
avg_check_by_all_years = '''
WITH daily_revenue AS (
    SELECT
        DATE(OrderFirstActionDateTimeUtc) AS payment_date,
        SUM(OrderTotalPrice) AS daily_total_revenue,
        COUNT(*) AS daily_payment_count
    FROM
        orders
    WHERE
        OrderLineStatusIdsExternalId = 'Paid'
    GROUP BY
        payment_date
),
daily_average_check AS (
    SELECT
        daily_total_revenue / daily_payment_count AS average_check
    FROM
        daily_revenue
    WHERE
        daily_payment_count > 0  -- Исключаем дни без платежей
)
SELECT
    ROUND(AVG(average_check), 2) AS overall_average_check
FROM
    daily_average_check;
'''

# RFM Analysis

## Calculate RFM
rfm = '''
WITH order_data AS (
    -- Extract the order date, customer id, and order amount for paid orders
    SELECT DISTINCT
        DATE(OrderFirstActionDateTimeUtc) AS order_date,
        OrderCustomerIdsMindboxId AS customer_id,
        OrderTotalPrice AS price
    FROM
        orders
    WHERE 
        OrderLineStatusIdsExternalId = 'Paid'
),
recency AS (
    -- Define the date of the last order for each customer
    SELECT
        customer_id,
        MAX(order_date) AS last_order_date
    FROM
        order_data
    GROUP BY
        customer_id
),
order_intervals AS (
    SELECT
        customer_id,
        order_date,
        LEAD(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS next_order_date
    FROM order_data
),
average_days_between_orders AS (
    SELECT 
        customer_id,
        COUNT(*) AS total_orders,
        AVG(
            CASE 
                WHEN next_order_date IS NOT NULL THEN
                    julianday(next_order_date) - julianday(order_date)  -- Difference in days between orders
                ELSE
                    NULL
            END
        ) AS avg_days_between_orders
    FROM order_intervals
    GROUP BY customer_id
),
frequency AS (
    SELECT 
        customer_id,
        total_orders,
        avg_days_between_orders,
    -- Order frequency per month (average number of orders per month)
        CASE
            WHEN total_orders > 1 AND avg_days_between_orders > 0 THEN 
                CAST(30 AS REAL) / NULLIF(avg_days_between_orders, 0)  -- Frequency in months
            ELSE 
               NULL  -- If only 1 order or period is 0, return NULL
        END AS order_frequency_per_month
    FROM 
        average_days_between_orders
    GROUP BY 
        customer_id, total_orders, avg_days_between_orders
),
monetary AS (
    -- Calculate the total amount spent by each customer
    SELECT
        customer_id,
        SUM(price) AS total_spent
    FROM
        order_data
    GROUP BY
        customer_id
),
max_date AS (
    -- Find the maximum date across all orders
    SELECT MAX(order_date) AS max_order_date
    FROM order_data
),
rfm AS (
    -- Join Recency (last order date), Frequency (order frequency), and Monetary (total spent) data
    SELECT
        r.customer_id,
        -- Calculate the difference in days between the maximum date and the last order (Recency)
        CAST(julianday((SELECT max_order_date FROM max_date)) - julianday(r.last_order_date) AS INT) AS recency_days,
        -- Number of orders per month (Frequency)
        f.order_frequency_per_month,
        -- Total amount spent (Monetary)
        m.total_spent
    FROM
        recency r
    JOIN
        frequency f ON r.customer_id = f.customer_id
    JOIN
        monetary m ON r.customer_id = m.customer_id
    WHERE CAST(julianday((SELECT max_order_date FROM max_date)) - julianday(r.last_order_date) AS INT) != 0
),
rfm_scores AS (
    SELECT
        r.customer_id,
        r.recency_days,
        r.order_frequency_per_month,
        r.total_spent,
        -- Scores for Recency
        CASE
            WHEN r.recency_days <= (SELECT AVG(recency_days) FROM rfm) THEN 3
            WHEN r.recency_days <= (SELECT AVG(recency_days) FROM rfm) * 2 THEN 2
            WHEN r.recency_days <= (SELECT AVG(recency_days) FROM rfm) * 3 THEN 1
            ELSE 4
        END AS recency_score,
        -- Scores for Frequency
        CASE
            WHEN r.order_frequency_per_month >= (SELECT AVG(order_frequency_per_month) FROM rfm) * 3 THEN 3
            WHEN r.order_frequency_per_month >= (SELECT AVG(order_frequency_per_month) FROM rfm) * 2 THEN 2
            WHEN r.order_frequency_per_month >= (SELECT AVG(order_frequency_per_month) FROM rfm) THEN 1
            ELSE 4
        END AS frequency_score,
        -- Scores for Monetary
        CASE
            WHEN r.total_spent >= (SELECT AVG(total_spent) FROM rfm) * 3 THEN 3
            WHEN r.total_spent >= (SELECT AVG(total_spent) FROM rfm) * 2 THEN 2
            WHEN r.total_spent >= (SELECT AVG(total_spent) FROM rfm) THEN 1
            ELSE 4
        END AS monetary_score
    FROM
        rfm r
),
rfm_groups AS (
    -- Define the RFM group for each customer based on their scores
    SELECT
        customer_id,
        recency_days,
        order_frequency_per_month,
        total_spent,
        recency_score,
        frequency_score,
        monetary_score,
        recency_score || frequency_score || monetary_score AS RFM
    FROM
        rfm_scores
),
rfm_group_percentages AS (
    -- Calculate the percentage of customers in each RFM group
    SELECT
        RFM,
        COUNT(*) AS customer_count,
        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ()), 2) AS percentage_RFM
    FROM
        rfm_groups
    GROUP BY
        RFM
)
-- Final query to display RFM groups, metrics, and the percentage distribution of customers
SELECT
    rg.customer_id,
    rg.recency_days,
    rg.order_frequency_per_month,
    rg.total_spent,
    rg.recency_score,
    rg.frequency_score,
    rg.monetary_score,
    rg.RFM,
    rgp.percentage_RFM,
    CASE
        WHEN rg.RFM IN ('123', '133', '143', '223', '233', '243', '323', '333', '343') THEN 'Key clients'
        WHEN rg.RFM IN ('112', '122', '113', '213', '214', '232', '312') THEN 'Prospective clients'
        WHEN rg.RFM IN ('111', '112', '121', '131', '211', '221', '311') THEN 'One-time donors'
        WHEN rg.RFM IN ('141', '142', '144', '241', '242', '244', '341', '342', '344', '444') THEN 'Rarely active'
        WHEN rg.RFM IN ('114', '124', '132', '213', '222', '224', '234', '324') THEN 'Moderately active'
        WHEN rg.RFM IN ('213', '222', '231', '312', '323') THEN 'Growth potential clients'
        WHEN rg.RFM IN ('221', '311', '321', '322', '331') THEN 'Highly active'
        ELSE 'Lost clients'
    END AS segment_name,
    CASE
        WHEN rg.RFM = '111' THEN 'Inactive clients with low transfer frequency and small donation amounts'
        WHEN rg.RFM = '112' THEN 'Inactive clients with low transfer frequency and medium donation amounts'
        WHEN rg.RFM = '113' THEN 'Inactive clients with low transfer frequency and high donation amounts'
        WHEN rg.RFM = '114' THEN 'Inactive clients with low transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '121' THEN 'Inactive clients with medium transfer frequency and small donation amounts'
        WHEN rg.RFM = '122' THEN 'Inactive clients with medium transfer frequency and medium donation amounts'
        WHEN rg.RFM = '123' THEN 'Inactive clients with medium transfer frequency and high donation amounts'
        WHEN rg.RFM = '124' THEN 'Inactive clients with medium transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '131' THEN 'Inactive clients with high transfer frequency and small donation amounts'
        WHEN rg.RFM = '132' THEN 'Inactive clients with high transfer frequency and medium donation amounts'
        WHEN rg.RFM = '133' THEN 'Inactive clients with high transfer frequency and high donation amounts'
        WHEN rg.RFM = '134' THEN 'Inactive clients with high transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '141' THEN 'Inactive clients with extremely low transfer frequency and small donation amounts'
        WHEN rg.RFM = '142' THEN 'Inactive clients with extremely low transfer frequency and medium donation amounts'
        WHEN rg.RFM = '143' THEN 'Inactive clients with extremely low transfer frequency and high donation amounts'
        WHEN rg.RFM = '144' THEN 'Inactive clients with extremely low transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '211' THEN 'Relatively active clients with low transfer frequency and small donation amounts'
        WHEN rg.RFM = '212' THEN 'Relatively active clients with low transfer frequency and medium donation amounts'
        WHEN rg.RFM = '213' THEN 'Relatively active clients with low transfer frequency and high donation amounts'
        WHEN rg.RFM = '214' THEN 'Relatively active clients with low transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '221' THEN 'Relatively active clients with medium transfer frequency and small donation amounts'
        WHEN rg.RFM = '222' THEN 'Relatively active clients with medium transfer frequency and medium donation amounts'
        WHEN rg.RFM = '223' THEN 'Relatively active clients with medium transfer frequency and high donation amounts'
        WHEN rg.RFM = '224' THEN 'Relatively active clients with medium transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '231' THEN 'Relatively active clients with high transfer frequency and small donation amounts'
        WHEN rg.RFM = '232' THEN 'Relatively active clients with high transfer frequency and medium donation amounts'
        WHEN rg.RFM = '233' THEN 'Relatively active clients with high transfer frequency and high donation amounts'
        WHEN rg.RFM = '234' THEN 'Relatively active clients with high transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '241' THEN 'Relatively active clients with extremely low transfer frequency and small donation amounts'
        WHEN rg.RFM = '242' THEN 'Relatively active clients with extremely low transfer frequency and medium donation amounts'
        when rg.RFM = '243' THEN 'Relatively active clients with extremely low transfer frequency and high donation amounts'
        WHEN rg.RFM = '244' THEN 'Relatively active clients with extremely low transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '311' THEN 'Active clients with low transfer frequency and small donation amounts'
        WHEN rg.RFM = '312' THEN 'Active clients with low transfer frequency and medium donation amounts'
        WHEN rg.RFM = '313' THEN 'Active clients with low transfer frequency and high donation amounts'
        WHEN rg.RFM = '314' THEN 'Active clients with low transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '321' THEN 'Active clients with medium transfer frequency and small donation amounts'
        WHEN rg.RFM = '322' THEN 'Active clients with medium transfer frequency and medium donation amounts'
        WHEN rg.RFM = '323' THEN 'Active clients with medium transfer frequency and high donation amounts'
        WHEN rg.RFM = '324' THEN 'Active clients with medium transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '331' THEN 'Active clients with high transfer frequency and small donation amounts'
        WHEN rg.RFM = '332' THEN 'Active clients with high transfer frequency and medium donation amounts'
        WHEN rg.RFM = '333' THEN 'Active clients with high transfer frequency and high donation amounts'
        WHEN rg.RFM = '334' THEN 'Active clients with high transfer frequency and extremely small donation amounts'
        WHEN rg.RFM = '341' THEN 'Active clients with extremely low transfer frequency and small donation amounts'
        WHEN rg.RFM = '342' THEN 'Active clients with extremely low transfer frequency and medium donation amounts'
        WHEN rg.RFM = '343' THEN 'Active clients with extremely low transfer frequency and high donation amounts'
        WHEN rg.RFM = '344' THEN 'Active clients with extremely low transfer frequency and extremely small donation amounts'
        ELSE 'Churned clients with extremely low transfer frequency and extremely small donation amounts'
    END AS segment_description   
FROM
    rfm_groups rg
JOIN
    rfm_group_percentages rgp ON rg.RFM = rgp.RFM;
'''

    
# Creating a table with RFM segments
rfm_segments = '''
WITH order_data AS (
    -- Extract the order date, customer id, and order amount for paid orders
    SELECT DISTINCT
        DATE(OrderFirstActionDateTimeUtc) AS order_date,
        OrderCustomerIdsMindboxId AS customer_id,
        OrderTotalPrice AS price
    FROM
        orders
    WHERE 
        OrderLineStatusIdsExternalId = 'Paid'
),
recency AS (
    -- Define the date of the last order for each customer
    SELECT
        customer_id,
        MAX(order_date) AS last_order_date
    FROM
        order_data
    GROUP BY
        customer_id
),
order_intervals AS (
    SELECT
        customer_id,
        order_date,
        LEAD(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS next_order_date
    FROM order_data
),
average_days_between_orders AS (
    SELECT 
        customer_id,
        COUNT(*) AS total_orders,
        AVG(
            CASE 
                WHEN next_order_date IS NOT NULL THEN
                    julianday(next_order_date) - julianday(order_date)  -- Difference in days between orders
                ELSE
                    NULL
            END
        ) AS avg_days_between_orders
    FROM order_intervals
    GROUP BY customer_id
),
frequency AS (
    SELECT 
        customer_id,
        total_orders,
        avg_days_between_orders,
    -- Order frequency per month (average number of orders per month)
        CASE
            WHEN total_orders > 1 AND avg_days_between_orders > 0 THEN 
                CAST(30 AS REAL) / NULLIF(avg_days_between_orders, 0)  -- Frequency in months
            ELSE 
               NULL  -- If only 1 order or period is 0, return NULL
        END AS order_frequency_per_month
    FROM 
        average_days_between_orders
    GROUP BY 
        customer_id, total_orders, avg_days_between_orders
),
monetary AS (
    -- Calculate the total amount spent by each customer
    SELECT
        customer_id,
        SUM(price) AS total_spent
    FROM
        order_data
    GROUP BY
        customer_id
),
max_date AS (
    -- Find the maximum date across all orders
    SELECT MAX(order_date) AS max_order_date
    FROM order_data
),
rfm AS (
    -- Join Recency (last order date), Frequency (order frequency), and Monetary (total spent) data
    SELECT
        r.customer_id,
        -- Calculate the difference in days between the maximum date and the last order (Recency)
        CAST(julianday((SELECT max_order_date FROM max_date)) - julianday(r.last_order_date) AS INT) AS recency_days,
        -- Number of orders per month (Frequency)
        f.order_frequency_per_month,
        -- Total amount spent (Monetary)
        m.total_spent
    FROM
        recency r
    JOIN
        frequency f ON r.customer_id = f.customer_id
    JOIN
        monetary m ON r.customer_id = m.customer_id
    WHERE CAST(julianday((SELECT max_order_date FROM max_date)) - julianday(r.last_order_date) AS INT) != 0
),
rfm_scores AS (
    SELECT
        r.customer_id,
        r.recency_days,
        r.order_frequency_per_month,
        r.total_spent,
        -- Scores for Recency
        CASE
            WHEN r.recency_days <= (SELECT AVG(recency_days) FROM rfm) THEN 3
            WHEN r.recency_days <= (SELECT AVG(recency_days) FROM rfm) * 2 THEN 2
            WHEN r.recency_days <= (SELECT AVG(recency_days) FROM rfm) * 3 THEN 1
            ELSE 4
        END AS recency_score,
        -- Scores for Frequency
        CASE
            WHEN r.order_frequency_per_month >= (SELECT AVG(order_frequency_per_month) FROM rfm) * 3 THEN 3
            WHEN r.order_frequency_per_month >= (SELECT AVG(order_frequency_per_month) FROM rfm) * 2 THEN 2
            WHEN r.order_frequency_per_month >= (SELECT AVG(order_frequency_per_month) FROM rfm) THEN 1
            ELSE 4
        END AS frequency_score,
        -- Scores for Monetary
        CASE
            WHEN r.total_spent >= (SELECT AVG(total_spent) FROM rfm) * 3 THEN 3
            WHEN r.total_spent >= (SELECT AVG(total_spent) FROM rfm) * 2 THEN 2
            WHEN r.total_spent >= (SELECT AVG(total_spent) FROM rfm) THEN 1
            ELSE 4
        END AS monetary_score
    FROM
        rfm r
),
rfm_groups AS (
    -- Define the RFM group for each customer based on their scores
    SELECT
        customer_id,
        recency_days,
        order_frequency_per_month,
        total_spent,
        recency_score,
        frequency_score,
        monetary_score,
        recency_score || frequency_score || monetary_score AS RFM
    FROM
        rfm_scores
),
rfm_group_percentages AS (
    -- Calculate the percentage of customers in each RFM group
    SELECT
        RFM,
        COUNT(*) AS customer_count,
        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ()), 2) AS percentage_RFM
    FROM
        rfm_groups
    GROUP BY
        RFM
),
rfm_table AS(
SELECT
    rg.customer_id,
    rg.recency_days,
    rg.order_frequency_per_month,
    rg.total_spent,
    rg.recency_score,
    rg.frequency_score,
    rg.monetary_score,
    rg.RFM,
    rgp.percentage_RFM
FROM
    rfm_groups rg
JOIN
    rfm_group_percentages rgp ON rg.RFM = rgp.RFM
),
rfm_aggregated AS (
    SELECT
        RFM AS rfm_segment,
        COUNT(*) AS users_count_in_segment,
        ROUND(AVG(recency_days), 2) AS avg_lifetime,
        ROUND(AVG(order_frequency_per_month), 2) AS avg_orders_count,
        ROUND(AVG(total_spent), 2) AS mean_donation_per_user,
        SUM(total_spent) AS total_donation_sum,
        CASE
            WHEN RFM IN ('123', '133', '143', '223', '233', '243', '323', '333', '343') THEN 'Key clients'
            WHEN RFM IN ('112', '122', '113', '213', '214', '232', '312') THEN 'Prospective clients'
            WHEN RFM IN ('111', '112', '121', '131', '211', '221', '311') THEN 'One-time donors'
            WHEN RFM IN ('141', '142', '144', '241', '242', '244', '341', '342', '344', '444') THEN 'Rarely active'
            WHEN RFM IN ('114', '124', '132', '213', '222', '224', '234', '324') THEN 'Moderately active'
            WHEN RFM IN ('213', '222', '231', '312', '323') THEN 'Growth potential clients'
            WHEN RFM IN ('221', '311', '321', '322', '331') THEN 'Highly active'
            ELSE 'Lost clients'
        END AS segment_name,
        CASE
            WHEN RFM = '111' THEN 'Inactive clients with low transfer frequency and small donation amounts'
            WHEN RFM = '112' THEN 'Inactive clients with low transfer frequency and medium donation amounts'
            WHEN RFM = '113' THEN 'Inactive clients with low transfer frequency and high donation amounts'
            WHEN RFM = '114' THEN 'Inactive clients with low transfer frequency and extremely small donation amounts'
            WHEN RFM = '121' THEN 'Inactive clients with medium transfer frequency and small donation amounts'
            WHEN RFM = '122' THEN 'Inactive clients with medium transfer frequency and medium donation amounts'
            WHEN RFM = '123' THEN 'Inactive clients with medium transfer frequency and high donation amounts'
            WHEN RFM = '124' THEN 'Inactive clients with medium transfer frequency and extremely small donation amounts'
            WHEN RFM = '131' THEN 'Inactive clients with high transfer frequency and small donation amounts'
            WHEN RFM = '132' THEN 'Inactive clients with high transfer frequency and medium donation amounts'
            WHEN RFM = '133' THEN 'Inactive clients with high transfer frequency and high donation amounts'
            WHEN RFM = '134' THEN 'Inactive clients with high transfer frequency and extremely small donation amounts'
            WHEN RFM = '141' THEN 'Inactive clients with extremely low transfer frequency and small donation amounts'
            WHEN RFM = '142' THEN 'Inactive clients with extremely low transfer frequency and medium donation amounts'
            WHEN RFM = '143' THEN 'Inactive clients with extremely low transfer frequency and high donation amounts'
            WHEN RFM = '144' THEN 'Inactive clients with extremely low transfer frequency and extremely small donation amounts'
            WHEN RFM = '211' THEN 'Relatively active clients with low transfer frequency and small donation amounts'
            WHEN RFM = '212' THEN 'Relatively active clients with low transfer frequency and medium donation amounts'
            WHEN RFM = '213' THEN 'Relatively active clients with low transfer frequency and high donation amounts'
            WHEN RFM = '214' THEN 'Relatively active clients with low transfer frequency and extremely small donation amounts'
            WHEN RFM = '221' THEN 'Relatively active clients with medium transfer frequency and small donation amounts'
            WHEN RFM = '222' THEN 'Relatively active clients with medium transfer frequency and medium donation amounts'
            WHEN RFM = '223' THEN 'Relatively active clients with medium transfer frequency and high donation amounts'
            WHEN RFM = '224' THEN 'Relatively active clients with medium transfer frequency and extremely small donation amounts'
            WHEN RFM = '231' THEN 'Relatively active clients with high transfer frequency and small donation amounts'
            WHEN RFM = '232' THEN 'Relatively active clients with high transfer frequency and medium donation amounts'
            WHEN RFM = '233' THEN 'Relatively active clients with high transfer frequency and high donation amounts'
            WHEN RFM = '234' THEN 'Relatively active clients with high transfer frequency and extremely small donation amounts'
            WHEN RFM = '241' THEN 'Relatively active clients with extremely low transfer frequency and small donation amounts'
            WHEN RFM = '242' THEN 'Relatively active clients with extremely low transfer frequency and medium donation amounts'
            WHEN RFM = '243' THEN 'Relatively active clients with extremely low transfer frequency and high donation amounts'
            WHEN RFM = '244' THEN 'Relatively active clients with extremely low transfer frequency and extremely small donation amounts'
            WHEN RFM = '311' THEN 'Active clients with low transfer frequency and small donation amounts'
            WHEN RFM = '312' THEN 'Active clients with low transfer frequency and medium donation amounts'
            WHEN RFM = '313' THEN 'Active clients with low transfer frequency and high donation amounts'
            WHEN RFM = '314' THEN 'Active clients with low transfer frequency and extremely small donation amounts'
            WHEN RFM = '321' THEN 'Active clients with medium transfer frequency and small donation amounts'
            WHEN RFM = '322' THEN 'Active clients with medium transfer frequency and medium donation amounts'
            WHEN RFM = '323' THEN 'Active clients with medium transfer frequency and high donation amounts'
            WHEN RFM = '324' THEN 'Active clients with medium transfer frequency and extremely small donation amounts'
            WHEN RFM = '331' THEN 'Active clients with high transfer frequency and small donation amounts'
            WHEN RFM = '332' THEN 'Active clients with high transfer frequency and medium donation amounts'
            WHEN RFM = '333' THEN 'Active clients with high transfer frequency and high donation amounts'
            WHEN RFM = '334' THEN 'Active clients with high transfer frequency and extremely small donation amounts'
            WHEN RFM = '341' THEN 'Active clients with extremely low transfer frequency and small donation amounts'
            WHEN RFM = '342' THEN 'Active clients with extremely low transfer frequency and medium donation amounts'
            WHEN RFM = '343' THEN 'Active clients with extremely low transfer frequency and high donation amounts'
            WHEN RFM = '344' THEN 'Active clients with extremely low transfer frequency and extremely small donation amounts'
            ELSE 'Churned clients with extremely low transfer frequency and extremely small donation amounts'
        END AS segment_description        
    FROM
        rfm_table
    GROUP BY
        RFM
)
SELECT
    rfm_segment,
    users_count_in_segment,
    avg_lifetime,
    avg_orders_count,
    mean_donation_per_user,
    total_donation_sum,
    segment_name,
    segment_description
FROM
    rfm_aggregated
ORDER BY
    avg_orders_count DESC;
'''


# COHORT ANALYSIS

# Retention rate

## Calculate retention by cohorts
rr = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with empty IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with empty dates
),
cohorts AS (
    -- Define cohorts (month of the first order for each user)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
    HAVING
        cohort IS NOT NULL  -- Remove rows with empty cohorts
),
orders_cohort AS (
    -- Slice by cohort and order month, calculate the number of unique customers
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (number of unique users in the first month of the cohort)
    SELECT
        cohort,
        MAX(n_customers) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month for the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT strftime('%Y-%m', DATE('2021-01-01', '+' || n || ' months')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
        UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12
        UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18
        UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21
        UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
        UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27
        UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33
        UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL SELECT 36
        UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
        UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42
        UNION ALL SELECT 43 UNION ALL SELECT 44 UNION ALL SELECT 45
    ) t
),
cohort_retention AS (
    -- Calculate lifetime (the difference in months between the cohort and the order month) and retention rate
    SELECT
        oc.cohort,
        m.month AS order_month,
        cs.n_customers_start,
        IFNULL(oc.n_customers, 0) AS n_customers,
        ROUND(IFNULL(oc.n_customers * 100.0 / cs.n_customers_start, 0), 1) AS retention_rate
    FROM
        months m
    LEFT JOIN orders_cohort oc ON m.month = oc.order_month
    LEFT JOIN cohort_size cs ON oc.cohort = cs.cohort
    WHERE
        oc.cohort IS NOT NULL -- Remove empty cohorts
)
-- Create a pivot table with retention rates by cohorts and months
SELECT
    cohort,
    n_customers_start,
    MAX(CASE WHEN order_month = '2021-01' THEN retention_rate END) AS '2021-01',
    MAX(CASE WHEN order_month = '2021-02' THEN retention_rate END) AS '2021-02',
    MAX(CASE WHEN order_month = '2021-03' THEN retention_rate END) AS '2021-03',
    MAX(CASE WHEN order_month = '2021-04' THEN retention_rate END) AS '2021-04',
    MAX(CASE WHEN order_month = '2021-05' THEN retention_rate END) AS '2021-05',
    MAX(CASE WHEN order_month = '2021-06' THEN retention_rate END) AS '2021-06',
    MAX(CASE WHEN order_month = '2021-07' THEN retention_rate END) AS '2021-07',
    MAX(CASE WHEN order_month = '2021-08' THEN retention_rate END) AS '2021-08',
    MAX(CASE WHEN order_month = '2021-09' THEN retention_rate END) AS '2021-09',
    MAX(CASE WHEN order_month = '2021-10' THEN retention_rate END) AS '2021-10',
    MAX(CASE WHEN order_month = '2021-11' THEN retention_rate END) AS '2021-11',
    MAX(CASE WHEN order_month = '2021-12' THEN retention_rate END) AS '2021-12',
    MAX(CASE WHEN order_month = '2022-01' THEN retention_rate END) AS '2022-01',
    MAX(CASE WHEN order_month = '2022-02' THEN retention_rate END) AS '2022-02',
    MAX(CASE WHEN order_month = '2022-03' THEN retention_rate END) AS '2022-03',
    MAX(CASE WHEN order_month = '2022-04' THEN retention_rate END) AS '2022-04',
    MAX(CASE WHEN order_month = '2022-05' THEN retention_rate END) AS '2022-05',
    MAX(CASE WHEN order_month = '2022-06' THEN retention_rate END) AS '2022-06',
    MAX(CASE WHEN order_month = '2022-07' THEN retention_rate END) AS '2022-07',
    MAX(CASE WHEN order_month = '2022-08' THEN retention_rate END) AS '2022-08',
    MAX(CASE WHEN order_month = '2022-09' THEN retention_rate END) AS '2022-09',
    MAX(CASE WHEN order_month = '2022-10' THEN retention_rate END) AS '2022-10',
    MAX(CASE WHEN order_month = '2022-11' THEN retention_rate END) AS '2022-11',
    MAX(CASE WHEN order_month = '2022-12' THEN retention_rate END) AS '2022-12',
    MAX(CASE WHEN order_month = '2023-01' THEN retention_rate END) AS '2023-01',
    MAX(CASE WHEN order_month = '2023-02' THEN retention_rate END) AS '2023-02',
    MAX(CASE WHEN order_month = '2023-03' THEN retention_rate END) AS '2023-03',
    MAX(CASE WHEN order_month = '2023-04' THEN retention_rate END) AS '2023-04',
    MAX(CASE WHEN order_month = '2023-05' THEN retention_rate END) AS '2023-05',
    MAX(CASE WHEN order_month = '2023-06' THEN retention_rate END) AS '2023-06',
    MAX(CASE WHEN order_month = '2023-07' THEN retention_rate END) AS '2023-07',
    MAX(CASE WHEN order_month = '2023-08' THEN retention_rate END) AS '2023-08',
    MAX(CASE WHEN order_month = '2023-09' THEN retention_rate END) AS '2023-09',
    MAX(CASE WHEN order_month = '2023-10' THEN retention_rate END) AS '2023-10',
    MAX(CASE WHEN order_month = '2023-11' THEN retention_rate END) AS '2023-11',
    MAX(CASE WHEN order_month = '2023-12' THEN retention_rate END) AS '2023-12',
    MAX(CASE WHEN order_month = '2024-01' THEN retention_rate END) AS '2024-01',
    MAX(CASE WHEN order_month = '2024-02' THEN retention_rate END) AS '2024-02',
    MAX(CASE WHEN order_month = '2024-03' THEN retention_rate END) AS '2024-03',
    MAX(CASE WHEN order_month = '2024-04' THEN retention_rate END) AS '2024-04',
    MAX(CASE WHEN order_month = '2024-05' THEN retention_rate END) AS '2024-05',
    MAX(CASE WHEN order_month = '2024-06' THEN retention_rate END) AS '2024-06',
    MAX(CASE WHEN order_month = '2024-07' THEN retention_rate END) AS '2024-07',
    MAX(CASE WHEN order_month = '2024-08' THEN retention_rate END) AS '2024-08',
    MAX(CASE WHEN order_month = '2024-09' THEN retention_rate END) AS '2024-09'
FROM
    cohort_retention
GROUP BY
    cohort, n_customers_start
ORDER BY
    cohort;
'''

## Calculate the average RR monthly
rr_by_month_per_year =  '''
WITH cohort AS (
    -- Define when each user first interacted with the product
    SELECT
        CustomerActionCustomerIdsMindboxId,
        strftime('%Y-%m', MIN(CustomerActionDateTimeUtc)) AS cohort_month
    FROM
        customers
    GROUP BY
        CustomerActionCustomerIdsMindboxId
),
retention AS (
    -- Define how many users from each cohort returned in subsequent months
    SELECT
        c.cohort_month,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS active_month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS retained_users
    FROM
        cohort c
    LEFT JOIN
        orders o ON c.CustomerActionCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    GROUP BY
        c.cohort_month, active_month
),
retention_summary AS (
    -- Calculate the retention percentage for each cohort and active month
    SELECT
        co.cohort_month,
        re.active_month,
        re.retained_users,
        COUNT(DISTINCT co.CustomerActionCustomerIdsMindboxId) AS total_users,
        (re.retained_users * 1.0 / NULLIF(COUNT(DISTINCT co.CustomerActionCustomerIdsMindboxId), 0)) * 100 AS retention_rate
    FROM
        retention re
    JOIN
        cohort co ON re.cohort_month = co.cohort_month
    GROUP BY
        co.cohort_month, re.active_month, re.retained_users
),
average_retention AS (
    -- Calculate the average retention rate for each cohort
    SELECT
        cohort_month,
        ROUND(AVG(retention_rate), 2) AS average_retention_rate,
        MAX(total_users) AS total_users  -- Or SUM(total_users), if the total number of users for the entire cohort is needed
    FROM
        retention_summary
    GROUP BY
        cohort_month
)

SELECT
    cohort_month,
    total_users,
    average_retention_rate
FROM
    average_retention
ORDER BY
    cohort_month;
'''

## Define the cohort names in the top 5 and the outsiders by retention (for cohorts with a lifetime of more than 12 months)
top_bottom_5_cohorts_by_rr = '''
WITH cohort AS (
    -- Define when each user first interacted with the product
    SELECT
        CustomerActionCustomerIdsMindboxId,
        strftime('%Y-%m', MIN(CustomerActionDateTimeUtc)) AS cohort_month
    FROM
        customers
    GROUP BY
        CustomerActionCustomerIdsMindboxId
),
retention AS (
    -- Define how many users from each cohort returned in subsequent months
    SELECT
        c.cohort_month,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS active_month,
        COUNT(DISTINCT o.OrderCustomerIdsMindboxId) AS retained_users
    FROM
        cohort c
    LEFT JOIN
        orders o ON c.CustomerActionCustomerIdsMindboxId = o.OrderCustomerIdsMindboxId
    GROUP BY
        c.cohort_month, active_month
),
retention_summary AS (
    -- Calculate the retention percentage for each cohort and active month
    SELECT
        co.cohort_month,
        re.active_month,
        re.retained_users,
        COUNT(DISTINCT co.CustomerActionCustomerIdsMindboxId) AS total_users,
        (re.retained_users * 1.0 / NULLIF(COUNT(DISTINCT co.CustomerActionCustomerIdsMindboxId), 0)) * 100 AS retention_rate
    FROM
        retention re
    JOIN
        cohort co ON re.cohort_month = co.cohort_month
    GROUP BY
        co.cohort_month, re.active_month, re.retained_users
),
average_retention AS (
    -- Calculate the average retention rate for each cohort
    SELECT
        cohort_month,
        ROUND(AVG(retention_rate), 2) AS average_retention_rate,
        COUNT(DISTINCT active_month) AS active_months_count,  -- Count the number of active months
        MAX(total_users) AS total_users
    FROM
        retention_summary
    GROUP BY
        cohort_month
),
filtered_cohorts AS (
    -- Filter cohorts to keep only those with data for at least 12 months
    SELECT
        cohort_month,
        average_retention_rate,
        total_users
    FROM
        average_retention
    WHERE
        active_months_count >= 12
),
top_cohorts AS (
    -- Get the top cohorts with the highest retention
    SELECT
        cohort_month,
        total_users,
        average_retention_rate,
        'top' AS category
    FROM
        filtered_cohorts
    ORDER BY
        average_retention_rate DESC
    LIMIT 5
),
bottom_cohorts AS (
    -- Get the bottom cohorts with the lowest retention
    SELECT
        cohort_month,
        total_users,
        average_retention_rate,
        'bottom' AS category
    FROM
        filtered_cohorts
    ORDER BY
        average_retention_rate ASC
    LIMIT 5
)
-- Combine the results of the top and bottom cohorts
SELECT
    *
FROM
    top_cohorts

UNION ALL

SELECT
    *
FROM
    bottom_cohorts
ORDER BY
    average_retention_rate DESC;
'''

# Average number of purchases for users by cohorts

## Calculate the average number of purchases for users by cohorts
avg_orders_by_cohorts = '''
WITH cohort AS (
    -- Define when each user first interacted with the product
    SELECT
        CustomerActionCustomerIdsMindboxId,
        strftime('%Y-%m', MIN(CustomerActionDateTimeUtc)) AS cohort_month
    FROM
        customers
    GROUP BY
        CustomerActionCustomerIdsMindboxId
),
purchases AS (
    -- Count the number of purchases for each user
    SELECT
        o.OrderCustomerIdsMindboxId,
        COUNT(*) AS purchase_count
    FROM
        orders o
    GROUP BY
        o.OrderCustomerIdsMindboxId
),
cohort_purchases AS (
    -- Join cohorts with purchase counts, replacing NULL with 0
    SELECT
        c.cohort_month,
        COALESCE(p.purchase_count, 0) AS purchase_count
    FROM
        cohort c
    LEFT JOIN
        purchases p ON c.CustomerActionCustomerIdsMindboxId = p.OrderCustomerIdsMindboxId
)
-- Calculate the average number of purchases for each cohort
SELECT
    cohort_month,
    ROUND(AVG(purchase_count), 2) AS average_purchases_per_user
FROM
    cohort_purchases
GROUP BY
    cohort_month
ORDER BY
    cohort_month;
'''

## Top-5 cohorts and 5 outsider cohorts by average donations
top_bottom_5_avg_orders_by_cohort = '''
WITH cohort AS (
    -- Define when each user first interacted with the product
    SELECT
        CustomerActionCustomerIdsMindboxId,
        strftime('%Y-%m', MIN(CustomerActionDateTimeUtc)) AS cohort_month
    FROM
        customers
    GROUP BY
        CustomerActionCustomerIdsMindboxId
),
purchases AS (
    -- Count the number of purchases for each user
    SELECT
        o.OrderCustomerIdsMindboxId,
        COUNT(*) AS purchase_count
    FROM
        orders o
    GROUP BY
        o.OrderCustomerIdsMindboxId
),
cohort_purchases AS (
    -- Join cohorts with purchase counts
    SELECT
        c.cohort_month,
        IFNULL(p.purchase_count, 0) AS purchase_count
    FROM
        cohort c
    LEFT JOIN
        purchases p ON c.CustomerActionCustomerIdsMindboxId = p.OrderCustomerIdsMindboxId
),
average_purchases AS (
    -- Calculate the average number of purchases for each cohort
    SELECT
        cohort_month,
        ROUND(AVG(purchase_count), 2) AS average_purchases_per_user
    FROM
        cohort_purchases
    GROUP BY
        cohort_month
),
top_cohorts AS (
    -- Select the top-5 cohorts with the highest average number of purchases
    SELECT
        cohort_month,
        average_purchases_per_user,
        'top' AS category
    FROM
        average_purchases
    ORDER BY
        average_purchases_per_user DESC
    LIMIT 5
),
bottom_cohorts AS (
    -- Select 5 cohorts with the lowest average number of purchases
    SELECT
        cohort_month,
        average_purchases_per_user,
        'bottom' AS category
    FROM
        average_purchases
    ORDER BY
        average_purchases_per_user ASC
    LIMIT 5
)
-- Combine the results
SELECT
    *
FROM
    top_cohorts

UNION ALL

SELECT
    *
FROM
    bottom_cohorts
ORDER BY
    category DESC, average_purchases_per_user DESC;
'''

## Average number of purchases across all cohorts
avg_orders_by_all_cohorts = '''
WITH cohort AS (
    -- Define when each user first interacted with the product
    SELECT
        CustomerActionCustomerIdsMindboxId,
        strftime('%Y-%m', MIN(CustomerActionDateTimeUtc)) AS cohort_month
    FROM
        customers
    GROUP BY
        CustomerActionCustomerIdsMindboxId
),
purchases AS (
    -- Count the number of purchases for each user
    SELECT
        o.OrderCustomerIdsMindboxId,
        COUNT(*) AS purchase_count
    FROM
        orders o
    GROUP BY
        o.OrderCustomerIdsMindboxId
),
cohort_purchases AS (
    -- Join cohorts with purchase counts, replacing NULL with 0
    SELECT
        c.cohort_month,
        COALESCE(p.purchase_count, 0) AS purchase_count
    FROM
        cohort c
    LEFT JOIN
        purchases p ON c.CustomerActionCustomerIdsMindboxId = p.OrderCustomerIdsMindboxId
),
average_purchases AS (
    -- Calculate the average number of purchases for each cohort
    SELECT
        cohort_month,
        ROUND(AVG(purchase_count), 2) AS average_purchases_per_user
    FROM
        cohort_purchases
    GROUP BY
        cohort_month
)
-- Calculate the overall average of the average purchases across cohorts
SELECT
    ROUND(AVG(average_purchases_per_user), 2) AS overall_average_purchases
FROM
    average_purchases;
'''

# Average check by cohorts
avg_check_by_cohorts = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month,
        o.OrderTotalPrice AS order_total_amount
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Exclude rows with empty IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Exclude rows with empty dates
),
cohorts AS (
    -- Define cohorts (the month of the first order for each user)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
    HAVING
        cohort IS NOT NULL  -- Exclude rows with empty cohorts
),
orders_cohort AS (
    -- Cohort and order month slice, count unique customers and total sales
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total_amount) AS total_sales
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (number of unique users in the first month of the cohort)
    SELECT
        cohort,
        MAX(n_customers) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month for the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT strftime('%Y-%m', DATE('2021-01-01', '+' || n || ' months')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
        UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12
        UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18
        UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21
        UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
        UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27
        UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33
        UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL SELECT 36
        UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
        UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42
        UNION ALL SELECT 43 UNION ALL SELECT 44 UNION ALL SELECT 45
    ) t
),
cohort_avg_check AS (
    -- Calculate the average check per user
    SELECT
        oc.cohort,
        m.month AS order_month,
        cs.n_customers_start,
        IFNULL(oc.n_customers, 0) AS n_customers,
        IFNULL(oc.total_sales, 0) AS total_sales,
        ROUND(IFNULL(oc.total_sales * 1.0 / NULLIF(oc.n_customers, 0), 0), 2) AS average_check  -- Average check
    FROM
        months m
    LEFT JOIN
        orders_cohort oc ON m.month = oc.order_month
    LEFT JOIN
        cohort_size cs ON oc.cohort = cs.cohort
    WHERE
        oc.cohort IS NOT NULL -- Exclude empty cohorts
)

-- Create a pivot table with the average check by cohort and month
SELECT
    cohort,
    n_customers_start,
    MAX(CASE WHEN order_month = '2021-01' THEN average_check END) AS '2021-01',
    MAX(CASE WHEN order_month = '2021-02' THEN average_check END) AS '2021-02',
    MAX(CASE WHEN order_month = '2021-03' THEN average_check END) AS '2021-03',
    MAX(CASE WHEN order_month = '2021-04' THEN average_check END) AS '2021-04',
    MAX(CASE WHEN order_month = '2021-05' THEN average_check END) AS '2021-05',
    MAX(CASE WHEN order_month = '2021-06' THEN average_check END) AS '2021-06',
    MAX(CASE WHEN order_month = '2021-07' THEN average_check END) AS '2021-07',
    MAX(CASE WHEN order_month = '2021-08' THEN average_check END) AS '2021-08',
    MAX(CASE WHEN order_month = '2021-09' THEN average_check END) AS '2021-09',
    MAX(CASE WHEN order_month = '2021-10' THEN average_check END) AS '2021-10',
    MAX(CASE WHEN order_month = '2021-11' THEN average_check END) AS '2021-11',
    MAX(CASE WHEN order_month = '2021-12' THEN average_check END) AS '2021-12',
    MAX(CASE WHEN order_month = '2022-01' THEN average_check END) AS '2022-01',
    MAX(CASE WHEN order_month = '2022-02' THEN average_check END) AS '2022-02',
    MAX(CASE WHEN order_month = '2022-03' THEN average_check END) AS '2022-03',
    MAX(CASE WHEN order_month = '2022-04' THEN average_check END) AS '2022-04',
    MAX(CASE WHEN order_month = '2022-05' THEN average_check END) AS '2022-05',
    MAX(CASE WHEN order_month = '2022-06' THEN average_check END) AS '2022-06',
    MAX(CASE WHEN order_month = '2022-07' THEN average_check END) AS '2022-07',
    MAX(CASE WHEN order_month = '2022-08' THEN average_check END) AS '2022-08',
    MAX(CASE WHEN order_month = '2022-09' THEN average_check END) AS '2022-09',
    MAX(CASE WHEN order_month = '2022-10' THEN average_check END) AS '2022-10',
    MAX(CASE WHEN order_month = '2022-11' THEN average_check END) AS '2022-11',
    MAX(CASE WHEN order_month = '2022-12' THEN average_check END) AS '2022-12',
    MAX(CASE WHEN order_month = '2023-01' THEN average_check END) AS '2023-01',
    MAX(CASE WHEN order_month = '2023-02' THEN average_check END) AS '2023-02',
    MAX(CASE WHEN order_month = '2023-03' THEN average_check END) AS '2023-03',
    MAX(CASE WHEN order_month = '2023-04' THEN average_check END) AS '2023-04',
    MAX(CASE WHEN order_month = '2023-05' THEN average_check END) AS '2023-05',
    MAX(CASE WHEN order_month = '2023-06' THEN average_check END) AS '2023-06',
    MAX(CASE WHEN order_month = '2023-07' THEN average_check END) AS '2023-07',
    MAX(CASE WHEN order_month = '2023-08' THEN average_check END) AS '2023-08',
    MAX(CASE WHEN order_month = '2023-09' THEN average_check END) AS '2023-09',
    MAX(CASE WHEN order_month = '2023-10' THEN average_check END) AS '2023-10',
    MAX(CASE WHEN order_month = '2023-11' THEN average_check END) AS '2023-11',
    MAX(CASE WHEN order_month = '2023-12' THEN average_check END) AS '2023-12',
    MAX(CASE WHEN order_month = '2024-01' THEN average_check END) AS '2024-01',
    MAX(CASE WHEN order_month = '2024-02' THEN average_check END) AS '2024-02',
    MAX(CASE WHEN order_month = '2024-03' THEN average_check END) AS '2024-03',
    MAX(CASE WHEN order_month = '2024-04' THEN average_check END) AS '2024-04',
    MAX(CASE WHEN order_month = '2024-05' THEN average_check END) AS '2024-05',
    MAX(CASE WHEN order_month = '2024-06' THEN average_check END) AS '2024-06',
    MAX(CASE WHEN order_month = '2024-07' THEN average_check END) AS '2024-07',
    MAX(CASE WHEN order_month = '2024-08' THEN average_check END) AS '2024-08',
    MAX(CASE WHEN order_month = '2024-09' THEN average_check END) AS '2024-09',
    ROUND(AVG(average_check), 2) AS average_cohort_check
FROM
    cohort_avg_check
GROUP BY
    cohort, n_customers_start
ORDER BY
    cohort;
'''

## Calculate the average check by cohorts
avg_check_by_cohorts_by_month = '''
WITH orders_data AS (
    -- Convert data to the required format and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month,
        o.OrderTotalPrice AS order_total_amount
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with empty IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with empty dates
),
cohorts AS (
    -- Define cohorts (the month of the first order for each user)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
),
orders_cohort AS (
    -- Slice by cohort and order month, calculate the number of unique customers and total order amount
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total_amount) AS total_sales
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (the number of unique users in the first month of the cohort)
    SELECT
        cohort,
        MAX(n_customers) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Consider only the first month for the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT strftime('%Y-%m', DATE('2021-01-01', '+' || n || ' month')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
        UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12
        UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18
        UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21
        UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
        UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27
        UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33
        UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL SELECT 36
        UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
        UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42
        UNION ALL SELECT 43 UNION ALL SELECT 44
    ) t
),
cohort_avg_check AS (
    -- Calculate the average check per user
    SELECT
        oc.cohort,
        m.month AS order_month,
        cs.n_customers_start,
        COALESCE(oc.n_customers, 0) AS n_customers,
        COALESCE(oc.total_sales, 0) AS total_sales,
        ROUND(COALESCE(oc.total_sales * 1.0 / NULLIF(oc.n_customers, 0), 0), 2) AS average_check
    FROM
        months m
    LEFT JOIN
        orders_cohort oc ON m.month = oc.order_month
    LEFT JOIN
        cohort_size cs ON oc.cohort = cs.cohort
)
-- Get cohorts and their average check
SELECT
    cohort,
    ROUND(AVG(average_check), 2) AS average_check
FROM
    cohort_avg_check
GROUP BY
    cohort
ORDER BY
    cohort;
'''

## Top 5 cohorts and 5 cohort outsiders by average check
top_bottom_5_cohorts_by_avg_check = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month,
        o.OrderTotalPrice AS order_total_amount  - Adding the total order amount
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with empty IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with empty dates
),
cohorts AS (
    -- Define cohorts (first order month for each customer)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
),
orders_cohort AS (
    -- Slice by cohort and order month, count unique customers and total sales
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total_amount) AS total_sales
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (number of unique users in the first month of the cohort)
    SELECT
        cohort,
        MAX(n_customers) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month for the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT
        strftime('%Y-%m', DATE('2021-01-01', '+' || n || ' month')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
        UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12
        UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18
        UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21
        UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
        UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27
        UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33
        UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL SELECT 36
        UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
        UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42
        UNION ALL SELECT 43 UNION ALL SELECT 44
    ) t
),
cohort_avg_check AS (
    -- Calculate the average check per user
    SELECT
        oc.cohort,
        m.month AS order_month,
        cs.n_customers_start,
        COALESCE(oc.n_customers, 0) AS n_customers,
        COALESCE(oc.total_sales, 0) AS total_sales,
        ROUND(COALESCE(oc.total_sales * 1.0 / NULLIF(oc.n_customers, 0), 0), 2) AS average_check
    FROM
        months m
    LEFT JOIN orders_cohort oc ON m.month = oc.order_month
    LEFT JOIN cohort_size cs ON oc.cohort = cs.cohort
),
cohort_avg AS (
    -- Get the average check per cohort
    SELECT
        cohort,
        ROUND(AVG(average_check), 2) AS average_check
    FROM
        cohort_avg_check
    GROUP BY
        cohort
)
-- Get the top 5 cohorts and the 5 bottom cohorts
SELECT
    cohort,
    average_check,
    CASE
        WHEN rank <= 5 THEN 'top'
        ELSE 'bottom'
    END AS top_or_bottom
FROM (
    SELECT
        cohort,
        average_check,
        ROW_NUMBER() OVER (ORDER BY average_check DESC) AS rank
    FROM
        cohort_avg
) AS ranked
WHERE
    rank <= 5 OR rank > (SELECT COUNT(*) FROM cohort_avg) - 5
ORDER BY
    average_check DESC;
'''

# LTV (lifetime value) by cohorts with accumulation

## Calculate the LTV with accumulation by cohorts
ltv_cumsum_by_cohorts = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month,
        o.OrderTotalPrice AS order_total
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with null IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with null dates
),
cohorts AS (
    -- Define cohorts (the month of the first order for each user)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
    HAVING
        cohort IS NOT NULL  -- Remove rows with null cohorts
),
orders_cohort AS (
    -- Slice by cohort and order month, count unique customers and total revenue
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total) AS total_revenue
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (unique users in the first month of the cohort)
    SELECT
        cohort,
        COUNT(DISTINCT order_month) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month for the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT strftime('%Y-%m', DATE('2021-01-01', '+' || n || ' months')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
        UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12
        UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18
        UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21
        UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
        UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27
        UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33
        UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL SELECT 36
        UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
        UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42
        UNION ALL SELECT 43 UNION ALL SELECT 44
    ) t
),
cohort_ltv AS (
    -- Calculate LTV for each cohort and month
    SELECT
        oc.cohort,
        m.month AS order_month,
        cs.n_customers_start,
        IFNULL(oc.n_customers, 0) AS n_customers,
        ROUND(IFNULL(oc.total_revenue, 0) / NULLIF(cs.n_customers_start, 0), 2) AS ltv
    FROM
        months m
    LEFT JOIN
        orders_cohort oc ON m.month = oc.order_month
    LEFT JOIN
        cohort_size cs ON oc.cohort = cs.cohort
    WHERE
        oc.cohort IS NOT NULL -- Remove empty cohorts
),
cohort_ltv_accumulated AS (
    -- Accumulate LTV over months
    SELECT
        cohort,
        order_month,
        n_customers_start,
        ltv,
        SUM(ltv) OVER (PARTITION BY cohort ORDER BY order_month) AS accumulated_ltv
    FROM
        cohort_ltv
)
-- Create a pivot table with accumulated LTV by cohort and month
SELECT
    cohort,
    n_customers_start,
    MAX(CASE WHEN order_month = '2021-01' THEN accumulated_ltv END) AS '2021-01',
    MAX(CASE WHEN order_month = '2021-02' THEN accumulated_ltv END) AS '2021-02',
    MAX(CASE WHEN order_month = '2021-03' THEN accumulated_ltv END) AS '2021-03',
    MAX(CASE WHEN order_month = '2021-04' THEN accumulated_ltv END) AS '2021-04',
    MAX(CASE WHEN order_month = '2021-05' THEN accumulated_ltv END) AS '2021-05',
    MAX(CASE WHEN order_month = '2021-06' THEN accumulated_ltv END) AS '2021-06',
    MAX(CASE WHEN order_month = '2021-07' THEN accumulated_ltv END) AS '2021-07',
    MAX(CASE WHEN order_month = '2021-08' THEN accumulated_ltv END) AS '2021-08',
    MAX(CASE WHEN order_month = '2021-09' THEN accumulated_ltv END) AS '2021-09',
    MAX(CASE WHEN order_month = '2021-10' THEN accumulated_ltv END) AS '2021-10',
    MAX(CASE WHEN order_month = '2021-11' THEN accumulated_ltv END) AS '2021-11',
    MAX(CASE WHEN order_month = '2021-12' THEN accumulated_ltv END) AS '2021-12',
    MAX(CASE WHEN order_month = '2022-01' THEN accumulated_ltv END) AS '2022-01',
    MAX(CASE WHEN order_month = '2022-02' THEN accumulated_ltv END) AS '2022-02',
    MAX(CASE WHEN order_month = '2022-03' THEN accumulated_ltv END) AS '2022-03',
    MAX(CASE WHEN order_month = '2022-04' THEN accumulated_ltv END) AS '2022-04',
    MAX(CASE WHEN order_month = '2022-05' THEN accumulated_ltv END) AS '2022-05',
    MAX(CASE WHEN order_month = '2022-06' THEN accumulated_ltv END) AS '2022-06',
    MAX(CASE WHEN order_month = '2022-07' THEN accumulated_ltv END) AS '2022-07',
    MAX(CASE WHEN order_month = '2022-08' THEN accumulated_ltv END) AS '2022-08',
    MAX(CASE WHEN order_month = '2022-09' THEN accumulated_ltv END) AS '2022-09',
    MAX(CASE WHEN order_month = '2022-10' THEN accumulated_ltv END) AS '2022-10',
    MAX(CASE WHEN order_month = '2022-11' THEN accumulated_ltv END) AS '2022-11',
    MAX(CASE WHEN order_month = '2022-12' THEN accumulated_ltv END) AS '2022-12',
    MAX(CASE WHEN order_month = '2023-01' THEN accumulated_ltv END) AS '2023-01',
    MAX(CASE WHEN order_month = '2023-02' THEN accumulated_ltv END) AS '2023-02',
    MAX(CASE WHEN order_month = '2023-03' THEN accumulated_ltv END) AS '2023-03',
    MAX(CASE WHEN order_month = '2023-04' THEN accumulated_ltv END) AS '2023-04',
    MAX(CASE WHEN order_month = '2023-05' THEN accumulated_ltv END) AS '2023-05',
    MAX(CASE WHEN order_month = '2023-06' THEN accumulated_ltv END) AS '2023-06',
    MAX(CASE WHEN order_month = '2023-07' THEN accumulated_ltv END) AS '2023-07',
    MAX(CASE WHEN order_month = '2023-08' THEN accumulated_ltv END) AS '2023-08',
    MAX(CASE WHEN order_month = '2023-09' THEN accumulated_ltv END) AS '2023-09',
    MAX(CASE WHEN order_month = '2023-10' THEN accumulated_ltv END) AS '2023-10',
    MAX(CASE WHEN order_month = '2023-11' THEN accumulated_ltv END) AS '2023-11',
    MAX(CASE WHEN order_month = '2023-12' THEN accumulated_ltv END) AS '2023-12',
    MAX(CASE WHEN order_month = '2024-01' THEN accumulated_ltv END) AS '2024-01',
    MAX(CASE WHEN order_month = '2024-02' THEN accumulated_ltv END) AS '2024-02',
    MAX(CASE WHEN order_month = '2024-03' THEN accumulated_ltv END) AS '2024-03',
    MAX(CASE WHEN order_month = '2024-04' THEN accumulated_ltv END) AS '2024-04',
    MAX(CASE WHEN order_month = '2024-05' THEN accumulated_ltv END) AS '2024-05',
    MAX(CASE WHEN order_month = '2024-06' THEN accumulated_ltv END) AS '2024-06',
    MAX(CASE WHEN order_month = '2024-07' THEN accumulated_ltv END) AS '2024-07',
    MAX(CASE WHEN order_month = '2024-08' THEN accumulated_ltv END) AS '2024-08',
    MAX(CASE WHEN order_month = '2024-09' THEN accumulated_ltv END) AS '2024-09'
FROM
    cohort_ltv_accumulated
GROUP BY
    cohort, n_customers_start
ORDER BY
    cohort;
'''

## Monthly LTV calculation
ltv_cumsum_by_cohorts_by_day = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(OrderFirstActionDateTimeUtc) AS order_date,
        STRFTIME('%Y-%m', OrderFirstActionDateTimeUtc) AS order_month,
        OrderTotalPrice AS order_total_amount
    FROM
        orders
    WHERE
        OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with null IDs
        AND OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with null dates
),
cohorts AS (
    -- Define cohorts (the month of the first order for each user)
    SELECT
        order_customer_mindbox_id,
        MIN(order_month) AS cohort
    FROM
        orders_data
    GROUP BY
        order_customer_mindbox_id
),
orders_cohort AS (
    -- Slice by cohort and order month, calculate the number of unique customers and total sales
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total_amount) AS total_sales
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (the number of unique users in the first month of the cohort)
    SELECT
        cohort,
        MAX(n_customers) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month of the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT STRFTIME('%Y-%m', DATE('2021-01-01', '+' || n || ' month')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
        UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
        UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20
        UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24 UNION ALL SELECT 25
        UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34 UNION ALL SELECT 35
        UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39 UNION ALL SELECT 40
        UNION ALL SELECT 41 UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL SELECT 44
    )
),
cohort_ltv AS (
    -- Calculate the accumulated LTV for each cohort's lifetime month
    SELECT
        oc.cohort,
        m.month AS order_month,
        cs.n_customers_start,
        IFNULL(SUM(oc.total_sales) OVER (PARTITION BY oc.cohort ORDER BY m.month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) AS ltv -- Накопительный LTV
    FROM
        months m
    LEFT JOIN orders_cohort oc ON m.month = oc.order_month
    LEFT JOIN cohort_size cs ON oc.cohort = cs.cohort
)
SELECT
    cohort,
    n_customers_start,
    order_month,
    ltv
FROM
    cohort_ltv
ORDER BY
    cohort, order_month;
'''

## Cumulative LTV Calculation by Cohorts
ltv_cumsum_by_cohorts_by_month = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month,
        o.OrderTotalPrice AS order_total -- Add the order total amount
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with null IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with null dates
),
cohorts AS (
    -- Define cohorts (the month of the first order for each user)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
    HAVING
        cohort IS NOT NULL  -- Remove rows with null cohorts
),
orders_cohort AS (
    -- Slice by cohort and order month, count unique customers and total sales
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total) AS total_revenue
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (number of unique users in the first month of the cohort)
    SELECT
        cohort,
        COUNT(DISTINCT order_month) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month of the cohort
    GROUP BY
        cohort
),
months AS (
    -- Generate all months from 2021-01 to 2024-09
    SELECT strftime('%Y-%m', DATE('2021-01-01', '+' || n || ' months')) AS month
    FROM (
        SELECT 0 AS n
        UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
        UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12
        UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
        UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18
        UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21
        UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
        UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27
        UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
        UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33
        UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL SELECT 36
        UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
        UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42
        UNION ALL SELECT 43 UNION ALL SELECT 44
    ) t
),
cohort_ltv AS (
    -- Calculate LTV for each cohort and month
    SELECT
        oc.cohort,
        COALESCE(oc.n_customers, 0) AS n_customers,
        ROUND(COALESCE(oc.total_revenue, 0) / NULLIF(cs.n_customers_start, 0), 2) AS ltv
    FROM
        orders_cohort oc
    LEFT JOIN cohort_size cs ON oc.cohort = cs.cohort
    WHERE
        oc.cohort IS NOT NULL -- Remove null cohorts
)
-- Create a table with cohort and LTV
SELECT
    cohort,
    SUM(ltv) AS ltv
FROM
    cohort_ltv
GROUP BY
    cohort
ORDER BY
    cohort;
'''

## Top-5 Cohorts and 5 Cohorts Outsiders by LTV
top_bottom_5_cohorts_by_ltv = '''
WITH orders_data AS (
    -- Format the data and extract the order month
    SELECT
        o.OrderCustomerIdsMindboxId AS order_customer_mindbox_id,
        DATE(o.OrderFirstActionDateTimeUtc) AS order_date,
        strftime('%Y-%m', o.OrderFirstActionDateTimeUtc) AS order_month,
        o.OrderTotalPrice AS order_total
    FROM
        orders o
    WHERE
        o.OrderCustomerIdsMindboxId IS NOT NULL  -- Remove rows with null IDs
        AND o.OrderFirstActionDateTimeUtc IS NOT NULL  -- Remove rows with null dates
),
cohorts AS (
    -- Define cohorts (the month of the first order for each user)
    SELECT
        od.order_customer_mindbox_id,
        MIN(od.order_month) AS cohort
    FROM
        orders_data od
    GROUP BY
        od.order_customer_mindbox_id
    HAVING
        cohort IS NOT NULL  -- Remove rows with null cohorts
),
orders_cohort AS (
    -- Slice by cohort and order month, count unique customers and total sales
    SELECT
        c.cohort,
        od.order_month,
        COUNT(DISTINCT od.order_customer_mindbox_id) AS n_customers,
        SUM(od.order_total) AS total_revenue
    FROM
        orders_data od
    JOIN
        cohorts c ON od.order_customer_mindbox_id = c.order_customer_mindbox_id
    GROUP BY
        c.cohort, od.order_month
),
cohort_size AS (
    -- Get the size of each cohort (number of unique users in the first month of the cohort)
    SELECT
        cohort,
        COUNT(DISTINCT order_month) AS n_customers_start
    FROM
        orders_cohort
    WHERE
        cohort = order_month  -- Only consider the first month of the cohort
    GROUP BY
        cohort
),
cohort_ltv AS (
    -- Calculate LTV for each cohort and month
    SELECT
        oc.cohort,
        COALESCE(oc.n_customers, 0) AS n_customers,
        ROUND(COALESCE(oc.total_revenue, 0) / NULLIF(cs.n_customers_start, 0), 2) AS ltv
    FROM
        orders_cohort oc
    LEFT JOIN cohort_size cs ON oc.cohort = cs.cohort
    WHERE
        oc.cohort IS NOT NULL -- Remove null cohorts
)

-- Get the top-5 cohorts and the bottom-5 cohorts
SELECT
    cohort,
    ltv,
    CASE
        WHEN rank <= 5 THEN 'top'
        ELSE 'bottom'
    END AS category
FROM (
    SELECT
        cohort,
        SUM(ltv) AS ltv,
        ROW_NUMBER() OVER (ORDER BY SUM(ltv) DESC) AS rank
    FROM
        cohort_ltv
    GROUP BY
        cohort
) AS ranked
WHERE
    rank <= 5 OR rank > (SELECT COUNT(DISTINCT cohort) FROM cohort_ltv) - 5
ORDER BY
    ltv DESC;
'''

