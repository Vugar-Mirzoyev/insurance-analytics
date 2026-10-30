# DAX measures

These are the measures of the ready-made report
(`insurance_analytics.SemanticModel/definition/tables/*.tmdl`). To build the report by
hand, copy each block into **Modeling > New measure** on the table named in its heading.
Table names are the CSV file names from `data/processed/`. Every ratio divides two
sums, so it is right at any filter level; never average a ratio column.

Market values are in thousand AZN, as CBAR publishes them. The `(mln AZN)` measures
divide by 1,000 for cards and charts.

> **Name clash.** Power BI compares names without case. A measure called `Premiums`
> on `insurer_quarterly` clashes with the column `premiums`, and the project does not
> open ("a column with the same name already exists"). That is why the base measures
> are called `Total Premiums` and `Total Claims Paid`.

## Date table

In the ready-made report the `Date` table is built in Power Query: it runs from
1 November 2015 to the end of the last month in `market_monthly.csv`, so it moves
forward by itself when a new CBAR file is loaded. For a manual build, this DAX table
does the same with a fixed end date (**Modeling > New table**):

```dax
Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2015, 11, 1 ), DATE ( 2026, 9, 30 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "Year-Quarter", YEAR ( [Date] ) & "-Q" & QUARTER ( [Date] ),
    "Quarter Label", "Q" & QUARTER ( [Date] ) & "-" & RIGHT ( YEAR ( [Date] ), 2 ),
    "Month", FORMAT ( [Date], "yyyy-mm" ),
    "Month No", MONTH ( [Date] )
)
```

Mark it as a date table (**Table tools > Mark as date table**, column `Date`) and sort
`Quarter Label` by `Year-Quarter` (**Column tools > Sort by column**).

The table must end on the last day CBAR has published (30 September 2026). If it ran
to 31 December, selecting 2026 would compare 9 months of 2026 with all 12 months of
2025 in `YoY %` and show -17% instead of +7.9%.

## Quarter start column (insurer_quarterly and class_quarterly)

The ready-made report adds it in Power Query. For a manual build:

```dax
quarter_start = DATE ( insurer_quarterly[year], insurer_quarterly[quarter] * 3 - 2, 1 )
```

```dax
quarter_start = DATE ( class_quarterly[year], class_quarterly[quarter] * 3 - 2, 1 )
```

## fact_portfolio

```dax
Written Premium = SUM ( fact_portfolio[written_premium] )
```

```dax
Earned Premium = SUM ( fact_portfolio[earned_premium] )
```

```dax
Claims Cost = SUM ( fact_portfolio[claims_cost] )
```

```dax
Claim Count = SUM ( fact_portfolio[claim_count] )
```

```dax
Exposure Years = SUM ( fact_portfolio[exposure_years] )
```

```dax
Loss Ratio = DIVIDE ( [Claims Cost], [Earned Premium] )
```

```dax
Loss Ratio (Written) = DIVIDE ( [Claims Cost], [Written Premium] )
```

```dax
Loss Ratio (Finished) =
VAR ValuationDate = DATE ( 2018, 12, 31 )
RETURN
    CALCULATE (
        [Loss Ratio],
        KEEPFILTERS ( fact_portfolio[month_start] <= EDATE ( ValuationDate, -12 ) )
    )
```

Only policy years that ended by the valuation date (started up to December 2017), so
segments are compared on fully earned years. `KEEPFILTERS` keeps the filter of a chart
axis or slicer instead of replacing it.

```dax
Earned Share = DIVIDE ( [Earned Premium], [Written Premium] )
```

```dax
Frequency = DIVIDE ( [Claim Count], [Exposure Years] )
```

```dax
Severity = DIVIDE ( [Claims Cost], [Claim Count] )
```

## fact_renewal

```dax
Policies Due = SUM ( fact_renewal[policies_due] )
```

```dax
Policies Renewed = SUM ( fact_renewal[policies_renewed] )
```

```dax
Renewal Rate = DIVIDE ( [Policies Renewed], [Policies Due] )
```

## insurer_quarterly

Quarterly market figures come from `insurer_quarterly`, not from summing
`market_monthly`: August and September 2022 are empty by month, but Q3 2022 is exact
in the quarterly table.

```dax
Total Premiums = SUM ( insurer_quarterly[premiums] )
```

```dax
Total Claims Paid = SUM ( insurer_quarterly[claims_paid] )
```

```dax
Premiums (mln AZN) = DIVIDE ( [Total Premiums], 1000 )
```

```dax
Claims Paid (mln AZN) = DIVIDE ( [Total Claims Paid], 1000 )
```

```dax
Payout Ratio = DIVIDE ( [Total Claims Paid], [Total Premiums] )
```

```dax
Premiums PQ = CALCULATE ( [Total Premiums], DATEADD ( 'Date'[Date], -1, QUARTER ) )
```

```dax
QoQ % = DIVIDE ( [Total Premiums] - [Premiums PQ], [Premiums PQ] )
```

```dax
Premiums PY = CALCULATE ( [Total Premiums], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )
```

```dax
YoY % = DIVIDE ( [Total Premiums] - [Premiums PY], [Premiums PY] )
```

```dax
Claims Paid PY = CALCULATE ( [Total Claims Paid], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )
```

```dax
Claims YoY % = DIVIDE ( [Total Claims Paid] - [Claims Paid PY], [Claims Paid PY] )
```

```dax
Market Share =
DIVIDE (
    [Total Premiums],
    CALCULATE (
        [Total Premiums],
        REMOVEFILTERS ( insurer_quarterly[insurer], insurer_quarterly[segment], insurer_quarterly[licence_revoked] )
    )
)
```

```dax
Segment Share =
VAR seg = SELECTEDVALUE ( insurer_quarterly[segment] )
RETURN
    DIVIDE (
        [Total Premiums],
        CALCULATE (
            [Total Premiums],
            REMOVEFILTERS ( insurer_quarterly[insurer], insurer_quarterly[licence_revoked] ),
            insurer_quarterly[segment] = seg
        )
    )
```

The denominator ignores the filter that hides revoked insurers, so the share is
always out of the whole market (or segment).

## class_quarterly

`class_quarterly` holds subtotals and their parts. Always filter `line_code` to the
lines you show; never sum the whole column.

```dax
Class Premiums = SUM ( class_quarterly[premiums] )
```

```dax
Class Claims Paid = SUM ( class_quarterly[claims_paid] )
```

```dax
Class Payout Ratio = DIVIDE ( [Class Claims Paid], [Class Premiums] )
```

## market_monthly

For the monthly trend chart only.

```dax
Monthly Premiums (mln AZN) = DIVIDE ( SUM ( market_monthly[premiums] ), 1000 )
```

```dax
Monthly Claims (mln AZN) = DIVIDE ( SUM ( market_monthly[claims_paid] ), 1000 )
```
