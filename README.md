# Deadlock Browser Build Maker

Make Deadlock hero builds in a browser, then paste them straight into the game.

Deadlock's build editor can copy a build to the clipboard as a text code and paste one back in. This tool writes those codes for you, so you can put a build together anywhere (including on a phone) and bring it into the game with one paste.

It is a single file, `index.html`, with no server and no install.

## Added Functionality

You can paste a build copied from the game into the tool with **Load a code**. Once it is loaded you can:

- **Add duplicates of items.** Put the same item in the build more than once.
- **Swap the hero.** Change which hero the build applies to, then paste it into that hero's editor.

## Using it

1. Open `index.html` in a browser, or visit the hosted page if you have set one up (see below).
2. Pick a hero, name the build and fill in the categories.
3. Press **Copy build code**.
4. In Deadlock, open a build in the editor (Build Browser, then Create New Build) and press the paste button.

Pasting replaces whatever is in the build you have open. It never changes any other saved build.

## What you can set

- Hero, build name and build description
- Up to three build tags (preset tags or items)
- Categories, each with a name, description and an **Optional** flag
- Items in order, each with an optional note and, for imbue items, the ability to imbue
- Ability point order
- Category sizes, either kept from a loaded build or fitted automatically to the number of items

**Load a code** reads any code copied from the game, so you can edit a public build or move a build to a different hero. Items the chosen hero can't buy are flagged, and the game shows them greyed out.

Builds are saved in your browser's local storage. To move one to another device, copy its code and load it there.

## Hosting it with GitHub Pages

1. In the repository, open **Settings**, then **Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**, pick the `main` branch and the `/ (root)` folder, and save.
3. After a minute the page is live at `https://<your-username>.github.io/<repository-name>/`.

## Keeping it current after a patch

The hero, item and tag lists are baked into `index.html`. When a patch adds or renames items or heroes, refresh them with:

```
python3 tools/update_data.py
```

The script needs only Python 3. It downloads the current game data from the public [SteamDatabase/GameTracking-Deadlock](https://github.com/SteamDatabase/GameTracking-Deadlock) repository and rewrites the data line in `index.html`.

## How the build code works

This was worked out by decoding codes copied from the game and pasting generated ones back in. It is not documented by Valve and may change.

A code is **Base64** text wrapping a **Zstandard** frame wrapping a **Protocol Buffers** message. There is no signature or checksum.

| Field | Type | Meaning |
|---|---|---|
| 1 | varint | Build ID. Must be present, but any number is accepted |
| 2 | varint | Hero ID |
| 3 | varint | Author's Steam account ID (optional) |
| 4 | varint | Last updated, Unix time (optional) |
| 5 | string | Build name |
| 6 | string | Build description |
| 7, 8 | varint | Language and version, both 0 in every sample seen |
| 9 | varint | Origin build ID (optional) |
| 10 | message | Details, see below |
| 11 | repeated varint | Build tags, up to three. Each is a preset tag ID or an item ID |

Details (field 10):

| Field | Type | Meaning |
|---|---|---|
| 1 | repeated message | Categories |
| 2 | message | Ability order: a repeated list (field 1) of point spends |

Category:

| Field | Type | Meaning |
|---|---|---|
| 1 | repeated message | Items |
| 2 | string | Name. The game's default names are tokens such as `#Citadel_HeroBuilds_EarlyGame` |
| 3 | string | Description |
| 4 | float | Width |
| 5 | float | Height (absent until the category has been resized) |
| 6 | varint | Optional flag |

Item:

| Field | Type | Meaning |
|---|---|---|
| 1 | varint | Item ID |
| 2 | string | Note |
| 4 | varint | Unknown. Written as 0 whenever the item has a note or an imbue |
| 5 | varint | Imbue target, an ability ID |

Ability point spend:

| Field | Type | Meaning |
|---|---|---|
| 1 | varint | Ability ID |
| 2 | varint | 2 for the unlock, 1 for an upgrade |
| 3 | varint (signed) | Points spent as a negative number: -1 for the unlock, then -1, -2 and -5 |

Other things worth knowing:

- **IDs are hashes.** Item, ability and tag IDs are the 32-bit MurmurHash2 of the internal name (for example `upgrade_close_range` for Close Quarters) with seed `0x31415926`.
- **The game compresses, this tool does not.** The game writes compressed Zstandard frames. This tool writes uncompressed (raw-block) frames, which are valid Zstandard and which the game accepts. Reading the game's codes does need a real decompressor.
- **The hero is not enforced.** A code for one hero pastes into another hero's editor; items that hero can't buy show greyed out.
- **Category width** is 12 + 81.75 per item in a row. The widest a category can be is 1083, which fits 13 items. Each extra row adds about 112 to the height.

## Credits

- Decompression uses [fzstd](https://github.com/101arrowz/fzstd) by Arjun Barrett, MIT licence, included inside `index.html`.
- Game data comes from [SteamDatabase/GameTracking-Deadlock](https://github.com/SteamDatabase/GameTracking-Deadlock).

This is an unofficial fan project and is not affiliated with or endorsed by Valve. Deadlock is a trademark of Valve Corporation.
