# Unreal MCP (native) and Hayba

Unreal MCP is Epic's built-in editor MCP server, plugin `ModelContextProtocol`. It shipped Experimental in 5.8, and 5.9's documentation describes the same feature. It runs inside the editor process and listens on `http://127.0.0.1:8000/mcp` (Streamable HTTP or SSE; no stdio). Its tools come from "toolsets" registered with the Toolset Registry: Actors, Blueprints and Widget Blueprints, Materials, MetaSounds, PCG, Niagara, Sequencer, Slate widget inspection, Console, Input, Perf, NavMesh, Scene Capture, GAS and automation tests. Tool search exposes four meta-tools: `list_toolsets`, `describe_toolsets`, `describe_tools` and `call_tool`. You can add tools in C++ (`UToolsetDefinition` with `AICallable` functions), in Python (`unreal.ToolsetDefinition`), or in Blueprint (`IToolsetProvider`). Each tool declares an access mode: Read, Write or Execute (the default).

## Overlap

Both servers drive the same editor surface: spawning and editing actors, Blueprint graphs, materials, PCG, Niagara, Sequencer, widget trees, console commands and input. For a single agent working in its own editor, the native server covers most of the day-to-day authoring, and it is Epic-maintained. Hayba would otherwise have to keep pace with each engine release.

## What Hayba has and the native server does not (today)

- **Concurrent agents on one editor.** The native server runs tool calls one at a time on the game thread and asks clients not to overlap calls. It has no authentication, owners or locks. Hayba has per-owner leases (scoped, world or global access classes), refusal of conflicting writes (for example PIE under another owner's exclusive lease), and per-owner holds (`editor_set_render_while_hidden`). That is the reason Hayba exists for FoA's many lanes.
- **Crash and hang policy.** Hayba has the python_run lexical policy (HCR codes: no try/with, dynamic builtins, blocking calls, level loads or unaudited console), a cooperative deadline, SEH-guarded `python_exec_file`, and refusal of known crash paths (the PIE compile-error modal, Blueprint member-name clashes, black captures, unknown parameters). In the native server a Python or Execute tool can do anything it is given.
- **Verified writes.** Hayba replies carry read-backs and proof fields: `verified`, `dirty`, `skipped_not_dirty`, compile reports and hierarchy. Native tools return whatever the toolset returns.
- **FoA-specific tooling.** Lux3D and Manycore asset tools, the PIE driving harness (explicit modifiers, PIE-viewport targeting, widget-tree clicks, screenshots), audio capture, `ue_remote` and editor_lock, and the scratch-host gate workflow.

## What the native server has that Hayba should use, not duplicate

- **Toolsets Epic keeps current** with engine API changes (GAS, MetaSound, NavMesh, Perf/Insights, automation tests). Hayba's own versions of these are the code most at risk on each engine bump.
- **An extension model.** An FoA C++/Python function marked `AICallable` becomes a tool with no server code.
- **Cooked-build tools** (`AIRuntimeCallable`) for runtime debugging, which Hayba does not target.

## Recommendation for FoA on 5.9

Keep Hayba as the server lane agents connect to. It is the one that makes concurrent agents safe, and every crash it now refuses was a real one in FoA. Leave Unreal MCP enabled but bound to localhost only, for read-only and single-user work: the user's own assistant session, Perf, automation tests and toolset discovery. Keep it off the shared lane editor's agent configs, because its calls bypass Hayba's leases and policy. A native write from one agent can collide with a Hayba-leased lane, and Hayba cannot see it.

Longer term, Hayba could call native toolsets through `call_tool` behind its own leases instead of re-implementing them. Each native tool's access mode (Read, Write or Execute) maps onto Hayba's access classes (read, scoped write, global). That would shrink what Hayba maintains to the concurrency and safety layer plus FoA's own tools.

Unverified until 5.9 is installed: whether 5.9 changes the toolset API, port or permissions. The 5.9 page describes the 5.8 behaviour, with no 5.9-specific notes.
