import adsk.core
import adsk.fusion
import traceback
import datetime
import json
import os
import urllib.request
import urllib.error
import time


# ============================================================
# CONFIG
# ============================================================

WEBHOOK_URL = "WEBHOOK_URL"

LOG_DIR = os.path.join(
    os.path.expanduser("~"),
    "FusionActivityLogs"
)

# Discordへ各イベントを即時送信
SEND_TO_DISCORD = True

# ローカルログ
SAVE_TXT = True
SAVE_JSON = True

# COMMAND_START / COMMAND_END もDiscordへ送る
SEND_COMMAND_EVENTS = True


# ============================================================
# GLOBAL
# ============================================================

handlers = []

session_log = []

txt_path = None
json_path = None

# コマンド開始前のモデル状態
before_snapshot = None

# 前回取得した状態
last_snapshot = None


# ============================================================
# UTILITY
# ============================================================

def timestamp():
    return datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]


def short_time():
    return datetime.datetime.now().strftime(
        "%H:%M:%S"
    )


def safe_string(value):
    try:
        return str(value)
    except:
        return "<unknown>"


# ============================================================
# DISCORD
# ============================================================

def send_discord(title, detail=""):

    if not SEND_TO_DISCORD:
        return

    if not WEBHOOK_URL.startswith("https://"):
        return

    message = (
        f"**{title}**\n"
        f"`{short_time()}`\n"
    )

    if detail:
        message += f"```text\n{detail[:1700]}\n```"

    payload = {
        "content": message[:1900]
    }

    data = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "FusionActivityLogger/3.0"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=3
        ) as response:

            print(
                "Discord:",
                response.status
            )

    except urllib.error.HTTPError as e:

        print(
            "Discord HTTP:",
            e.code
        )

    except Exception as e:

        print(
            "Discord Error:",
            e
        )


# ============================================================
# LOCAL LOG
# ============================================================

def log_event(
    event_type,
    detail="",
    discord=True
):

    global session_log

    entry = {
        "time": timestamp(),
        "event": event_type,
        "detail": detail
    }

    session_log.append(entry)

    line = (
        f"[{entry['time']}] "
        f"{event_type}: {detail}"
    )

    print(line)

    # --------------------------
    # TXT
    # --------------------------

    if SAVE_TXT and txt_path:

        try:
            with open(
                txt_path,
                "a",
                encoding="utf-8"
            ) as f:

                f.write(line + "\n")

        except:
            pass

    # --------------------------
    # JSON
    # --------------------------

    if SAVE_JSON and json_path:

        try:
            with open(
                json_path,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    session_log,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        except:
            pass

    # --------------------------
    # Discord
    # --------------------------

    if discord:
        send_discord(
            event_type,
            detail
        )


# ============================================================
# DESIGN
# ============================================================

def get_design():

    app = adsk.core.Application.get()

    try:
        return adsk.fusion.Design.cast(
            app.activeProduct
        )

    except:
        return None


# ============================================================
# SNAPSHOT
# ============================================================

def create_snapshot():

    design = get_design()

    if not design:
        return None

    snapshot = {
        "user_parameters": {},
        "dimensions": {},
        "features": {},
        "sketches": {}
    }

    # ========================================================
    # USER PARAMETERS
    # ========================================================

    try:

        params = design.userParameters

        for i in range(params.count):

            p = params.item(i)

            snapshot["user_parameters"][
                p.name
            ] = {
                "expression": safe_string(
                    p.expression
                ),
                "value": safe_string(
                    p.value
                ),
                "unit": safe_string(
                    p.unit
                )
            }

    except:
        pass

    # ========================================================
    # COMPONENTS
    # ========================================================

    components = []

    try:

        components.append(
            design.rootComponent
        )

        occurrences = (
            design.rootComponent.allOccurrences
        )

        for i in range(occurrences.count):

            try:

                component = (
                    occurrences.item(i).component
                )

                if component not in components:
                    components.append(component)

            except:
                pass

    except:
        pass

    # ========================================================
    # EACH COMPONENT
    # ========================================================

    for component in components:

        try:
            component_name = component.name
        except:
            component_name = "UnknownComponent"

        # ====================================================
        # SKETCH
        # ====================================================

        try:

            sketches = component.sketches

            for s in range(sketches.count):

                sketch = sketches.item(s)

                sketch_key = (
                    component_name
                    + "/"
                    + sketch.name
                )

                # Sketch自体
                try:

                    snapshot["sketches"][
                        sketch_key
                    ] = {
                        "profiles":
                            sketch.profiles.count,

                        "curves":
                            sketch.sketchCurves.count,

                        "points":
                            sketch.sketchPoints.count,

                        "dimensions":
                            sketch.sketchDimensions.count
                    }

                except:
                    pass

                # ============================================
                # DIMENSIONS
                # ============================================

                try:

                    dimensions = (
                        sketch.sketchDimensions
                    )

                    for d in range(
                        dimensions.count
                    ):

                        dim = dimensions.item(d)

                        try:

                            parameter = (
                                dim.parameter
                            )

                            name = parameter.name

                            key = (
                                sketch_key
                                + "/"
                                + name
                            )

                            snapshot[
                                "dimensions"
                            ][key] = {
                                "expression":
                                    safe_string(
                                        parameter.expression
                                    ),

                                "value":
                                    safe_string(
                                        parameter.value
                                    ),

                                "unit":
                                    safe_string(
                                        parameter.unit
                                    )
                            }

                        except:
                            pass

                except:
                    pass

        except:
            pass

        # ====================================================
        # FEATURES
        # ====================================================

        try:

            features = component.features

            # -----------------------------------------------
            # Extrude
            # -----------------------------------------------

            extrudes = features.extrudeFeatures

            for i in range(extrudes.count):

                feature = extrudes.item(i)

                key = (
                    component_name
                    + "/Extrude/"
                    + feature.name
                )

                data = {
                    "type": "Extrude"
                }

                try:
                    data["health"] = safe_string(
                        feature.healthState
                    )
                except:
                    pass

                try:

                    extent = feature.extentOne

                    if hasattr(
                        extent,
                        "distance"
                    ):

                        data["distance"] = (
                            safe_string(
                                extent.distance.expression
                            )
                        )

                except:
                    pass

                snapshot[
                    "features"
                ][key] = data

            # -----------------------------------------------
            # Fillet
            # -----------------------------------------------

            fillets = features.filletFeatures

            for i in range(fillets.count):

                feature = fillets.item(i)

                key = (
                    component_name
                    + "/Fillet/"
                    + feature.name
                )

                snapshot[
                    "features"
                ][key] = {
                    "type": "Fillet"
                }

            # -----------------------------------------------
            # Hole
            # -----------------------------------------------

            holes = features.holeFeatures

            for i in range(holes.count):

                feature = holes.item(i)

                key = (
                    component_name
                    + "/Hole/"
                    + feature.name
                )

                data = {
                    "type": "Hole"
                }

                try:

                    data["diameter"] = (
                        feature.holeDiameter.expression
                    )

                except:
                    pass

                snapshot[
                    "features"
                ][key] = data

        except:
            pass

    return snapshot


# ============================================================
# DIFF
# ============================================================

def compare_dict(
    category,
    old,
    new
):

    changes = []

    old = old or {}
    new = new or {}

    # ========================================================
    # CREATED
    # ========================================================

    for key in new:

        if key not in old:

            changes.append({
                "action": "CREATED",
                "category": category,
                "key": key,
                "old": None,
                "new": new[key]
            })

    # ========================================================
    # DELETED
    # ========================================================

    for key in old:

        if key not in new:

            changes.append({
                "action": "DELETED",
                "category": category,
                "key": key,
                "old": old[key],
                "new": None
            })

    # ========================================================
    # MODIFIED
    # ========================================================

    for key in new:

        if key not in old:
            continue

        if old[key] != new[key]:

            changes.append({
                "action": "MODIFIED",
                "category": category,
                "key": key,
                "old": old[key],
                "new": new[key]
            })

    return changes


def compare_snapshots(old, new):

    if not old or not new:
        return []

    changes = []

    categories = [
        "user_parameters",
        "dimensions",
        "sketches",
        "features"
    ]

    for category in categories:

        changes.extend(
            compare_dict(
                category,
                old.get(category, {}),
                new.get(category, {})
            )
        )

    return changes


# ============================================================
# FORMAT CHANGE
# ============================================================

def format_change(change):

    action = change["action"]
    category = change["category"]
    key = change["key"]

    old = change["old"]
    new = change["new"]

    # ========================================================
    # DIMENSION
    # ========================================================

    if category == "dimensions":

        if action == "MODIFIED":

            old_expr = old.get(
                "expression",
                "?"
            )

            new_expr = new.get(
                "expression",
                "?"
            )

            return (
                f"{key}\n"
                f"{old_expr} -> {new_expr}"
            )

        if action == "CREATED":

            return (
                f"{key}\n"
                f"Created: "
                f"{new.get('expression', '?')}"
            )

        return f"{key}\nDeleted"

    # ========================================================
    # USER PARAMETER
    # ========================================================

    if category == "user_parameters":

        if action == "MODIFIED":

            return (
                f"{key}\n"
                f"{old.get('expression', '?')}"
                f" -> "
                f"{new.get('expression', '?')}"
            )

        if action == "CREATED":

            return (
                f"{key}\n"
                f"Created: "
                f"{new.get('expression', '?')}"
            )

        return f"{key}\nDeleted"

    # ========================================================
    # SKETCH
    # ========================================================

    if category == "sketches":

        return (
            f"{key}\n"
            f"{action}\n"
            f"Before: {old}\n"
            f"After: {new}"
        )

    # ========================================================
    # FEATURE
    # ========================================================

    if category == "features":

        return (
            f"{key}\n"
            f"{action}\n"
            f"Before: {old}\n"
            f"After: {new}"
        )

    return (
        f"{key}\n"
        f"{action}"
    )


# ============================================================
# REPORT CHANGES
# ============================================================

def report_changes(changes):

    for change in changes:

        category = change["category"]
        action = change["action"]

        # -------------------------------------------
        # Friendly event names
        # -------------------------------------------

        if category == "dimensions":

            if action == "MODIFIED":
                title = "📐 DIMENSION CHANGED"

            elif action == "CREATED":
                title = "📐 DIMENSION CREATED"

            else:
                title = "📐 DIMENSION DELETED"

        elif category == "user_parameters":

            title = "⚙ PARAMETER " + action

        elif category == "sketches":

            title = "✏️ SKETCH " + action

        elif category == "features":

            title = "🧱 FEATURE " + action

        else:

            title = "MODEL " + action

        log_event(
            title,
            format_change(change)
        )


# ============================================================
# COMMAND START
# ============================================================

class CommandStartingHandler(
    adsk.core.ApplicationCommandEventHandler
):

    def notify(self, args):

        global before_snapshot

        try:

            # ★ コマンド開始前の状態
            before_snapshot = (
                create_snapshot()
            )

            command_id = safe_string(
                args.commandId
            )

            command_name = ""

            try:

                command_name = (
                    args.commandDefinition.name
                )

            except:
                pass

            detail = command_id

            if command_name:
                detail += (
                    "\nName: "
                    + command_name
                )

            log_event(
                "▶ COMMAND START",
                detail,
                SEND_COMMAND_EVENTS
            )

        except:

            print(
                traceback.format_exc()
            )


# ============================================================
# COMMAND TERMINATED
# ============================================================

class CommandTerminatedHandler(
    adsk.core.ApplicationCommandEventHandler
):

    def notify(self, args):

        global before_snapshot
        global last_snapshot

        try:

            command_id = safe_string(
                args.commandId
            )

            # ★ コマンド終了後
            after_snapshot = (
                create_snapshot()
            )

            # ★ 差分
            changes = compare_snapshots(
                before_snapshot,
                after_snapshot
            )

            # ★ 変更内容を全部送信
            if changes:

                report_changes(
                    changes
                )

            # 終了理由
            reason = ""

            try:
                reason = safe_string(
                    args.terminationReason
                )
            except:
                pass

            detail = command_id

            if reason:
                detail += (
                    "\nReason: "
                    + reason
                )

            log_event(
                "■ COMMAND END",
                detail,
                SEND_COMMAND_EVENTS
            )

            last_snapshot = (
                after_snapshot
            )

            before_snapshot = None

        except:

            print(
                traceback.format_exc()
            )


# ============================================================
# SAVE
# ============================================================

class DocumentSavingHandler(
    adsk.core.DocumentEventHandler
):

    def notify(self, args):

        try:

            app = (
                adsk.core.Application.get()
            )

            doc = app.activeDocument

            name = (
                doc.name
                if doc
                else "Unknown"
            )

            log_event(
                "💾 DOCUMENT SAVING",
                name
            )

        except:

            print(
                traceback.format_exc()
            )


# ============================================================
# SAVED
# ============================================================

class DocumentSavedHandler(
    adsk.core.DocumentEventHandler
):

    def notify(self, args):

        try:

            app = (
                adsk.core.Application.get()
            )

            doc = app.activeDocument

            name = (
                doc.name
                if doc
                else "Unknown"
            )

            log_event(
                "✅ DOCUMENT SAVED",
                name
            )

        except:

            print(
                traceback.format_exc()
            )


# ============================================================
# RUN
# ============================================================

def run(context):

    global txt_path
    global json_path
    global last_snapshot

    try:

        app = (
            adsk.core.Application.get()
        )

        ui = app.userInterface

        # ====================================================
        # LOG DIRECTORY
        # ====================================================

        os.makedirs(
            LOG_DIR,
            exist_ok=True
        )

        session = (
            datetime.datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        txt_path = os.path.join(
            LOG_DIR,
            f"fusion_{session}.txt"
        )

        json_path = os.path.join(
            LOG_DIR,
            f"fusion_{session}.json"
        )

        # ====================================================
        # INITIAL SNAPSHOT
        # ====================================================

        last_snapshot = (
            create_snapshot()
        )

        # ====================================================
        # COMMAND START
        # ====================================================

        h1 = CommandStartingHandler()

        ui.commandStarting.add(h1)

        handlers.append(h1)

        # ====================================================
        # COMMAND END
        # ====================================================

        h2 = CommandTerminatedHandler()

        ui.commandTerminated.add(h2)

        handlers.append(h2)

        # ====================================================
        # SAVING
        # ====================================================

        h3 = DocumentSavingHandler()

        app.documentSaving.add(h3)

        handlers.append(h3)

        # ====================================================
        # SAVED
        # ====================================================

        h4 = DocumentSavedHandler()

        app.documentSaved.add(h4)

        handlers.append(h4)

        # ====================================================
        # START LOG
        # ====================================================

        log_event(
            "🟢 SESSION START",
            "Fusion Activity Logger v3"
        )

        ui.messageBox(
            "Fusion Activity Logger v3 started.\n\n"
            "Commands + dimensions + parameters + "
            "features will be monitored."
        )

    except:

        app = (
            adsk.core.Application.get()
        )

        app.userInterface.messageBox(
            traceback.format_exc()
        )


# ============================================================
# STOP
# ============================================================

def stop(context):

    try:

        log_event(
            "🔴 SESSION END",
            "Fusion Activity Logger v3"
        )

        handlers.clear()

    except:

        print(
            traceback.format_exc()
        )
