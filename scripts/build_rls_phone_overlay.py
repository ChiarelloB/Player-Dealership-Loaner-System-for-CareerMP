from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path


INDEX_PATH = "ui/ui-vue/dist/index.js"
LAYOUT_PATH = "lua/ge/extensions/ui/phone/layout.lua"
TILE_SOURCE_PATH = "ui/entrypoints/main/tiles/marketplace.png"
TILE_OUTPUT_PATH = "ui/entrypoints/main/tiles/player-dealership.png"
DEFAULT_OUTPUT_NAME = "zz_CareerMPPartySharedVehiclesRLSPhoneOverlay.zip"


PLAYER_DEALERSHIP_MANIFEST = (
    "player_dealership_exports=__export({default:()=>player_dealership_default}),"
    "player_dealership_default={id:`player-dealership`,name:`Player Dealer`,"
    "icon:icons.shoppingCart,iconTile:`player-dealership.png`,"
    "route:`/career/phone-player-dealership`,color:`#22b573`,"
    "iconColor:`#ffffff`,category:`Vehicles`,defaultPage:0,defaultPosition:3},"
)

PLAYER_DEALERSHIP_ROUTE = (
    "{path:`phone-player-dealership`,name:`phone-player-dealership`,"
    "component:{__name:`PhonePlayerDealershipBridge`,setup(){onMounted(()=>{try{"
    "window.bngApi&&window.bngApi.engineLua&&window.bngApi.engineLua("
    "`extensions.load(\"careerMPPartySharedVehicles\"); "
    "careerMPPartySharedVehicles.openFromPhone(\"dealership\")`)"
    "}catch(e){console.error(`Failed to open Player Dealership`,e)}"
    "setTimeout(()=>router$1.replace({name:`phone-main`}),150)});"
    "return(_ctx,_cache)=>(openBlock(),createElementBlock(`div`,"
    "{class:`phone-player-dealership-bridge`},`Opening Player Dealership...`))}}},"
)


def patch_index(index_js: str) -> str:
    if "player_dealership_exports" not in index_js:
        manifest_pattern = re.compile(
            r"(marketplace_exports=__export\(\{default:\(\)=>marketplace_default\}\),"
            r"marketplace_default=\{id:`marketplace`,name:`Marketplace`,.*?"
            r"route:`/career/phone-marketplace`,.*?defaultPosition:2\},)"
        )
        index_js, count = manifest_pattern.subn(r"\1" + PLAYER_DEALERSHIP_MANIFEST, index_js, count=1)
        if count != 1:
            raise RuntimeError("Could not find the RLS marketplace phone manifest anchor.")

    module_anchor = '"../apps/manifests/marketplace.js":marketplace_exports,'
    module_insert = module_anchor + '"../apps/manifests/player-dealership.js":player_dealership_exports,'
    if '"../apps/manifests/player-dealership.js":player_dealership_exports' not in index_js:
        if module_anchor not in index_js:
            raise RuntimeError("Could not find the RLS phone manifest module anchor.")
        index_js = index_js.replace(module_anchor, module_insert, 1)

    route_anchor = "{path:`phone-marketplace`,name:`phone-marketplace`,component:PhoneMarketplace_default},"
    if "path:`phone-player-dealership`" not in index_js:
        if route_anchor not in index_js:
            raise RuntimeError("Could not find the RLS phone marketplace route anchor.")
        index_js = index_js.replace(route_anchor, route_anchor + PLAYER_DEALERSHIP_ROUTE, 1)

    return index_js


def patch_layout(layout_lua: str) -> str:
    layout_lua = re.sub(r"local LAYOUT_VERSION = \d+", "local LAYOUT_VERSION = 3", layout_lua, count=1)

    if '"player-dealership"' not in layout_lua:
        layout_lua = layout_lua.replace(
            '        "marketplace",\n',
            '        "marketplace",\n        "player-dealership",\n',
            1,
        )

    migration_block = (
        '  if version < 3 then\n'
        '    normalized.version = LAYOUT_VERSION\n'
        '    changed = true\n'
        '  end\n\n'
        '  if insertMissingApp(normalized, "player-dealership", "marketplace") then\n'
        '    normalized.version = LAYOUT_VERSION\n'
        '    changed = true\n'
        '  end\n\n'
    )
    if 'insertMissingApp(normalized, "player-dealership", "marketplace")' not in layout_lua:
        anchor = (
            '  if version < 2 then\n'
            '    insertMissingApp(normalized, "fre-contracts", "freeroam-events")\n'
            '    normalized.version = LAYOUT_VERSION\n'
            '    changed = true\n'
            '  end\n\n'
        )
        if anchor not in layout_lua:
            raise RuntimeError("Could not find the RLS phone layout migration anchor.")
        layout_lua = layout_lua.replace(anchor, anchor + migration_block, 1)

    return layout_lua


def build_overlay(rls_zip: Path, out_dir: Path, output_name: str) -> Path:
    if not rls_zip.is_file():
        raise FileNotFoundError(f"RLS zip not found: {rls_zip}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / output_name

    with zipfile.ZipFile(rls_zip, "r") as source:
        missing = [
            path
            for path in (INDEX_PATH, LAYOUT_PATH, TILE_SOURCE_PATH)
            if path not in source.namelist()
        ]
        if missing:
            raise RuntimeError("Missing required RLS files: " + ", ".join(missing))

        patched_index = patch_index(source.read(INDEX_PATH).decode("utf-8"))
        patched_layout = patch_layout(source.read(LAYOUT_PATH).decode("utf-8"))
        tile_png = source.read(TILE_SOURCE_PATH)

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        target.writestr(INDEX_PATH, patched_index)
        target.writestr(LAYOUT_PATH, patched_layout)
        target.writestr(TILE_OUTPUT_PATH, tile_png)

    with zipfile.ZipFile(out_zip, "r") as target:
        bad_file = target.testzip()
        if bad_file:
            raise RuntimeError(f"Generated overlay zip failed validation at {bad_file}")

    return out_zip


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a small local overlay that adds Player Dealership to the RLS phone."
    )
    parser.add_argument(
        "--rls-zip",
        "--rls-compatible-zip",
        dest="rls_zip",
        required=True,
        help="Path to the local RLS compatible zip used by your server.",
    )
    parser.add_argument(
        "--out-dir",
        default="dist",
        help="Output directory for the generated overlay zip.",
    )
    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help="Generated overlay zip name.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_zip = build_overlay(Path(args.rls_zip).resolve(), Path(args.out_dir).resolve(), args.output_name)
    print(out_zip)
    print(out_zip.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
