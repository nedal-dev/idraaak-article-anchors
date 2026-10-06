# Idraaak Article Anchors

A manual, local checker for fragment links and section IDs in static HTML article source, including exported or copied Gutenberg markup. Results use Vim's quickfix list so you can jump to the exact problem attribute.

This is a Vim plugin, not a WordPress plugin. It checks the current buffer without changing it, including unsaved or read-only article buffers. It makes no network requests and sends no article content to a website or service.

## Requirements

- Vim 8.2 or newer with `+job`, `+channel`, `+timers` and UTF-8 encoding.
- Python 3.8 or newer as a local executable. Embedded Vim Python support is not needed.
- Python's standard library only; no pip packages, account, API key or subscription.
- Neovim is not supported by this version.

## Install

Extract the release ZIP into a native Vim package directory:

- Linux/macOS: `~/.vim/pack/idraaak/start/idraaak-article-anchors/`
- Windows: `~/vimfiles/pack/idraaak/start/idraaak-article-anchors/`

The `plugin`, `autoload`, `python` and `doc` directories must remain together. Restart Vim, then run `:helptags ALL` if you want native help. A plugin manager can also install `nedal-dev/idraaak-article-anchors`.

## Use

Open your article's HTML source and run:

```vim
:IdraaakAnchorsCheck
:copen
```

Press Enter on a quickfix result to jump to the attribute. `:cnext` and `:cprevious` move between results. Run the check again after editing. `:IdraaakAnchorsClear` cancels pending checks and clears this plugin's results for the current buffer.

The plugin does not install key bindings, run on save or automatically open a quickfix window. Changing article text invalidates previous results. Each check adds a quickfix list without replacing another tool's current list; clearing results only clears the list owned by this plugin. Vim retains its usual limited quickfix history.

## Python configuration

The plugin tries `python3` then `python` on Unix, and `py -3`, `python3`, then `python` on native Windows. If that does not find a working Python 3.8+, set a command list in your vimrc:

```vim
let g:idraaak_anchors_python = ['py', '-3']
" Or an absolute executable path:
let g:idraaak_anchors_python = ['C:/path/to/python.exe']
```

The command runs directly as an argument list, never through a shell. The bundled worker runs with `-I -B`, reads a buffer snapshot through stdin and returns a JSON report through stdout. It does not create article copies on disk. Checks time out after 20 seconds; files above 2 MiB of UTF-8 text are rejected, and results show at most 500 issues.

## What it checks

- Fragment-only `href="#section"` on `a` and `area` elements.
- Missing targets, duplicate nonempty `id` values, and links to ambiguous duplicate IDs.
- Exact Arabic/Unicode IDs, UTF-8 percent encoding and HTML character entities.
- Literal ID or legacy `<a name>` matching first, then one percent-decoding pass; IDs are case-sensitive and are not normalized.
- UTF-8 byte columns for accurate Vim navigation after Arabic text or emoji.

HTML comments and raw-text elements such as `script`, `style`, `textarea` and `title` are ignored. Inert `template` contents are ignored, while the template element's own ID can be a target. Empty fragments, document-top fallback and text-only `#:~:text` links are skipped. A nonempty `base href` produces a warning and skips destination checks because the actual document URL is unknown; duplicate IDs are still checked.

Try `examples/article.html`: it contains valid Arabic and encoded links plus one missing target and a duplicate-target problem.

## Limits

This is a static source check, not a browser or an HTML5 tree builder. Malformed HTML may be interpreted differently by a browser. It cannot see IDs or click handlers created by JavaScript, validate external links, check `other-page.html#section`, verify live WordPress rendering, or audit Gutenberg block-comment pairing. A Gutenberg JSON `anchor` value alone is not a rendered section ID. It never fixes or rewrites article content.

## Tests

```text
python -m unittest discover -s tests -v
```

The native Vim integration test uses a clean Vim profile and a configured Python path:

```sh
IDRAAAK_TEST_PYTHON=/path/to/python3 vim -Nu NONE -i NONE -n -es -S tests/test_vim.vim
```

On PowerShell, set `$env:IDRAAAK_TEST_PYTHON` to your executable path, then run the Vim command. It writes `tests/vim-results.json`, reports real quickfix navigation, Arabic byte columns, read-only buffers, preserved unrelated lists, cancelled jobs and stale snapshots. The parser is shared with the author's [Sublime Text checker](https://github.com/nedal-dev/idraaak-article-anchor-checker), under the same MIT license.

## License and developer

MIT. Copyright 2026 Nedal Shabaan.

Developed for article editing workflows at [Idraaak](https://idraaak.com/).
