# Sources

## Support Matrix

| Source | Support level | API type | Credentials | Cheapest price field | Polling limits | Current implementation |
| --- | --- | --- | --- | --- | --- | --- |
| MLB Schedule | Supported | Public MLB stats API | None | N/A | Lookahead window only | Implemented |
| Ticketmaster | Supported | Official Discovery API | Public API key | `priceRanges[].min` | Rate limited; matches are best-effort | Implemented |
| SeatGeek | Scaffold only | Official Platform API | Client ID required | `stats.lowest_price` is documented upstream | Auth required; not implemented end-to-end here | Scaffold only |
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

- Public API requires authentication.
- Docs expose `stats.lowest_price`, but not an all-in pricing signal.
- Current branch only carries a disabled scaffold for this adapter.
- The repo should treat SeatGeek as a future partial-integration candidate, not current live support.

### Vivid Seats

- Public buyer-facing developer support is not clearly documented.
- Visible documentation is oriented around broker tooling.
- Current branch only carries an unsupported-by-default scaffold.
- Do not describe it as working live support.
