**Deploy finished, 3 E2E tests still failing**

## Results

- Build: OK
- E2E: 3 failing out of 412
  - `auth`: timeout
  - `cart`: fixture

| Check | Owner | Status |
|:---|:---:|---:|
| [Build](https://example.com/build) | `ci` | **OK** |
| [E2E tests](https://example.com/e2e) | `qa` | 3 failing |

1. Fix the auth timeout
2. Rerun the suite

```bash
npm run test:e2e
```

Can we fix it before Friday?
