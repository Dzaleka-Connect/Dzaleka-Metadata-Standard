# Dzaleka Services API reference

The DMS Sources workspace reads published metadata from [Dzaleka Services](https://services.dzaleka.com/api-docs/). It does not synchronize, publish, or modify upstream content. Contact, subscription, submission, and other write endpoints are intentionally not connected.

## Supported collections

| Collection | Upstream endpoint | Draft type |
| --- | --- | --- |
| Public art | `/api/artworks` | `artwork` |
| Photos | `/api/photos` | `photo` |
| Events | `/api/events` | `event` |
| Community stories | `/api/community-voices` | `story` |
| Resources | `/api/resources` | `document` |
| News | `/api/news` | `document` |
| Places and sites | `/api/v1/spatial.json` | `site` |

## Local endpoints

- `GET /api/sources` lists supported collections without connecting to the external service.
- `GET /api/sources/{collection}` returns `{ "items": [...], "cached": false }` with normalized metadata.
- `GET /api/sources/{collection}?id={source-id}` returns `{ "draft": {...} }`. The `id` parameter contains a URL-encoded source identifier.

Collection reads use a fixed HTTPS host, an endpoint allowlist, a 10-second timeout, an 8 MB response limit, and a five-minute cache. The client rejects redirects. Rate-limit responses include HTTP 429 and `Retry-After`. The client pauses new upstream reads during that interval and does not retry automatically. HTTP 503 means the client could not reach the source. HTTP 502 means the client could not use the upstream response.

The browser only calls the local DMS server. The server sends GET requests to Dzaleka Services when a collection is loaded or a draft is requested without a cached response. No local record data, personal API key, or write request is sent upstream.

## Draft mapping and review

Drafts receive a new UUID and retain the source collection endpoint and item identifier in a typed `references` relation. The source endpoint plus a fragment identifies the upstream item, but is not a promise of a standalone item HTML page.

The client copies source titles, descriptions or excerpts, creators, tags, and locations when available. Point coordinates preserve latitude and longitude, including zero. The client retains explicit source licenses and spatial attribution. A photo's image URL identifies its digital file. An event or article illustration does not identify the item itself. Approximate and partial dates remain text in `coverage.period` rather than becoming invented exact dates.

These mappings cover selected fields, not the entire upstream payload. Unmapped metadata remains at the linked source. Language remains blank for review, and missing descriptions remain blank. Imported access and consent default to `restricted` and `unknown`. The draft must pass DMS validation before the server saves it. Public availability does not establish consent or permission to reuse.

Repeated imports create independent drafts rather than updates to existing records. The Records workspace provides edits to existing DMS records. There is no automatic merge, background polling, or removal of records when an upstream item changes.
