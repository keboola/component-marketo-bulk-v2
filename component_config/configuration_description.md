## Configuration Parameters
1. Munchkin ID
    - Available in `Admin` > `Web Services` menu in the REST API section
2. Client ID
3. Client Secret

## Endpoint Parameters
1. Leads
    - Created At - `Required`
        - `Leads` endpoint is required to have either `Created At` or `Updated At` parameters configured. The componet will fail if none of them is configured
        - `month/year`
            - Mainly use for backfill
            - Required format - MMM YYYY (e.g. Jan 2019)
        - `timespan`
            - Specifying the amount days back you want to extract
    - Updated At - `Optional`
        - `Leads` endpoint is required to have either `Created At` or `Updated At` parameters configured. The componet will fail if none of them is configured
        - `month/year`
            - Mainly use for backfill
            - Required format - MMM YYYY (e.g. Jan 2019)
        - `timespan`
            - Specifying the amount days back you want to extract
    - Desired Fields - `Required`
2. Activities
    - Created At - `Required`
        - `month/year`
            - Mainly use for backfill
            - Required format - MMM YYYY (e.g. Jan 2019)
        - `timespan`
            - Specifying the amount days back you want to extract
    - Desired Activities - `Optional`
        - IDs of activities you want to extract and separate them by comma. Note: The “Delete Lead” activity is not supported.

## Output Tables
For `Leads` endpoint the resulting table contains all possible columns. This is hardcoded and cannot be changed. The PK is `id`, loads are incremental.

For `Activities` endpoint the PK is `MarketoGUID`, the loads are incremental as well.
