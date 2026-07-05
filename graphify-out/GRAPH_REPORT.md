# Graph Report - C:/dev/maintain/lbms  (2026-07-05)

## Corpus Check
- Corpus is ~5,043 words - fits in a single context window. You may not need a graph.

## Summary
- 92 nodes · 187 edges · 7 communities (5 shown, 2 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Scrobbler Core Logic|Scrobbler Core Logic]]
- [[_COMMUNITY_Offline Listen Cache|Offline Listen Cache]]
- [[_COMMUNITY_Documentation Concepts|Documentation Concepts]]
- [[_COMMUNITY_Installer Script|Installer Script]]
- [[_COMMUNITY_Dependencies and Changelog|Dependencies and Changelog]]
- [[_COMMUNITY_Startup and Configuration|Startup and Configuration]]
- [[_COMMUNITY_Logger Module|Logger Module]]

## God Nodes (most connected - your core abstractions)
1. `ListenBrainzScrobbler` - 31 edges
2. `Logger` - 13 edges
3. `ListenCache` - 12 edges
4. `install.sh script` - 8 edges
5. `log_info()` - 8 edges
6. `log_ok()` - 6 edges
7. `setup_service()` - 6 edges
8. `main()` - 6 edges
9. `execute_cmd()` - 5 edges
10. `check_system()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `setup_service()` --implements--> `lbms.service Systemd Unit`  [INFERRED]
  install.sh → README.md
- `ListenCache` --implements--> `Offline Cache`  [INFERRED]
  src/main.py → README.md
- `liblistenbrainz 0.7.0` --conceptually_related_to--> `ListenBrainzScrobbler`  [INFERRED]
  requirements.txt → src/main.py
- `python-dotenv 1.2.2` --conceptually_related_to--> `Token Storage (.env)`  [INFERRED]
  requirements.txt → README.md
- `Renderer Scrobbling (1.3.0)` --conceptually_related_to--> `AirPlay / Spotify Connect Renderers`  [INFERRED]
  CHANGELOG.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Scrobble Timing Flow** — readme_canonical_scrobble_rule, readme_min_play_time, src_main_listenbrainzscrobbler_canonical_delay, src_main_listenbrainzscrobbler_start_listen_timer, src_main_listenbrainzscrobbler_delayed_submit [INFERRED 0.85]
- **Offline Cache Recovery** — readme_offline_cache, src_main_listencache, src_main_listencache_process_pending_listens, src_main_listenbrainzscrobbler_check_connection_and_process_cache, changelog_atomic_cache_write [INFERRED 0.85]
- **Token Security Chain** — readme_env_token_storage, requirements_python_dotenv, src_logger_logger_add_redaction, install_setup_configuration [INFERRED 0.75]

## Communities (7 total, 2 thin omitted)

### Community 1 - "Offline Listen Cache"
Cohesion: 0.19
Nodes (4): Atomic Cache Write Durability, ListenCache, Uses single submission for small queues, batch for larger ones., Atomic write (temp file + replace). Caller must hold self._lock.

### Community 2 - "Documentation Concepts"
Cohesion: 0.22
Nodes (12): Renderer Scrobbling (1.3.0), Canonical Scrobble Rule, currentsong.txt, --dry-run Mode, lbms.service Systemd Unit, ListenBrainz, Listening Now Status, min_play_time Floor (+4 more)

### Community 3 - "Installer Script"
Cohesion: 0.52
Nodes (11): check_root(), check_system(), execute_cmd(), log_error(), log_info(), log_ok(), setup_configuration(), setup_permissions() (+3 more)

### Community 4 - "Dependencies and Changelog"
Cohesion: 0.22
Nodes (8): Pause/Resume Duplicate Fix (1.2.2), Song Identity by Title/Artist/Album, FileSystemEventHandler, Token Storage (.env), Repeat-1 Single Listen Limitation, liblistenbrainz 0.7.0, python-dotenv 1.2.2, watchdog 6.0.0

### Community 5 - "Startup and Configuration"
Cohesion: 0.22
Nodes (3): main(), _parse_args(), print_banner()

## Knowledge Gaps
- **1 isolated node(s):** `--dry-run Mode`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ListenBrainzScrobbler` connect `Scrobbler Core Logic` to `Offline Listen Cache`, `Dependencies and Changelog`, `Startup and Configuration`, `Logger Module`?**
  _High betweenness centrality (0.441) - this node is a cross-community bridge._
- **Why does `Logger` connect `Logger Module` to `Scrobbler Core Logic`, `Offline Listen Cache`, `Dependencies and Changelog`, `Startup and Configuration`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Why does `ListenCache` connect `Offline Listen Cache` to `Documentation Concepts`, `Startup and Configuration`, `Logger Module`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ListenBrainzScrobbler` (e.g. with `liblistenbrainz 0.7.0` and `Logger`) actually correct?**
  _`ListenBrainzScrobbler` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Logger` (e.g. with `ListenBrainzScrobbler` and `.__init__()`) actually correct?**
  _`Logger` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ListenCache` (e.g. with `Offline Cache` and `Logger`) actually correct?**
  _`ListenCache` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Atomic write (temp file + replace). Caller must hold self._lock.`, `Uses single submission for small queues, batch for larger ones.`, `Scrobble delay: min(duration * 0.5, 240s), floor at min_play_time.         With` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._