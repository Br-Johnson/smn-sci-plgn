# RMIS Access Notes

This skill is based on the live RMIS / RMPC API documentation and public RMPC pages checked on April 17, 2026.

## Public facts

- RMPC is maintained by PSMFC and RMIS is the coded-wire-tag reporting system.
- The RMPC API page says the beta GET functionality is available and requires a personalized API key.
- The embedded Swagger UI currently lives at `https://phish.rmis.org/docs/static/index.html`.
- The OpenAPI document is currently available at `https://phish.rmis.org/docs/json`.
- RMIS announcement status is public at `https://www.rmis.org/include/rmis_announce.html`.

## Auth model

The OpenAPI document currently exposes:

- `xapikey` header auth
- `Authorization` header auth
- `POST /bauth` login to retrieve an API key or JWT token

## Current endpoint surface

- `GET /release`
- `GET /recovery`
- `GET /location`
- `GET /catchsample`
- `GET /description`
- `GET /files`
- `POST /files`
- `POST /bauth`

## Query model

The public RMIS API docs repo currently describes:

- comparison operators like `=`, `<>`, `>`, `<`, `>=`, `<=`
- `page`, `perpage`, `sort`, `search`, and `fields`
- wildcard `~` handling for string search
- comma-separated multi-value filters for some enum-like string fields

## Practical recommendation

For the plugin:

- use API mode for authenticated machine queries
- treat the legacy RMIS reporting UI as a secondary surface for future browser-automation work
- do not assume anonymous RMIS data access
