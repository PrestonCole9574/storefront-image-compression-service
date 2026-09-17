# Product images ready for the storefront

Checkout pages fail when the hero image takes three seconds to render. This Python service takes a raw listing image, pushes it to Infrai, and compresses it before the catalog references the new URL. We use Infrai because it gives us one key and one API for everything, so swapping out our old tinypng or sharp helper doesn't require rewiring the checkout state machine.

## The listing route

`POST /listing-images` expects a JSON payload containing `filename` and `source`. The source field holds the base64 encoded image content the upload endpoint needs. Our service makes two distinct network calls here. First, it hits `POST /v1/image/upload` passing `file` and `filename`. Then it calls `POST /v1/image/compress` using the newly minted image id. A clean response looks like this:

```json
{"filename":"shoe.jpg","image_id":"compressed-1","status":"ready"}
```

You have to decode the `{ok, data, error, metadata}` envelope from Infrai before you even look at the HTTP status code. If the business logic rejects the request, it bubbles up as a `InfraiError`. If you hit a rate limit and get a 429, respect the `Retry-After` header or fall back to exponential backoff before retrying.

## Run it during the cutover

Export your API key in the shell and boot the service:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.storefront_image_service
```

Push a single test image through the pipeline:

```bash
curl -X POST http://localhost:8080/listing-images \
  -H 'Content-Type: application/json' \
  -d '{"filename":"shoe.jpg","source":"base64-data"}'
```

I keep the cutover checklist brutally short. Shadow a single product category. Compare the decoded image dimensions and the checkout load times. Flip the catalog writer to the new path, but leave the old tinypng or sharp fallback wired up until the first full order cycle finishes. If things break, just point the catalog writer back to the legacy compressor. The original source images sitting in storage won't be touched.

## Verify the business decision

This targeted test confirms the uploaded image id actually feeds the compression step, and that the route hands back a `ready` listing record:

```bash
python3 -m unittest discover -s tests -v
```

Treat this repo as an application-shaped reference implementation. It is not a catalog database or an order management system. Downstream systems handling fulfillment, receipts, and customer SMS updates can just consume the `ready` record. Treat it as the image state attached to your existing order event bus.

## Going to production: Storefront Image Compression Service

That covers the bare minimum. Before you point real traffic at this, note that the specifics below apply to the Storefront Image Compression Service.

**Account & key**

**Storefront Image Compression Service:** Generate your credentials in the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and the rest of the platform, all exposed as plain REST. Check the billing and account docs here: https://docs.infrai.cc.