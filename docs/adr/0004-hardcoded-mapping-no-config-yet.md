# 4. Hard-code the Fn+arrow mapping in v1; defer config.toml

Date: 2026-05-07

## Status

Accepted (revisitable).

## Context

The original plan (`/.claude/plans/im-on-a-ga401l-polymorphic-rain.md`)
proposed a `config.toml` next to the executable so the Fn-code → VK
mapping could be tweaked without recompiling.

In practice, the v1 mapping is fixed by user intent:

```
0xB2 → VK_HOME
0xB3 → VK_END
0xC4 → VK_PRIOR
0xC5 → VK_NEXT
```

There is no second mapping anyone has asked for. Adding TOML parsing,
file-watching, and error reporting at this stage is YAGNI.

## Decision

Hard-code the mapping in `src/main.rs::map_action`. Skip the config-file
machinery for v1.

## Consequences

- Less code, less surface area, no parser to test.
- Changing the mapping requires a recompile — but the toolchain is one
  `cargo build --release` away and this only matters if the user wants
  different navigation keys.
- If a future need arises (e.g. user wants Fn+Up to be Insert instead of
  PageUp), revisit and add `config.toml`. The `map_action` function is
  the single place that needs replacing — call sites already abstract
  the lookup.
