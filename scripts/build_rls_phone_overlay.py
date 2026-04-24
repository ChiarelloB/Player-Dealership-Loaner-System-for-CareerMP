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

PLAYER_DEALERSHIP_COMPONENT = r"""
{__name:`PhonePlayerDealership`,setup(){
let root=null,state={ownedVehicles:[],marketplace:{myListings:[],publicListings:[],listingCount:0},players:[]},activeTab=`market`,notice=``,searchQuery=``,refreshTimer=null;
const styleId=`careermp-player-dealer-phone-style`;
function engine(cmd,callback){try{if(window.bngApi&&window.bngApi.engineLua){window.bngApi.engineLua(cmd,callback)}}catch(error){console.error(`Player Dealer Lua call failed`,error)}}
function luaString(value){return String(value==null?``:value).replace(/\\/g,`\\\\`).replace(/"/g,`\\"`)}
function html(value){return String(value==null?``:value).replace(/[&<>"']/g,char=>({"&":`&amp;`,"<":`&lt;`,">":`&gt;`,'"':`&quot;`,"'":`&#39;`})[char])}
function money(value){let amount=Number(value)||0;return `$`+amount.toLocaleString(void 0,{minimumFractionDigits:0,maximumFractionDigits:0})}
function array(value){return Array.isArray(value)?value:[]}
function safeState(data){if(typeof data===`string`){try{data=JSON.parse(data)}catch{return}}if(!data||typeof data!==`object`)return;state=data;state.ownedVehicles=array(state.ownedVehicles);state.players=array(state.players);state.marketplace=state.marketplace||{};state.marketplace.myListings=array(state.marketplace.myListings);state.marketplace.publicListings=array(state.marketplace.publicListings);render()}
function ensureStyle(){if(document.getElementById(styleId))return;let style=document.createElement(`style`);style.id=styleId;style.textContent=`
.phone-player-dealership-native{height:100%;min-height:0}
.phone-player-dealer{height:100%;min-height:0;box-sizing:border-box;padding:14px 14px 22px;overflow-y:auto;color:#f6fff9;background:radial-gradient(circle at 20% -8%,rgba(34,181,115,.28),transparent 34%),linear-gradient(180deg,#080a12 0%,#0c111c 44%,#06080e 100%);font-family:Overpass,Arial,sans-serif}
.phone-player-dealer *{box-sizing:border-box}
.phone-player-dealer button{border:0;border-radius:14px;padding:10px 12px;background:#1edc88;color:#03110c;font-weight:1000;box-shadow:0 8px 18px rgba(0,0,0,.22)}
.phone-player-dealer__hero{border:1px solid rgba(255,255,255,.11);border-radius:24px;padding:16px;background:linear-gradient(135deg,rgba(30,220,136,.22),rgba(71,85,105,.18));box-shadow:inset 0 1px 0 rgba(255,255,255,.1);margin-bottom:12px}
.phone-player-dealer__hero-kicker{font-size:10px;font-weight:1000;text-transform:uppercase;letter-spacing:.12em;color:#7dffc4;margin-bottom:7px}
.phone-player-dealer__hero strong{display:block;font-size:21px;letter-spacing:-.05em;line-height:1.02;margin-bottom:7px;color:#fff}
.phone-player-dealer__hero span{display:block;color:#c6d2ce;font-size:12px;line-height:1.35}
.phone-player-dealer__search{position:sticky;top:-14px;z-index:5;margin:0 -2px 10px;padding-top:8px;background:linear-gradient(180deg,#080a12 0%,rgba(8,10,18,.92) 72%,rgba(8,10,18,0) 100%)}
.phone-player-dealer__search input{width:100%;border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:12px 14px;background:rgba(255,255,255,.08);color:#fff;font-size:13px;font-weight:900;outline:none}
.phone-player-dealer__search input::placeholder{color:#8d9a96}
.phone-player-dealer__tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:10px 0 12px}
.phone-player-dealer__tab{background:rgba(255,255,255,.07)!important;color:#dff8ef!important;border:1px solid rgba(255,255,255,.09)!important;padding:9px 5px!important;font-size:10px!important;box-shadow:none!important}
.phone-player-dealer__tab.is-active{background:#1edc88!important;color:#03110c!important}
.phone-player-dealer__notice{margin:8px 0 10px;padding:9px 10px;border-radius:14px;background:rgba(30,220,136,.12);border:1px solid rgba(30,220,136,.18);color:#d6fff0;font-size:12px;font-weight:900}
.phone-player-dealer__list{display:flex;flex-direction:column;gap:10px}
.phone-player-dealer__card{border:1px solid rgba(255,255,255,.1);border-radius:20px;background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(255,255,255,.035));padding:10px;box-shadow:0 14px 26px rgba(0,0,0,.22)}
.phone-player-dealer__media{height:82px;border-radius:16px;margin-bottom:10px;background:linear-gradient(135deg,#202a36,#0a1019);position:relative;overflow:hidden;border:1px solid rgba(255,255,255,.08)}
.phone-player-dealer__media:before{content:"";position:absolute;inset:13px 22px;border-radius:18px 24px 12px 12px;background:linear-gradient(135deg,#25df8b,#5ef0b2);box-shadow:54px 14px 0 -11px rgba(255,255,255,.18),-42px 16px 0 -13px rgba(255,255,255,.14)}
.phone-player-dealer__media:after{content:"";position:absolute;left:45px;right:45px;bottom:15px;height:12px;border-radius:999px;background:rgba(0,0,0,.32);box-shadow:-35px 0 0 -1px rgba(0,0,0,.55),35px 0 0 -1px rgba(0,0,0,.55)}
.phone-player-dealer__row{display:flex;justify-content:space-between;align-items:flex-start;gap:9px}
.phone-player-dealer__name{font-size:15px;font-weight:1000;line-height:1.15;color:#fff}
.phone-player-dealer__meta{margin-top:4px;color:#a9b8b2;font-size:11px;line-height:1.35}
.phone-player-dealer__price{font-size:16px;font-weight:1000;color:#4dffb5;white-space:nowrap}
.phone-player-dealer__seller{display:flex;justify-content:space-between;gap:8px;margin-top:8px;color:#cbd8d2;font-size:11px}
.phone-player-dealer__tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}
.phone-player-dealer__tag{border-radius:999px;padding:4px 7px;background:rgba(255,255,255,.09);color:#d9fff2;font-size:10px;font-weight:900}
.phone-player-dealer__tag.warn{background:rgba(255,176,71,.18);color:#ffd797}.phone-player-dealer__tag.good{background:rgba(30,220,136,.18);color:#8dffd0}
.phone-player-dealer__actions{display:flex;gap:7px;margin-top:11px;align-items:center}.phone-player-dealer__actions input{width:100%;min-width:0;border:1px solid rgba(255,255,255,.14);border-radius:14px;padding:10px;background:rgba(255,255,255,.08);color:white;font-weight:900;outline:none}
.phone-player-dealer__actions button{white-space:nowrap}.phone-player-dealer__actions button.danger{background:#ff5d58;color:#fff}
.phone-player-dealer__empty{text-align:center;border:1px dashed rgba(255,255,255,.16);border-radius:20px;padding:20px 12px;color:#a9c3b8;font-size:13px;line-height:1.35;background:rgba(255,255,255,.04)}
`;document.head.appendChild(style)}
function setNotice(message){notice=message||``;render()}
function refresh(){engine(`careerMPPartySharedVehicles.getUiState()`,safeState)}
function findPrice(id){if(!root)return 0;let fields=Array.from(root.querySelectorAll(`[data-price-for]`));let field=fields.find(item=>item.getAttribute(`data-price-for`)===String(id));return Math.max(0,parseInt(field&&field.value,10)||0)}
function runAction(action,id){if(!id)return;if(action===`buy`){engine(`careerMPPartySharedVehicles.buyListing("${luaString(id)}")`);setNotice(`Purchase request sent.`)}else if(action===`delist`){engine(`careerMPPartySharedVehicles.delistVehicle("${luaString(id)}")`);setNotice(`Listing removed.`)}else if(action===`list`){let price=findPrice(id);if(price<=0){setNotice(`Enter a valid asking price first.`);return}engine(`careerMPPartySharedVehicles.listVehicle("${luaString(id)}", ${price})`);setNotice(`Vehicle listed for ${money(price)}.`)}setTimeout(refresh,350);setTimeout(refresh,1200)}
function bind(){if(!root)return;root.querySelectorAll(`[data-tab]`).forEach(button=>button.addEventListener(`click`,()=>{activeTab=button.getAttribute(`data-tab`);render()}));root.querySelectorAll(`[data-action]`).forEach(button=>button.addEventListener(`click`,()=>runAction(button.getAttribute(`data-action`),button.getAttribute(`data-id`))));root.querySelectorAll(`input`).forEach(input=>{input.addEventListener(`focus`,()=>engine(`setCEFTyping(true)`));input.addEventListener(`blur`,()=>engine(`setCEFTyping(false)`))});let search=root.querySelector(`[data-search]`);search&&search.addEventListener(`input`,()=>{searchQuery=search.value||``;render()});let refreshButton=root.querySelector(`[data-refresh]`);refreshButton&&refreshButton.addEventListener(`click`,()=>refresh())}
function matchesSearch(item){let query=searchQuery.trim().toLowerCase();if(!query)return!0;let text=[item.vehicleName,item.model,item.sellerName,item.askingPrice,item.marketValue].join(` `).toLowerCase();return text.includes(query)}
function vehicleTags(vehicle){let tags=[];if(vehicle.isCurrent)tags.push(`<span class="phone-player-dealer__tag good">Current</span>`);if(vehicle.needsRepair)tags.push(`<span class="phone-player-dealer__tag warn">Needs repair</span>`);if(vehicle.isListedForSale)tags.push(`<span class="phone-player-dealer__tag good">Listed</span>`);if(vehicle.isLoanedOut)tags.push(`<span class="phone-player-dealer__tag">Loaned</span>`);if(!tags.length)tags.push(`<span class="phone-player-dealer__tag">Private stock</span>`);return tags.join(``)}
function listingCard(listing,own){return `<article class="phone-player-dealer__card"><div class="phone-player-dealer__media"></div><div class="phone-player-dealer__row"><div><div class="phone-player-dealer__name">${html(listing.vehicleName||`Vehicle`)}</div><div class="phone-player-dealer__meta">${html(listing.model||`Unknown model`)}</div></div><div class="phone-player-dealer__price">${money(listing.askingPrice)}</div></div><div class="phone-player-dealer__seller"><span>${own?`Your listing`:`Seller: ${html(listing.sellerName||`Player`)}`}</span><span>CareerMP</span></div><div class="phone-player-dealer__actions">${own?`<button class="danger" data-action="delist" data-id="${html(listing.listingId)}">Remove ad</button>`:`<button data-action="buy" data-id="${html(listing.listingId)}">Buy now</button>`}</div></article>`}
function vehicleCard(vehicle){let id=String(vehicle.inventoryId||``);let defaultPrice=Number(vehicle.askingPrice||vehicle.marketValue||1000)||1000;return `<article class="phone-player-dealer__card"><div class="phone-player-dealer__media"></div><div class="phone-player-dealer__row"><div><div class="phone-player-dealer__name">${html(vehicle.vehicleName||`Vehicle`)}</div><div class="phone-player-dealer__meta">${html(vehicle.model||`Unknown model`)} • Est. ${money(vehicle.marketValue)}</div></div></div><div class="phone-player-dealer__tags">${vehicleTags(vehicle)}</div><div class="phone-player-dealer__actions">${vehicle.isListedForSale?`<span class="phone-player-dealer__price">${money(vehicle.askingPrice)}</span><button class="danger" data-action="delist" data-id="${html(vehicle.listingId)}">Remove ad</button>`:`<input type="number" min="1" step="1" value="${html(defaultPrice)}" data-price-for="${html(id)}"><button data-action="list" data-id="${html(id)}">Post ad</button>`}</div></article>`}
function render(){if(!root)return;ensureStyle();let marketplace=state.marketplace||{},publicListings=array(marketplace.publicListings),myListings=array(marketplace.myListings),owned=array(state.ownedVehicles),marketFiltered=publicListings.filter(matchesSearch),ownedFiltered=owned.filter(matchesSearch),mineFiltered=myListings.filter(matchesSearch);let content=``;if(activeTab===`market`)content=marketFiltered.length?marketFiltered.map(item=>listingCard(item,false)).join(``):`<div class="phone-player-dealer__empty">No vehicle ads found. Try another search or wait for players to list cars.</div>`;if(activeTab===`cars`)content=ownedFiltered.length?ownedFiltered.map(vehicleCard).join(``):`<div class="phone-player-dealer__empty">No garage vehicles matched your search.</div>`;if(activeTab===`mine`)content=mineFiltered.length?mineFiltered.map(item=>listingCard(item,true)).join(``):`<div class="phone-player-dealer__empty">You do not have matching active dealership ads.</div>`;root.innerHTML=`<div class="phone-player-dealer"><section class="phone-player-dealer__hero"><div class="phone-player-dealer__hero-kicker">Online dealership</div><strong>Buy and sell player cars.</strong><span>Post your own ad, browse server listings, and trade vehicles from the RLS phone.</span></section><div class="phone-player-dealer__search"><input data-search type="text" value="${html(searchQuery)}" placeholder="Search cars, sellers, prices..."><div class="phone-player-dealer__tabs"><button class="phone-player-dealer__tab ${activeTab===`market`?`is-active`:``}" data-tab="market">Market (${publicListings.length})</button><button class="phone-player-dealer__tab ${activeTab===`cars`?`is-active`:``}" data-tab="cars">My Cars (${owned.length})</button><button class="phone-player-dealer__tab ${activeTab===`mine`?`is-active`:``}" data-tab="mine">My Ads (${myListings.length})</button></div></div>${notice?`<div class="phone-player-dealer__notice">${html(notice)}</div>`:``}<div class="phone-player-dealer__list">${content}</div><div style="height:10px"></div></div>`;bind()}
onMounted(()=>{ensureStyle();engine(`extensions.load("careerMPPartySharedVehicles")`);setTimeout(refresh,100);refreshTimer=setInterval(refresh,1500)});
onBeforeUnmount(()=>{refreshTimer&&clearInterval(refreshTimer);engine(`setCEFTyping(false)`)});
return(_ctx,_cache)=>(openBlock(),createBlock(PhoneWrapper_default,{"app-name":`Player Dealer`},{default:withCtx(()=>[createBaseVNode(`div`,{class:`phone-player-dealership-native`,ref:el=>root=el},null,512)]),_:1}))
}}
"""

PLAYER_DEALERSHIP_ROUTE = (
    "{path:`phone-player-dealership`,name:`phone-player-dealership`,component:"
    + PLAYER_DEALERSHIP_COMPONENT.strip()
    + "},"
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
    route_start = index_js.find("{path:`phone-player-dealership`,name:`phone-player-dealership`,component:")
    if route_start >= 0:
        route_end = index_js.find("{path:`phone-repo`,name:`phone-repo`", route_start)
        if route_end < 0:
            raise RuntimeError("Could not find the RLS phone repo route after the Player Dealer route.")
        index_js = index_js[:route_start] + PLAYER_DEALERSHIP_ROUTE + index_js[route_end:]
    else:
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


def build_patched_rls_zip(rls_zip: Path, out_zip: Path) -> Path:
    if not rls_zip.is_file():
        raise FileNotFoundError(f"RLS zip not found: {rls_zip}")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    replacement_paths = {INDEX_PATH, LAYOUT_PATH, TILE_OUTPUT_PATH}

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

        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as target:
            copied = set()
            for info in source.infolist():
                if info.filename in replacement_paths or info.filename in copied:
                    continue
                copied.add(info.filename)
                data = source.read(info.filename)
                new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                new_info.comment = info.comment
                new_info.extra = info.extra
                new_info.internal_attr = info.internal_attr
                new_info.external_attr = info.external_attr
                new_info.create_system = info.create_system
                target.writestr(new_info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

            target.writestr(INDEX_PATH, patched_index, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            target.writestr(LAYOUT_PATH, patched_layout, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            target.writestr(TILE_OUTPUT_PATH, tile_png, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(out_zip, "r") as target:
        bad_file = target.testzip()
        if bad_file:
            raise RuntimeError(f"Generated patched RLS zip failed validation at {bad_file}")
        names = target.namelist()
        for required_path in (INDEX_PATH, LAYOUT_PATH, TILE_OUTPUT_PATH):
            if names.count(required_path) != 1:
                raise RuntimeError(f"{required_path} appears {names.count(required_path)} times in generated zip")
        patched_index = target.read(INDEX_PATH).decode("utf-8")
        if "PhonePlayerDealership" not in patched_index:
            raise RuntimeError("Generated RLS zip does not contain the native Player Dealer phone app")

    return out_zip


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build local RLS phone integration files for Player Dealership."
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
    parser.add_argument(
        "--full-rls-out",
        default="",
        help=(
            "Optional output path for a full patched RLS compatible zip. "
            "Use this for the native RLS phone app workflow."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.full_rls_out:
        out_zip = build_patched_rls_zip(Path(args.rls_zip).resolve(), Path(args.full_rls_out).resolve())
    else:
        out_zip = build_overlay(Path(args.rls_zip).resolve(), Path(args.out_dir).resolve(), args.output_name)
    print(out_zip)
    print(out_zip.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
