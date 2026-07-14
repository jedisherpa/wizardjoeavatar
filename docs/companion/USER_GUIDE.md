# Wizard Joe Companion User Guide

## Start

1. Open **Wizard Joe Companion** from Applications.
2. Open Prism GT in either order. Wizard Joe discovers Prism automatically.
3. Play music, a podcast, or an audiobook in Prism. The source indicator changes
   to the active media source and Wizard Joe performs with it.
4. Start a Prism persona response. Speech temporarily takes performance
   priority, the mouth animates while speech is audible, and the prior media
   performance resumes when speech ends or pauses.

No terminal, localhost page, port, token, Python environment, or LaunchAgent
operation is part of normal use.

## Controls

- **Play demo** runs a local movement sequence when Prism is not driving media.
- **Repeat** continuously visits the complete installed pose library in shuffled
  rounds. A Prism media session takes priority automatically.
- **Poses** selects an individual installed pose.
- **Pause reactions** keeps playback audible while stopping media-driven avatar
  reactions.
- **Restart engine** restarts only the child owned by this app.
- **Open Prism GT** launches the installed Prism application.
- **Launch at login** uses the macOS login-item facility.

Movement keys work only while the stage is focused. Arrow keys move, Space
triggers the stage action, and Escape stops the current local action. Standard
buttons retain normal keyboard behavior.

## Status

- **Starting**: the packaged engine is launching.
- **Ready**: the engine and frame stream are available.
- **Waiting for Prism**: Wizard Joe is ready but Prism has not sent fresh media.
- **Music / Podcast / Audiobook / Speech**: that source currently drives motion.
- **Reactions paused**: playback continues; media animation is intentionally
  paused.
- **Reconnecting**: the app is recovering a child or connector restart.
- **Needs attention**: open Diagnostics for the safe error code and recovery.

## Recovery

1. Confirm both applications are open.
2. Wait a few seconds for automatic discovery and retry.
3. Use **Restart engine** in Wizard Joe Companion.
4. Quit and reopen Wizard Joe Companion. Prism can remain open.
5. Open **Diagnostics**, use **Copy safe diagnostics**, and attach that text to
   a bug report. It excludes credentials, media content, transcript text, URLs,
   and file paths.

The legacy Wizard Joe service on port 8765 is independent. Companion does not
stop, edit, or reuse it.

## Privacy

The integration stays on literal loopback. Prism sends numeric timing and
performance features, not raw audio, persona text, media bytes, URLs, or local
file paths. Wizard Joe cannot execute Prism actions or bypass governance and
approval boundaries.
