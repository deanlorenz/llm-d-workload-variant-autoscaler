# Chat links

### convention: chat-file-links
description: In the VSCode extension chat, .md file links resolve relative to the open workspace root; image links do not open via any link form -- display images inline with the Read tool instead.
scope: anyone recommending a file or showing an image to the user in chat
trigger: about to link a document or image in a chat response
status: active
origin: feedback_chat_file_links_full_path.md

**Two separate bugs, corrected twice on the same day after being conflated.**

**For a document (.md etc.): the chat UI's file link resolves relative to the open workspace
root** — e.g. a markdown link reading "label" with target planning/foo.md, not an absolute
filesystem path. Confirmed via a VSCode
webview log: an absolute-path link's click fired an `open_file` request but nothing opened; a
relative, workspace-root-relative link to the same kind of file worked immediately. This is
still subject to the plan-authoring relative-links-worktree-boundary rule for any target that
lives in a different worktree than the document itself.

**For an image (.png etc.): no link form opens it, at all.** Even after fixing the path to be
workspace-relative, a link to a `.png` still produces a registered `open_file` request with no
visible effect — this is not a path problem; .md links with the identical relative-path style
work immediately for documents. The chat UI's `open_file` mechanism appears not to do anything
useful for image files specifically (no editor tab, no preview pane triggered from a chat link).

**How to apply:**
- Recommending a **document** to the user in chat: a markdown link, path relative to the open
  workspace root.
- Showing the user an **image**: never link it — use the `Read` tool on the image path and let
  it render inline in the chat response. This is the only mechanism confirmed to work for images.
  Do not spend retries on image link syntax variants; go straight to inline display.
