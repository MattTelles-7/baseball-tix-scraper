# Sources

## Support Matrix

| Source | Support level | API type | Credentials | Cheapest price field | Status |
| --- | --- | --- | --- | --- | --- |
| Ticketmaster | Supported | Official Discovery API | Public API key | `priceRanges[].min` | Planned primary source |
| SeatGeek | Partial | Official Platform API | Client ID required | `stats.lowest_price` | Planned disabled-by-default adapter |
| Vivid Seats | Unsupported by default | Broker-oriented API surface | Token depends on broker tooling | Not suitable for honest public-buyer support yet | Planned scaffold only |

## Notes

### Ticketmaster

- Public Discovery API is appropriate for v1.
- `priceRanges.min` is the best official/public price signal available with ordinary credentials.
- It may not always equal the true current cheapest live listing price.

### SeatGeek

- Public API requires authentication.
- Docs expose `stats.lowest_price`, but not an all-in pricing signal.
- Support should remain clearly labeled as partial until proven reliable in practice.

### Vivid Seats

- Public buyer-facing developer support is not clearly documented.
- Visible documentation is oriented around broker tooling.
- The adapter should stay unsupported by default unless a clean official path is available.
