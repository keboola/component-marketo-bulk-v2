# Keboola Marketo Bulk Extractor V2

Marketo is a platform where users can develops and sells marketing automation software for account-based marketing and other marketing services and products including SEO and content creation.

This component will allow users to extract their leads and lead activities into Keboola to conduct further analysis.

## Marketo REST API
[API documentation](http://developers.marketo.com/rest-api/bulk-extract/)

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

## Development

If required, change local data folder (the `CUSTOM_FOLDER` placeholder) path to your custom path in the docker-compose file:

```yaml
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone this repository, init the workspace and run the component with following command:

```
git clone repo_path my-new-component
cd my-new-component
docker-compose build
docker-compose run --rm dev
```

Run the test suite and lint check using this command:

```
docker-compose run --rm test
```

# Integration

For information about deployment and integration with KBC, please refer to the [deployment section of developers documentation](https://developers.keboola.com/extend/component/deployment/) 