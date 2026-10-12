# DocPull Registry

This registry holds shared [DocPull](https://github.com/raintree-technology/docpull)
pack recipes. A recipe lists a pack's public sources, pinned page URLs, and the
content hash of each page its publisher synced. Recipes contain no page content.

## Use a pack

```bash
docpull add python-asyncio-docs@2026-10
```

DocPull reads `index.json`, downloads the recipe, and checks its sha256. It then
adds the sources to your project and fetches every page on your machine. Finally,
it reports which pages still match the publisher's hashes. Live pages change, so
some drift is expected and is reported rather than treated as an error. Use
`name@latest` for the newest version.

## Publish a pack

1. Sync a DocPull project whose sources pin their page URLs in
   `discovered_urls`.
2. Export the recipe:

   ```bash
   docpull registry export --name my-pack --version 2026-10 \
     --description "What the pack covers" --out packs/my-pack/2026-10.json
   ```

3. Update the index and check every recipe:

   ```bash
   python tools/check.py --write
   ```

4. Open a pull request. A maintainer reviews every recipe before merging.

## Rules

- Pack names are lowercase letters, digits, and hyphens. Versions use
  `[A-Za-z0-9._-]`, up to 32 characters.
- Sources must use public HTTPS URLs and a crawl type. Sources that use `auth`
  cannot be exported.
- Only list sources whose terms allow automated access. DocPull respects
  robots.txt when it fetches pages.
- Published versions are immutable. Publish changes as a new version.

## Trust

`index.json` records each recipe's sha256, and DocPull refuses any recipe that
doesn't match. GitHub pull request review is the moderation step. Signed
indexes may come later.
