# Product Validation

## Product boundary
Cross-project contract and benchmark harness for the ML/AI security product family.

## Real-world validation ladder
1. Unit tests for each adapter.
2. Multi-repository checkout of actual sibling products at explicit revisions.
3. Execute adapters against those checkouts rather than mocks.
4. Validate normalized result schema and provenance metadata.
5. Publish a combined evidence artifact containing the exact child-repository SHAs.

## Evidence rules
Adapter success proves integration compatibility, not security efficacy. Every combined report must retain the originating repository revision and benchmark scope.
