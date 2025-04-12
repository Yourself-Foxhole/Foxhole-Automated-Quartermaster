# Task Interface Design

## Task Structure

### Core Task Data
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Task Data Structure                            │
├─────────────────────────────────────────────────────────────────────────┤
│ Task ID: UUID                                                            │
│ Status: Available | Claimed | In Progress | Completed | Stale | Released │
│ Priority: 1-10 (Higher is more urgent)                                  │
│ Created: Timestamp                                                       │
│ Last Updated: Timestamp                                                  │
│ Claimed By: Discord User ID (if claimed)                                │
│ Claimed At: Timestamp (if claimed)                                      │
│ Auto-Release: Timestamp (2 hours from claim)                            │
│                                                                         │
│ Item Details:                                                            │
│ ├── Item Name: String                                                   │
│ ├── Item Quantity: Integer                                              │
│ ├── Item Category: String                                               │
│ └── Item Priority: Integer                                              │
│                                                                         │
│ Location Details:                                                        │
│ ├── Source Location: String                                             │
│ ├── Source Building: String                                             │
│ ├── Destination Location: String                                        │
│ └── Destination Building: String                                        │
│                                                                         │
│ Task Details:                                                            │
│ ├── Task Type: Transport | Production | Redistribution                  │
│ ├── Description: String                                                 │
│ ├── Notes: String                                                       │
│ └── Estimated Time: Integer (minutes)                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Discord Interface Components

### Task Board View

#### Discord Embed for Task List
```json
{
  "title": "Logistics Task Board",
  "description": "Available tasks for logistics operations",
  "color": 3447003,
  "fields": [
    {
      "name": "🔴 Critical Tasks",
      "value": "Task #123: Transport 500 7.62mm to Frontline Bunker\nTask #124: Transport 200 HE Grenades to Frontline Base",
      "inline": false
    },
    {
      "name": "🟡 Priority Tasks",
      "value": "Task #125: Transport 1000 Basic Materials to Factory\nTask #126: Transport 500 Diesel to Storage Depot",
      "inline": false
    },
    {
      "name": "💚 Optional Tasks",
      "value": "Task #127: Redistribute 2000 Basic Materials from Storage to Factory",
      "inline": false
    }
  ],
  "footer": {
    "text": "Use /task claim <id> to claim a task"
  }
}
```

### Individual Task View

#### Discord Embed for Task Details
```json
{
  "title": "Task #123: Transport Ammunition",
  "description": "Critical supply needed at frontline",
  "color": 15158332,
  "fields": [
    {
      "name": "Item",
      "value": "7.62mm Ammunition (500)",
      "inline": true
    },
    {
      "name": "Priority",
      "value": "🔴 Critical (10/10)",
      "inline": true
    },
    {
      "name": "Status",
      "value": "Available",
      "inline": true
    },
    {
      "name": "Source",
      "value": "Storage Depot (Seaport)",
      "inline": true
    },
    {
      "name": "Destination",
      "value": "Frontline Bunker (T3)",
      "inline": true
    },
    {
      "name": "Estimated Time",
      "value": "45 minutes",
      "inline": true
    }
  ],
  "footer": {
    "text": "Created 10 minutes ago • Auto-releases in 2 hours if claimed"
  }
}
```

### Task Action Components

#### Discord Button Components
```json
{
  "type": 1,
  "components": [
    {
      "type": 2,
      "style": 3,
      "label": "Claim Task",
      "custom_id": "claim_task_123"
    },
    {
      "type": 2,
      "style": 1,
      "label": "Update Progress",
      "custom_id": "update_task_123"
    },
    {
      "type": 2,
      "style": 4,
      "label": "Complete Task",
      "custom_id": "complete_task_123"
    },
    {
      "type": 2,
      "style": 2,
      "label": "Release Task",
      "custom_id": "release_task_123"
    }
  ]
}
```

### Task Progress Update Modal

#### Discord Modal for Progress Updates
```json
{
  "title": "Update Task Progress",
  "custom_id": "update_progress_123",
  "components": [
    {
      "type": 1,
      "components": [
        {
          "type": 4,
          "custom_id": "progress_percentage",
          "label": "Progress Percentage",
          "style": 1,
          "min_length": 1,
          "max_length": 3,
          "placeholder": "50",
          "required": true
        }
      ]
    },
    {
      "type": 1,
      "components": [
        {
          "type": 4,
          "custom_id": "progress_notes",
          "label": "Progress Notes",
          "style": 2,
          "min_length": 1,
          "max_length": 1000,
          "placeholder": "Currently loading the truck with ammunition...",
          "required": false
        }
      ]
    }
  ]
}
```

## Task Board Commands

### Discord Slash Commands
```
/task
├── list [priority] [location] [item]
├── view <task_id>
├── claim <task_id>
├── update <task_id> <progress> [notes]
├── complete <task_id>
├── release <task_id>
└── filter [priority] [location] [item] [status]
```

## Task Auto-Release Mechanism

### Auto-Release Logic
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Auto-Release Process                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Check Task Status                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    Is Task Claimed?     │           │    Is Task In Progress? │
└─────────────────────────┘           └─────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    Check Claim Time     │           │    Check Last Update    │
└─────────────────────────┘           └─────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    Time Since Claim     │           │    Time Since Update    │
└─────────────────────────┘           └─────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    > 2 Hours?           │           │    > 2 Hours?           │
└─────────────────────────┘           └─────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Release Task                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Notify User                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Task Notification System

### Notification Types
1. **Task Created**
   - Notify logistics channel
   - Include task details and priority

2. **Task Claimed**
   - Notify logistics channel
   - Tag claiming user
   - Include task details

3. **Task Updated**
   - Notify logistics channel
   - Tag claiming user
   - Show progress update

4. **Task Completed**
   - Notify logistics channel
   - Tag claiming user
   - Show completion details

5. **Task Released**
   - Notify logistics channel
   - Tag previous claiming user (if applicable)
   - Show reason for release

6. **Task Auto-Released**
   - Notify logistics channel
   - Tag previous claiming user
   - Indicate auto-release due to inactivity

## Task Board Filtering

### Filter Options
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Task Board Filters                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    Priority Filter      │           │    Location Filter      │
│  ┌─────────────┐        │           │  ┌─────────────┐        │
│  │ Critical    │        │           │  │ Frontline   │        │
│  │ High        │        │           │  │ Backline    │        │
│  │ Medium      │        │           │  │ Logistics   │        │
│  │ Low         │        │           │  │ Production  │        │
│  └─────────────┘        │           │  └─────────────┘        │
└─────────────────────────┘           └─────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    Item Type Filter     │           │    Status Filter        │
│  ┌─────────────┐        │           │  ┌─────────────┐        │
│  │ Ammunition  │        │           │  │ Available   │        │
│  │ Medical     │        │           │  │ Claimed     │        │
│  │ Supplies    │        │           │  │ In Progress │        │
│  │ Resources   │        │           │  │ Completed   │        │
│  └─────────────┘        │           │  └─────────────┘        │
└─────────────────────────┘           └─────────────────────────┘
```

## Task Board Pagination

### Pagination Controls
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Task Board Pagination                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│    Page Navigation      │           │    Items Per Page       │
│  ┌─────────────┐        │           │  ┌─────────────┐        │
│  │ Previous    │        │           │  │ 5 Tasks     │        │
│  │ Next        │        │           │  │ 10 Tasks    │        │
│  │ First       │        │           │  │ 20 Tasks    │        │
│  │ Last        │        │           │  │ 50 Tasks    │        │
│  └─────────────┘        │           │  └─────────────┘        │
└─────────────────────────┘           └─────────────────────────┘
``` 