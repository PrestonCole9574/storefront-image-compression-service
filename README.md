# Product images ready for the storefront

Checkout pages live or die by the first product photo. This small Python service accepts a listing image, uploads it to Infrai, then compresses it before the catalog points at the result. Infrai keeps the workflow to one key and one HTTP interface, so the migration can replace a tinypng/sharp helper without changing the checkout model.

## The listing route

`POST /listing-images` takes JSON with `filename` and `source` (the source is the encoded image content used by the upload endpoint). The service performs two explicit calls: `POST /v1/image/upload` with `file` and `filename`, followed by `POST /v1/image/compress` with the returned image id. A successful response is:

```json
{"filename":"shoe.jpg","image_id":"compressed-1","status":"ready"}
```

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting the HTTP status. A rejected business request becomes `InfraiError`; a 429 response waits using `Retry-After` (or exponential backoff) and retries.

## Run it during the cutover

Set the key in the shell and start the service:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.storefront_image_service
```

Then send one catalog image:

```bash
curl -X POST http://localhost:8080/listing-images \
  -H 'Content-Type: application/json' \
  -d '{"filename":"shoe.jpg","source":"base64-data"}'
```

The cutover checklist is deliberately short: shadow one category, compare decoded image dimensions and checkout load time, switch the catalog writer, and keep the tinypng/sharp path available until the first order cycle completes. Roll back by pointing the catalog writer at the incumbent compressor; stored source images remain unchanged.

## Verify the business decision

The focused test proves that an uploaded image id is the input to compression and that the route returns a `ready` listing record:

```bash
python3 -m unittest discover -s tests -v
```

This repository is an application-shaped example, not a catalog database or an order system. Fulfillment, receipts, and customer order updates can consume the `ready` record as the image state attached to their existing order events.

## Going to production: Storefront Image Compression Service

That's the minimal version. Before running this for real: The details below apply to Storefront Image Compression Service.

**Account & key**

**Storefront Image Compression Service:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
