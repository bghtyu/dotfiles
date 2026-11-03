# Pinned third-party rule sources

These are byte-for-byte, source-controlled upstream snapshots, not a live subscription.
`manifest.json` records immutable Git commit revisions, source URLs, SHA-256 hashes,
licenses, file formats, and routing-category roots. Paths in the manifest are relative
to `clash/vendor/`. Every recursive `include:` dependency of the listed domain roots
is included. No network access is needed when building from these snapshots.

## Sources and redistribution

- **v2fly/domain-list-community**, commit
  `f9486122931b6fc7d8733731ea58caef4ad33936`, MIT license.
  Copyright (c) 2018-2019 V2Ray. See `domain-list-community/LICENSE`.
- **gaoyifan/china-operator-ip**, `ip-lists` commit
  `ffabdf398bf6c9b3ffa2d66e536155b87188d0d9`, MIT license.
  Copyright (c) 2017 Yifan Gao. See `china-operator-ip/LICENSE`.
  `china.txt` and `china6.txt` contain IPv4 and IPv6 CIDRs respectively.

Keep the corresponding copyright and MIT permission notices with redistributed
copies or substantial portions, including converted lists. The repository's own
license does not replace these notices. Sources are provided without warranty.
No blackmatrix7 snapshots are bundled: that project's root license is GPL-2.0,
not MIT. No source without an explicit redistribution license was selected.

## Parsing contract

`roots` maps logical category names to one or more source paths. `files` hashes
all source data, including `_dependency` entries. `licenses` hashes the license
texts. The original data retains its comments and attributes unchanged.

For `v2fly-domain-list`:

- Strip `#` comments and blank lines.
- A bare domain (or `domain:`) means a suffix match; `full:` means an exact match.
- `keyword:` means a substring match. None occur in this pinned closure.
- Expand `include:name` recursively from `domain-list-community/data/name`.
- Attributes follow the match as whitespace-delimited `@name` tokens.
- An include filter `@cn` selects entries having attribute `cn`.
- An include filter `@-!cn` selects entries **without** the attribute `!cn`.
  Here `!cn` is an attribute name; do not treat its `!` as filter negation.
  Multiple include filters are combined with logical AND.
- Attribute filters apply to resolved domain entries, including nested includes.
- `regexp:` entries require explicit engine-compatibility handling. The common
  portable output may omit them, but must report the omissions rather than
  silently claim full upstream coverage. This snapshot contains 15 raw regexp
  entries, some reachable through more than one category.
- No affiliation (`&name`) tokens occur in this selected source closure. This
  snapshot is a chosen raw-source closure, not the full upstream compiled geosite.

For `cidr-lines`, nonempty lines are ordinary CIDRs. Route IPv4 as `IP-CIDR` and
IPv6 as `IP-CIDR6`, normally with `no-resolve`.

## Scope decisions

- `China` uses `cn`, including its complete recursive source closure, and is
  supplemented by `ChinaIP`. These are routing hints, not a jurisdiction oracle.
- `Game` uses `category-games-!cn` for foreign gaming services. Chinese game
  services can fall through to `China`; broad game rules may include domestic CDN
  attributes and should not be described as geographic guarantees.
- `GlobalMedia` intentionally selects Netflix, Disney, HBO, Prime Video and
  Twitch plus their dependencies. It is not a comprehensive streaming catalog.
  Upstream `category-media` principally describes news, not streaming video.
- `AI` includes the foreign AI category plus explicit OpenAI, Anthropic, Gemini
  and GitHub Copilot roots. Specific AI rules should precede Google/GitHub rules.
- `LAN` is the upstream private-domain list, not a private IP range list.
  The application must provide its own RFC-defined private/local IP rules.
- There is no dedicated upstream WeChat list. The unchanged `tencent` source is
  retained as provenance only, not a routing root: using it wholesale would
  wrongly label all Tencent traffic as WeChat. Supply narrow, reviewed WeChat
  overrides separately, and do not classify all `qq.com` as WeChat.
- No broad advertising list is bundled. Upstream `@ads` attributes remain source
  metadata and must not automatically imply rejection.

## Updating safely

Choose new immutable commits, refresh the exact files and recursive closure,
verify the licenses at those same commits, recalculate hashes, and review the
resulting routing changes. Do not simply replace pinned URLs with branch URLs.
