# Architecture Overview

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Real-Debrid TUI Application                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         rdtui/app.py                             │
│                      Main Application (RDTUI)                    │
│  - Orchestrates all components                                  │
│  - Handles UI events and user actions                           │
│  - Manages application state                                    │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   rdtui/ui/  │ │  rdtui/api/  │ │rdtui/models/ │ │ rdtui/utils/ │
│              │ │              │ │              │ │              │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │ tables.py│ │ │ │real_     │ │ │ │torrent.py│ │ │ │download  │ │
│ │          │ │ │ │debrid.py │ │ │ │          │ │ │ │.py       │ │
│ │Torrents  │ │ │ │          │ │ │ │TorrentRow│ │ │ │          │ │
│ │Table     │ │ │ │RDClient  │ │ │ │          │ │ │ │run_      │ │
│ │          │ │ │ │          │ │ │ │from_info │ │ │ │downloader│ │
│ │Queue     │ │ │ │user()    │ │ │ │pretty_*  │ │ │ │          │ │
│ │Table     │ │ │ │torrents()│ │ │ │          │ │ │ │          │ │
│ └──────────┘ │ │ │add_*     │ │ │ └──────────┘ │ │ └──────────┘ │
│              │ │ │delete_*  │ │ │              │ │              │
│ ┌──────────┐ │ │ │unrestrict│ │ │              │ │ ┌──────────┐ │
│ │modals.py │ │ │ └──────────┘ │ │              │ │ │media.py  │ │
│ │          │ │ │              │ │              │ │ │          │ │
│ │Help      │ │ │ ┌──────────┐ │ │              │ │ │is_video  │ │
│ │Modal     │ │ │ │aria2.py  │ │ │              │ │ │run_mpv   │ │
│ │          │ │ │ │          │ │ │              │ │ │          │ │
│ │Input     │ │ │ │Aria2RPC  │ │ │              │ │ └──────────┘ │
│ │Modal     │ │ │ │          │ │ │              │ │              │
│ │          │ │ │ │add_uri   │ │ │              │ │ ┌──────────┐ │
│ │Settings  │ │ │ │tell_*    │ │ │              │ │ │formatters│ │
│ │Modal     │ │ │ │pause     │ │ │              │ │ │.py       │ │
│ └──────────┘ │ │ │remove    │ │ │              │ │ │          │ │
│              │ │ └──────────┘ │ │              │ │ │format_   │ │
└──────────────┘ └──────────────┘ └──────────────┘ │ │size      │ │
                                                    │ │progress  │ │
                                                    │ │speed     │ │
                                                    │ │eta       │ │
                                                    │ └──────────┘ │
                                                    └──────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  rdtui/config/   │
              │                  │
              │  ┌────────────┐  │
              │  │manager.py  │  │
              │  │            │  │
              │  │load_config │  │
              │  │save_config │  │
              │  │get_config_ │  │
              │  │dir         │  │
              │  └────────────┘  │
              └──────────────────┘
```

## Data Flow

### 1. User Interaction Flow
```
User Input → UI Components → App Event Handlers → API Clients → External Services
                                                 ↓
                                            Update Models
                                                 ↓
                                            Render UI
```

### 2. Torrent List Refresh Flow
```
User presses 'r'
    ↓
app.action_refresh()
    ↓
RDClient.torrents()
    ↓
[TorrentRow.from_info(t) for t in response]
    ↓
app._render_table()
    ↓
TorrentsTable displays updated data
```

### 3. Download Flow
```
User presses 'd'
    ↓
app.action_download()
    ↓
app._collect_links(tid)
    ↓
RDClient.unrestrict_link(url)
    ↓
If aria2 enabled:
    Aria2RPC.add_uri()
    ↓
    app.refresh_queue()
Else:
    run_downloader()
```

### 4. Settings Flow
```
User presses 'g'
    ↓
app.action_settings()
    ↓
SettingsModal displayed
    ↓
User saves settings
    ↓
SettingsModal.Saved message
    ↓
app.on_settings_modal_saved()
    ↓
save_config()
    ↓
app.setup_client()
```

## Module Dependencies

```
app.py
├── ui/tables.py
├── ui/modals.py
├── api/real_debrid.py
├── api/aria2.py
├── models/torrent.py
├── utils/download.py
├── utils/media.py
├── utils/formatters.py
└── config/manager.py

ui/modals.py
└── (no internal dependencies)

ui/tables.py
└── (no internal dependencies)

api/real_debrid.py
└── httpx (external)

api/aria2.py
└── httpx (external)

models/torrent.py
├── humanize (external)
├── dateutil (external)
└── rich (external)

utils/download.py
└── asyncio (stdlib)

utils/media.py
└── asyncio (stdlib)

utils/formatters.py
└── humanize (external)

config/manager.py
├── json (stdlib)
├── os (stdlib)
├── platform (stdlib)
└── pathlib (stdlib)
```

## Key Design Patterns

### 1. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- UI components don't directly call API methods
- Business logic is separated from presentation

### 2. **Dependency Injection**
- App class receives configuration
- API clients are initialized with tokens/URLs
- Components are loosely coupled

### 3. **Event-Driven Architecture**
- Textual's message passing for UI events
- Modal dialogs post messages on completion
- App responds to events asynchronously

### 4. **Factory Pattern**
- `TorrentRow.from_info()` creates instances from API data
- Centralized object creation

### 5. **Strategy Pattern**
- Different downloaders (aria2c, curl, wget)
- Configurable at runtime

## Benefits of This Architecture

1. **Modularity**: Each component can be developed/tested independently
2. **Scalability**: Easy to add new features without affecting existing code
3. **Maintainability**: Clear structure makes code easy to understand
4. **Testability**: Components can be mocked and tested in isolation
5. **Reusability**: API clients and utilities can be used in other projects
6. **Flexibility**: Easy to swap implementations (e.g., different API clients)

## Future Enhancements

Potential architectural improvements:

1. **Service Layer**: Extract business logic from app.py into service classes
2. **Repository Pattern**: Abstract data access behind repositories
3. **State Management**: Centralized state management for complex UI state
4. **Plugin System**: Allow extensions through plugins
5. **Async Queue**: Better handling of background tasks
6. **Caching Layer**: Cache API responses to reduce network calls

