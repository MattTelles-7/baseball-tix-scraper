# Sources

## Support Matrix

| Source | Support level | API type | Credentials | Cheapest price field | Polling limits | Current implementation |
| --- | --- | --- | --- | --- | --- | --- |
| MLB Schedule | Supported | Public MLB stats API | None | N/A | Lookahead window only | Implemented |
| Ticketmaster | Supported | Official Discovery API | Public API key | `priceRanges[].min` | Rate limited; matches are best-effort | Implemented |
| SeatGeek | Partial | Official Platform API | Client ID required | `stats.lowest_price` | Auth required; public lowest price may still be omitted per event | Implemented, disabled by default |
| Vivid Seats | Scaffold only | Broker-oriented API surface | Token depends on broker tooling | No honest public-buyer field yet | No clean buyer-facing path confirmed | Scaffold only |

## Notes

### MLB Schedule

- The app uses the public MLB stats schedule endpoint for upcoming games.
- That endpoint is the source of truth for home-game filtering and lookahead windows.

### Ticketmaster

- Public Discovery API is appropriate for v1.
- `priceRanges.min` is the best official/public price signal available with ordinary credentials.
- It may not always equal the true current cheapest live listing price.
- Current code uses `priceRanges.min` from the Discovery API response and does not require privileged marketplace access.

### SeatGeek

- Public API requires a `client_id`.
- Docs expose `stats.lowest_price`, performer-role filters, and event URLs.
- Current code implements event matching and `stats.lowest_price` fetching through the official API.
- All-in pricing is not exposed in the public API, so `price_is_all_in` remains unknown.
- This source is still partial support because some events may return no public lowest price.

### Vivid Seats

- Public buyer-facing developer support is not clearly documented.
- Visible documentation is oriented around broker tooling.
- Current branch only carries an unsupported-by-default scaffold.
- Do not describe it as working live support.
