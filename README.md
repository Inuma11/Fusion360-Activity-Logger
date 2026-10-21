# Fusion360 Activity Logger

A Python-based activity logging and design change tracking add-in for Autodesk Fusion 360.

## Overview

Fusion360 Activity Logger is a monitoring tool designed to record modeling activities and track design changes within Autodesk Fusion 360.

It uses Fusion 360 API events to capture user operations and detect modifications to design elements.

The tool supports local logging and real-time Discord notifications, making it useful for reviewing modeling workflows, debugging design operations, and tracking CAD development activities.

## Features

- **Command Logging** — Track command start and termination events.
- **Design Change Detection** — Detect changes to sketch dimensions and user parameters.
- **Feature Tracking** — Monitor creation, modification, and deletion of supported features, including Extrude, Fillet, and Hole.
- **Document Events** — Record document save events.
- **Local Logging** — Store activity records in TXT and JSON formats.
- **Discord Integration** — Send activity and change notifications through Discord Webhooks.
- **Snapshot Comparison** — Compare design states before and after operations to identify changes.

## How It Works

1. Listen for Fusion 360 API events.
2. Capture modeling activities and design snapshots.
3. Compare design states to detect changes.
4. Store activity records locally.
5. Send notifications to Discord.

## Use Cases

- CAD workflow analysis
- Design change tracking
- Modeling process documentation
- Debugging and development
- Educational and research purposes

## Limitations

This tool records events available through the Fusion 360 API. It is not a system-wide keylogger and does not capture arbitrary keyboard input.

Not all internal modeling operations are necessarily exposed through the Fusion 360 API.:D

## Technology

- Python
- Autodesk Fusion 360 API
- Discord Webhooks
- JSON / TXT logging
