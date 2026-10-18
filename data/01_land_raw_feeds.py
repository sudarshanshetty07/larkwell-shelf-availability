# Databricks notebook source
# MAGIC %md
# MAGIC # 1 · Land the day's raw feeds (simulated source systems)
# MAGIC
# MAGIC **Larkwell Foods is a fictitious UK food retailer. Every record is synthetic.**
# MAGIC
# MAGIC Each morning Larkwell's source systems drop their extracts into the Unity Catalog volume `raw.landing`.
# MAGIC This notebook plays the part of those systems for one business day.
# MAGIC
# MAGIC | Feed | Format | Source system | Rows (approx.) |
# MAGIC |---|---|---|---|
# MAGIC | `store_master`, `product_master`, `supplier_master`, `depot_master` | CSV | Master data | 900 / 6,025 / 120 / 7 |
# MAGIC | `store_stock` | CSV, gzip, one file per area | Store stock and sales system | 5,400,000 |
# MAGIC | `deliveries` | JSON lines | Depot and supplier deliveries | ~390,000 |
# MAGIC | `order_events` | JSON lines | Store ordering system | ~110,000 |
# MAGIC | `stock_counts` | JSON lines | Handheld stock counts | ~75,000 |
# MAGIC | `waste` | JSON lines | Waste recording | ~150,000 |
# MAGIC | `allocations` | JSON lines | Supply allocation | ~100,000 |
# MAGIC
# MAGIC **The files carry signals, not answers.** Nothing in them says why a shelf is empty: the Lakeflow pipeline works that out.
# MAGIC They also carry realistic noise that the pipeline has to handle correctly:
# MAGIC - lines with several kinds of evidence at once;
# MAGIC - order blocks that were later released;
# MAGIC - duplicate delivery lines re-sent by the depot system;
# MAGIC - a few malformed records;
# MAGIC - master-data corrections.
# MAGIC
# MAGIC The notebook also writes an **answer key** to the `raw.answer_key` volume, which the pipeline never reads.
# MAGIC It's used to test the pipeline's output row by row. The headline counts are pinned, so the business case always shows the same numbers.

# COMMAND ----------

dbutils.widgets.text("catalog", "larkwell_osa")
dbutils.widgets.text("business_date", "2026-10-17")
dbutils.widgets.text("seed", "20261017")

CATALOG = dbutils.widgets.get("catalog")
BUSINESS_DATE = dbutils.widgets.get("business_date")
SEED = int(dbutils.widgets.get("seed"))
LANDING = f"/Volumes/{CATALOG}/raw/landing"
ANSWER_KEY = f"/Volumes/{CATALOG}/raw/answer_key/{BUSINESS_DATE}"
print("Landing zone:", LANDING, "| business date:", BUSINESS_DATE, "| seed:", SEED)

# COMMAND ----------

import json
import os
import re

import numpy as np
import pandas as pd

rng = np.random.default_rng(SEED)
N_STORES, N_UPCS = 900, 6000

# Exact headline counts: (reason, gaps, lows, space-lows). Sales-lows = lows - space-lows.
TARGETS = [
    ("KNOWN_GAP", 40446, 21805, 10843),
    ("SUPPLIER_SHORT", 26454, 14257, 7121),
    ("UNDER_FORECAST", 20058, 10931, 5452),
    ("ORDER_DELIVERY_BLOCK", 15957, 8534, 4262),
    ("SCARCITY", 10817, 5756, 2830),
    ("STOCKFILE_ADJUSTMENT", 10582, 5715, 2880),
    ("WASTE", 6775, 3662, 1873),
    ("INVESTIGATE", 2676, 1409, 709),
]
SS_TYPES = [("DEPOT_SHORT", 10195), ("LOGISTICS_DELAY", 10226), ("PRODUCTION_ISSUE", 10107),
            ("RAW_MATERIAL_SHORTAGE", 10183)]
assert sum(n for _, n in SS_TYPES) == 26454 + 14257

# The order the pipeline's root-cause rules check the evidence in (first match wins).
CASCADE = ["KNOWN_GAP", "SCARCITY", "SUPPLIER_SHORT", "ORDER_DELIVERY_BLOCK", "STOCKFILE_ADJUSTMENT", "WASTE",
           "UNDER_FORECAST", "INVESTIGATE"]
RANK = {r: i + 1 for i, r in enumerate(CASCADE)}

# COMMAND ----------

# MAGIC %md ## Depots and stores

# COMMAND ----------

# division -> area -> (stores, depot)
AREAS = {
    "North & Scotland": {"Scotland": (104, "Northgate DC"), "North East": (70, "Pennine DC"),
                         "Yorkshire": (68, "Pennine DC"), "North West": (130, "Merseyvale DC")},
    "Central": {"East Midlands": (52, "Midshire DC"), "West Midlands": (45, "Midshire DC")},
    "South": {"London": (175, "Riverside DC"), "South East": (140, "Wealden DC"),
              "South West & Wales": (116, "Westcountry DC")},
}
DEPOTS = [("Northgate DC", "Scotland"), ("Pennine DC", "North East & Yorkshire"), ("Merseyvale DC", "North West"),
          ("Midshire DC", "Midlands"), ("Riverside DC", "London"), ("Wealden DC", "South East"),
          ("Westcountry DC", "South West & Wales")]
DEPOT_ID = {name: f"D{i + 1:02d}" for i, (name, _) in enumerate(DEPOTS)}

TOWNS = {
    "Scotland": "Edinburgh,Glasgow,Aberdeen,Dundee,Inverness,Perth,Stirling,Paisley,East Kilbride,Livingston,Hamilton,Cumbernauld,Kirkcaldy,Dunfermline,Ayr,Kilmarnock,Greenock,Falkirk,Coatbridge,Airdrie,Irvine,Dumfries,Elgin,Oban,Fort William,St Andrews,Arbroath,Montrose,Peterhead,Galashiels,Peebles,North Berwick,Musselburgh,Dalkeith,Bearsden,Milngavie,Clydebank,Dumbarton,Helensburgh,Largs,Troon,Prestwick,Kelso,Hawick,Forfar,Crieff,Pitlochry,Aviemore,Nairn,Thurso",
    "North East": "Newcastle,Sunderland,Durham,Middlesbrough,Gateshead,Darlington,Hartlepool,Stockton-on-Tees,Hexham,Morpeth,Alnwick,Berwick-upon-Tweed,Whitley Bay,Tynemouth,South Shields,Jarrow,Washington,Chester-le-Street,Consett,Bishop Auckland,Redcar,Guisborough,Yarm,Cramlington,Blyth,Ashington,Ponteland,Seaham,Peterlee,Barnard Castle",
    "Yorkshire": "Leeds,Sheffield,York,Harrogate,Huddersfield,Wakefield,Doncaster,Rotherham,Barnsley,Halifax,Hull,Scarborough,Whitby,Beverley,Ilkley,Skipton,Ripon,Selby,Pontefract,Castleford,Dewsbury,Keighley,Otley,Wetherby,Malton,Bridlington,Northallerton,Thirsk,Goole,Batley,Morley,Pudsey,Holmfirth",
    "North West": "Manchester,Liverpool,Chester,Preston,Lancaster,Blackpool,Bolton,Stockport,Warrington,Wigan,Southport,Altrincham,Wilmslow,Knutsford,Macclesfield,Bury,Rochdale,Oldham,Burnley,Blackburn,Kendal,Carlisle,Keswick,Penrith,Ambleside,Windermere,Whitehaven,Barrow-in-Furness,Ormskirk,St Helens,Widnes,Runcorn,Crewe,Nantwich,Northwich,Formby,Crosby,Birkenhead,Wallasey,Heswall,Didsbury,Chorlton,Salford,Prestwich,Lytham St Annes,Clitheroe,Morecambe,Ulverston",
    "East Midlands": "Nottingham,Leicester,Derby,Lincoln,Northampton,Loughborough,Mansfield,Chesterfield,Newark,Grantham,Stamford,Market Harborough,Kettering,Corby,Wellingborough,Oakham,Melton Mowbray,Hinckley,Coalville,Ashby-de-la-Zouch,Matlock,Bakewell,Buxton,Ilkeston,Long Eaton,Beeston,West Bridgford,Southwell,Retford,Worksop,Boston,Skegness,Spalding,Sleaford,Gainsborough,Louth",
    "West Midlands": "Birmingham,Coventry,Wolverhampton,Solihull,Sutton Coldfield,Worcester,Hereford,Shrewsbury,Telford,Stafford,Lichfield,Tamworth,Nuneaton,Rugby,Warwick,Leamington Spa,Stratford-upon-Avon,Kenilworth,Redditch,Bromsgrove,Kidderminster,Malvern,Ludlow,Evesham,Walsall,Dudley,Stourbridge,Halesowen,West Bromwich,Burton upon Trent,Cannock,Newcastle-under-Lyme,Uttoxeter,Oswestry",
    "London": "Covent Garden,Islington,Clapham,Camden,Greenwich,Hammersmith,Kensington,Chelsea,Wimbledon,Richmond,Ealing,Croydon,Bromley,Stratford,Canary Wharf,Battersea,Brixton,Hackney,Shoreditch,Notting Hill,Marylebone,Holborn,Victoria,Waterloo,Paddington,King's Cross,Liverpool Street,London Bridge,Euston,Fulham,Putney,Balham,Tooting,Streatham,Dulwich,Peckham,Lewisham,Blackheath,Hampstead,Highgate,Muswell Hill,Crouch End,Finchley,Hendon,Harrow,Wembley,Kingston,Sutton,Barnet,Walthamstow,Ilford,Romford,Bexleyheath,Woolwich,Chiswick,Acton,Shepherd's Bush,Southwark,Bermondsey,Angel,Kentish Town,Stoke Newington,Dalston,Bow,Mile End,Wapping,Pimlico,Mayfair,Soho,Fitzrovia,Bloomsbury,Clerkenwell,Barbican,Moorgate,Farringdon,Aldgate,St Pancras,Vauxhall,Kennington,Herne Hill,Forest Hill,Catford,Eltham,Orpington,Twickenham,Teddington,Hounslow,Uxbridge,Ruislip,Pinner,Stanmore,Edgware,Mill Hill,Southgate,Palmers Green,Wood Green,Tottenham,Leyton,Wanstead,Woodford,Chingford,Barking,Hornchurch,Upminster",
    "South East": "Brighton,Guildford,Reading,Oxford,Canterbury,Maidstone,Tunbridge Wells,Sevenoaks,Tonbridge,Crawley,Horsham,Chichester,Worthing,Eastbourne,Hastings,Lewes,Winchester,Basingstoke,Southampton,Portsmouth,Farnham,Woking,Epsom,Dorking,Reigate,Camberley,Bracknell,Windsor,Maidenhead,High Wycombe,Aylesbury,Banbury,Bicester,Abingdon,Henley-on-Thames,Marlow,Beaconsfield,Amersham,St Albans,Watford,Harpenden,Hitchin,Stevenage,Welwyn Garden City,Chelmsford,Colchester,Brentwood,Southend-on-Sea,Cambridge,Ely,Bury St Edmunds,Ipswich,Norwich,Ashford,Folkestone,Dover,Whitstable,Margate,Rochester,Dartford",
    "South West & Wales": "Bristol,Bath,Exeter,Plymouth,Truro,Cheltenham,Gloucester,Taunton,Salisbury,Bournemouth,Poole,Dorchester,Weymouth,Yeovil,Wells,Bridgwater,Barnstaple,Torquay,Newton Abbot,Totnes,Falmouth,Penzance,St Ives,Newquay,Tavistock,Chippenham,Devizes,Marlborough,Frome,Stroud,Cirencester,Tewkesbury,Cardiff,Swansea,Newport,Bridgend,Llandudno,Aberystwyth,Carmarthen,Wrexham,Bangor,Cowbridge,Abergavenny,Monmouth,Chepstow,Tenby,Brecon,Conwy,Penarth",
}

# Format x business scope, exact store counts
FORMATS = [("Superstore", "Owned", 252), ("Superstore", "Franchise", 18), ("Local", "Owned", 343),
           ("Local", "Franchise", 46), ("Travel", "Owned", 108), ("Travel", "Franchise", 3),
           ("Forecourt", "Owned", 67), ("Forecourt", "Franchise", 10), ("Outlet", "Owned", 48),
           ("Outlet", "Franchise", 5)]
fmt_labels = [(f, s) for f, s, n in FORMATS for _ in range(n)]
rng.shuffle(fmt_labels)
NAME_PATTERNS = {"Superstore": ["{t}", "{t} Retail Park", "{t} Superstore"],
                 "Local": ["{t} Local", "{t} High Street", "{t} Village"],
                 "Travel": ["{t} Station", "{t} Central Station"],
                 "Forecourt": ["{t} Forecourt", "{t} Services"],
                 "Outlet": ["{t} Outlet", "{t} Outlet Village"]}


def store_name(town, fmt, used):
    for pattern in NAME_PATTERNS[fmt]:
        cand = pattern.format(t=town)
        if cand not in used:
            return cand
    return None


stores, used, k = [], set(), 0
for division, areas in AREAS.items():
    for area, (n, depot) in areas.items():
        towns = TOWNS[area].split(",")
        t = 0
        for i in range(n):
            fmt, scope = fmt_labels[k]
            if area == "London" and i == 0:          # flagship used as the app's default scan store
                fmt, scope, name = "Superstore", "Owned", "Covent Garden"
                j = next(x for x in range(k, len(fmt_labels)) if fmt_labels[x] == ("Superstore", "Owned"))
                fmt_labels[k], fmt_labels[j] = fmt_labels[j], fmt_labels[k]
            else:
                name, tries = None, 0
                while name is None:
                    name = store_name(towns[t % len(towns)], fmt, used)
                    t += 1
                    tries += 1
                    assert tries <= 3 * len(towns), f"ran out of {fmt} names in {area}"
            used.add(name)
            stores.append({"store_idx": len(stores), "store": name, "division": division, "area": area,
                           "site_trading_group": fmt, "business_scope": scope, "depot": depot})
            k += 1
dim_store = pd.DataFrame(stores)
dim_store["store_id"] = [f"S{i + 1:04d}" for i in dim_store.store_idx]
assert len(dim_store) == N_STORES and dim_store.store.is_unique
print(dim_store.groupby(["site_trading_group", "business_scope"]).size())

# COMMAND ----------

# MAGIC %md ## Products and suppliers

# COMMAND ----------

# category -> (cluster, department, {product group: (UPC count, "Base:size,size;...")})
CATALOGUE = {
    "Bakery": ("Ambient", "Fresh Foods", {
        "Bread": (161, "White Bloomer:400g,800g;Seeded Batch Loaf:400g,800g;Sourdough Loaf:400g,800g;Wholemeal Loaf:400g,800g;Rye Loaf:400g,800g;Malted Grain Loaf:400g,800g;Tiger Loaf:400g,800g;Granary Cob:400g,800g;Ciabatta:270g,540g;Baguette:250g,400g;Brioche Loaf:400g,600g;Soda Bread:400g,600g"),
        "Cakes": (119, "Lemon Drizzle Cake:300g,450g;Victoria Sponge:300g,450g;Carrot Cake:300g,450g;Chocolate Fudge Cake:300g,450g;Coffee & Walnut Cake:300g,450g;Madeira Cake:300g,450g;Fruit Cake:400g,800g;Red Velvet Cake:300g,450g;Bakewell Slices:6pk,12pk"),
        "Morning Goods": (107, "All-Butter Croissants:4pk,8pk;Pain au Chocolat:4pk,8pk;Cinnamon Swirls:4pk,8pk;English Muffins:4pk,6pk;Crumpets:6pk,12pk;Scotch Pancakes:6pk,12pk;Fruit Scones:4pk,6pk;Plain Bagels:4pk,6pk"),
        "Wraps & Flatbreads": (76, "Tortilla Wraps:4pk,8pk;Wholemeal Wraps:4pk,8pk;Plain Naan:2pk,4pk;Garlic Naan:2pk,4pk;Pitta Bread:4pk,6pk;Chapatis:4pk,8pk")}),
    "Beverages": ("Ambient", "Drinks", {
        "Chilled Drinks": (98, "Orange Juice:1L,1.75L;Apple Juice:1L,1.75L;Mango Smoothie:250ml,750ml;Berry Smoothie:250ml,750ml;Cloudy Lemonade:330ml,1L;Iced Latte:250ml,1L;Coconut Water:330ml,1L"),
        "Hot Drinks": (138, "Breakfast Tea:80 bags,160 bags;Earl Grey Tea:50 bags,100 bags;Green Tea:40 bags,80 bags;Peppermint Tea:20 bags,40 bags;Ground Coffee:227g,454g;Coffee Beans:500g,1kg;Instant Coffee:100g,200g;Decaf Coffee:100g,200g;Hot Chocolate:250g,500g;Chai Latte Mix:200g,400g"),
        "Soft Drinks": (113, "Sparkling Water:500ml,1.5L;Still Water:500ml,1.5L;Cola:330ml,2L;Diet Cola:330ml,2L;Lemon & Lime Soda:330ml,2L;Ginger Beer:330ml,1L;Elderflower Presse:275ml,750ml;Tonic Water:200ml,1L;Orange Squash:1L,1.5L")}),
    "Grocery": ("Ambient", "Grocery", {
        "Baking": (125, "Plain Flour:1kg,1.5kg;Self-Raising Flour:1kg,1.5kg;Strong Bread Flour:1kg,1.5kg;Caster Sugar:500g,1kg;Icing Sugar:500g,1kg;Light Brown Sugar:500g,1kg;Baking Powder:100g,170g;Cocoa Powder:125g,250g;Vanilla Extract:38ml,100ml"),
        "Breakfast": (118, "Porridge Oats:500g,1kg;Granola:500g,1kg;Muesli:500g,1kg;Corn Flakes:500g,750g;Bran Flakes:500g,750g;Honey Nut Clusters:375g,750g;Strawberry Jam:340g,454g;Orange Marmalade:340g,454g;Clear Honey:340g,454g"),
        "Canned Goods": (123, "Chopped Tomatoes:400g,4x400g;Baked Beans:415g,4x415g;Chickpeas:400g,4x400g;Red Kidney Beans:400g,4x400g;Tuna Chunks:145g,4x145g;Sweetcorn:198g,3x198g;Coconut Milk:400ml,4x400ml;Lentil Soup:400g,4x400g;Tomato Soup:400g,4x400g"),
        "Condiments": (120, "Tomato Ketchup:460g,920g;Mayonnaise:400g,800g;English Mustard:100g,180g;Wholegrain Mustard:100g,180g;Brown Sauce:425g,600g;Sweet Chilli Sauce:280g,500g;Soy Sauce:150ml,500ml;Balsamic Vinegar:250ml,500ml;Extra Virgin Olive Oil:500ml,1L"),
        "Cooking Sauces": (116, "Tikka Masala Sauce:350g,500g;Korma Sauce:350g,500g;Bolognese Sauce:500g,750g;Arrabbiata Sauce:340g,500g;Pesto Genovese:190g,290g;Red Pesto:190g,290g;Sweet & Sour Sauce:350g,500g;Black Bean Sauce:350g,500g;Carbonara Sauce:300g,450g"),
        "Pasta & Rice": (143, "Spaghetti:500g,1kg;Penne:500g,1kg;Fusilli:500g,1kg;Linguine:500g,1kg;Rigatoni:500g,1kg;Basmati Rice:500g,1kg,2kg;Long Grain Rice:500g,1kg,2kg;Arborio Rice:500g,1kg;Egg Noodles:250g,500g;Couscous:500g,1kg")}),
    "Snacks & Confectionery": ("Ambient", "Grocery", {
        "Biscuits": (100, "Digestives:400g,800g;Chocolate Digestives:300g,600g;Shortbread:150g,300g;Ginger Nuts:250g,500g;Bourbon Creams:200g,400g;Custard Creams:200g,400g;Oat Biscuits:300g,600g;Jam Rings:200g,400g"),
        "Chocolate": (91, "Milk Chocolate Bar:100g,200g;Dark Chocolate 70%:100g,200g;White Chocolate Bar:100g,200g;Hazelnut Chocolate Bar:100g,200g;Salted Caramel Chocolate:100g,200g;Chocolate Buttons:70g,150g;Chocolate Truffles:150g,300g"),
        "Crisps": (133, "Sea Salt Crisps:6pk,150g;Salt & Vinegar Crisps:6pk,150g;Cheese & Onion Crisps:6pk,150g;Sour Cream & Chive Crisps:6pk,150g;Sweet Chilli Crisps:6pk,150g;Tortilla Chips:200g,400g;Sweet & Salty Popcorn:100g,200g;Veggie Crisps:100g,200g;Pretzels:150g,300g;Hand-Cooked Crisps:150g,300g"),
        "Nuts & Dried Fruit": (95, "Salted Peanuts:200g,400g;Cashews:200g,400g;Almonds:200g,400g;Mixed Nuts:200g,400g;Pistachios:150g,300g;Sultanas:375g,750g;Dried Apricots:250g,500g")}),
    "Dairy": ("Chilled", "Chilled", {
        "Butter & Spreads": (64, "Salted Butter:250g,500g;Unsalted Butter:250g,500g;Spreadable Butter:250g,500g;Olive Spread:500g,1kg;Plant Butter:250g,500g"),
        "Cheese": (127, "Mature Cheddar:200g,400g;Extra Mature Cheddar:200g,400g;Red Leicester:200g,400g;Brie:200g,400g;Camembert:150g,250g;Mozzarella:125g,250g;Halloumi:225g,450g;Stilton:200g,400g;Parmesan:100g,200g;Feta:200g,400g"),
        "Cream": (66, "Double Cream:300ml,600ml;Single Cream:300ml,600ml;Whipping Cream:300ml,600ml;Sour Cream:150ml,300ml;Creme Fraiche:200ml,300ml"),
        "Milk": (130, "Whole Milk:1 pint,2 pints,4 pints;Semi-Skimmed Milk:1 pint,2 pints,4 pints;Skimmed Milk:1 pint,2 pints,4 pints;Oat Drink:1L,2L;Almond Drink:1L,2L;Lactose-Free Milk:1L,2L;Jersey Milk:1L,2L;Goat's Milk:1L,2L"),
        "Yogurt": (95, "Greek Yogurt:500g,1kg;Natural Yogurt:500g,1kg;Strawberry Yogurt:4x125g,500g;Vanilla Yogurt:4x125g,500g;Skyr:450g,850g;Kefir:500ml,1L;Coconut Yogurt:350g,500g")}),
    "Deli & Cooked Meats": ("Chilled", "Chilled", {
        "Dips & Houmous": (84, "Classic Houmous:200g,300g;Red Pepper Houmous:200g,300g;Guacamole:150g,250g;Tzatziki:200g,300g;Sour Cream & Chive Dip:200g,300g;Tomato Salsa:200g,300g"),
        "Olives & Antipasti": (73, "Green Olives:160g,320g;Kalamata Olives:160g,320g;Sun-Dried Tomatoes:140g,280g;Roasted Peppers:140g,280g;Stuffed Peppers:150g,300g;Artichoke Hearts:140g,280g"),
        "Pate & Spreads": (37, "Chicken Liver Pate:170g,340g;Smoked Mackerel Pate:115g,230g;Mushroom Pate:115g,230g"),
        "Sliced Meats": (116, "Honey Roast Ham:120g,240g;Smoked Ham:120g,240g;Roast Chicken Slices:120g,240g;Salami:70g,140g;Chorizo:70g,140g;Prosciutto:70g,140g;Pastrami:100g,200g;Turkey Slices:120g,240g;Roast Beef Slices:100g,200g")}),
    "Desserts": ("Chilled", "Chilled", {
        "Cheesecakes": (62, "Vanilla Cheesecake:2pk,4pk;Lemon Cheesecake:2pk,4pk;Raspberry Cheesecake:2pk,4pk;Salted Caramel Cheesecake:2pk,4pk;Chocolate Cheesecake:2pk,4pk"),
        "Tarts": (84, "Lemon Tart:2pk,4pk;Treacle Tart:2pk,4pk;Bakewell Tart:2pk,4pk;Chocolate Tart:2pk,4pk;Apple Tart:2pk,4pk;Custard Tarts:4pk,6pk"),
        "Trifles & Pots": (88, "Sherry Trifle:2pk,4pk;Chocolate Pots:2pk,4pk;Creme Brulee:2pk,4pk;Eton Mess:2pk,4pk;Panna Cotta:2pk,4pk;Sticky Toffee Pudding:2pk,4pk;Tiramisu:2pk,4pk")}),
    "Fresh Meat": ("Chilled", "Fresh Foods", {
        "Beef": (143, "Beef Mince 5% Fat:250g,500g,750g;Beef Mince 12% Fat:250g,500g,750g;Sirloin Steak:225g,450g;Ribeye Steak:225g,450g;Fillet Steak:170g,340g;Rump Steak:225g,450g;Diced Beef:400g,800g;Beef Brisket:500g,1kg;Topside Joint:750g,1.25kg;Beef Burgers:2pk,4pk"),
        "Lamb": (78, "Lamb Leg Joint:1kg,2kg;Lamb Shoulder:1kg,2kg;Lamb Chops:4pk,8pk;Lamb Mince:400g,800g;Diced Lamb:400g,800g;Lamb Shanks:2pk,4pk"),
        "Pork": (111, "Pork Sausages:6pk,12pk;Smoked Bacon:200g,400g;Unsmoked Bacon:200g,400g;Pork Loin Steaks:4pk,8pk;Pork Belly Slices:400g,800g;Pork Shoulder Joint:1kg,2kg;Pork Mince:400g,800g;Gammon Joint:750g,1.5kg"),
        "Poultry": (103, "Chicken Breast Fillets:300g,600g;Chicken Thighs:500g,1kg;Chicken Drumsticks:500g,1kg;Whole Chicken:1.4kg,2kg;Chicken Wings:500g,1kg;Turkey Breast Steaks:300g,600g;Duck Breasts:2pk,4pk;Chicken Mini Fillets:300g,600g")}),
    "Fresh Produce": ("Chilled", "Fresh Foods", {
        "Fruit": (248, "Bananas:5pk,1kg;Royal Gala Apples:4pk,6pk,1kg;Braeburn Apples:4pk,6pk;Conference Pears:4pk,6pk;Strawberries:227g,400g,600g;Raspberries:150g,300g;Blueberries:150g,300g,500g;Blackberries:150g,300g;Seedless Grapes:500g,1kg;Easy Peeler Clementines:600g,1kg;Oranges:4pk,6pk;Lemons:3pk,5pk;Limes:3pk,5pk;Mangoes:1pk,2pk;Pineapple:1pk,2pk;Kiwi Fruit:4pk,6pk;Plums:400g,600g;Nectarines:4pk,6pk;Cherries:200g,400g"),
        "Herbs": (128, "Basil:30g,60g;Coriander:30g,60g;Flat-Leaf Parsley:30g,60g;Mint:30g,60g;Rosemary:20g,40g;Thyme:20g,40g;Chives:20g,40g;Dill:20g,40g;Sage:20g,40g;Tarragon:20g,40g"),
        "Prepared Veg": (77, "Stir Fry Vegetables:300g,600g;Vegetable Rice:300g,600g;Butternut Squash Chunks:400g,800g;Sliced Mushrooms:250g,500g;Diced Onions:300g,600g;Cauliflower Florets:320g,640g"),
        "Salad": (175, "Baby Leaf Salad:120g,200g;Rocket:60g,120g;Watercress:85g,150g;Iceberg Lettuce:1pk,2pk;Cos Lettuce:2pk,3pk;Cherry Tomatoes:250g,500g;Vine Tomatoes:6pk,500g;Cucumber:1pk,2pk;Spring Onions:100g,200g;Radishes:240g,400g;Mixed Peppers:3pk,6pk;Beetroot:250g,500g;Celery:1pk,2pk"),
        "Vegetables": (235, "Potatoes:1kg,2kg,2.5kg;Baby Potatoes:750g,1.5kg;Sweet Potatoes:750g,1kg;Carrots:500g,1kg;Parsnips:500g,750g;Broccoli:335g,500g;Cauliflower:1pk,2pk;Brussels Sprouts:500g,1kg;Green Beans:200g,400g;Mangetout:150g,300g;Asparagus:125g,250g;Leeks:500g,750g;Courgettes:500g,750g;Aubergine:1pk,2pk;Red Onions:500g,1kg;Brown Onions:1kg,2kg;Garlic:3pk,5pk;Mushrooms:250g,500g")}),
    "Ready Meals": ("Chilled", "Chilled", {
        "British": (110, "Cottage Pie:400g,800g;Shepherd's Pie:400g,800g;Fish Pie:400g,800g;Beef Stew & Dumplings:400g,800g;Sausage & Mash:400g,800g;Chicken & Leek Pie:400g,800g;Toad in the Hole:400g,800g;Roast Chicken Dinner:400g,800g"),
        "Chinese": (82, "Sweet & Sour Chicken:400g,800g;Chicken Chow Mein:400g,800g;Beef in Black Bean Sauce:400g,800g;Egg Fried Rice:250g,500g;Kung Pao Chicken:400g,800g;Crispy Chilli Beef:400g,800g"),
        "Pub Classics": (87, "Steak & Ale Pie:400g,800g;Fish & Chips:400g,800g;Ham Hock & Mustard Mash:400g,800g;Chilli Con Carne:400g,800g;Lamb Hotpot:400g,800g;Chicken & Mushroom Pie:400g,800g;Mac & Cheese Bake:400g,800g"),
        "Indian": (109, "Chicken Tikka Masala:400g,800g;Chicken Korma:400g,800g;Lamb Rogan Josh:400g,800g;Chicken Jalfrezi:400g,800g;Butter Chicken:400g,800g;Vegetable Biryani:400g,800g;Saag Aloo:300g,600g;Dal Makhani:300g,600g"),
        "Italian": (123, "Beef Lasagne:400g,800g;Spaghetti Bolognese:400g,800g;Chicken Carbonara:400g,800g;Mushroom Risotto:400g,800g;Spinach & Ricotta Cannelloni:400g,800g;Penne Arrabbiata:400g,800g;Seafood Linguine:400g,800g;Margherita Pizza:1pk,2pk;Pepperoni Pizza:1pk,2pk")}),
    "Sandwiches & Food To Go": ("Chilled", "Chilled", {
        "Salads": (65, "Chicken Caesar Salad:220g,320g;Super Grains Salad:220g,320g;Tuna Nicoise:220g,320g;Falafel & Houmous Salad:220g,320g;Prawn Layered Salad:220g,320g"),
        "Sandwiches": (125, "Chicken & Bacon Sandwich:1pk,2pk;Egg Mayo Sandwich:1pk,2pk;Prawn Mayo Sandwich:1pk,2pk;Cheese & Pickle Sandwich:1pk,2pk;BLT Sandwich:1pk,2pk;Tuna & Sweetcorn Sandwich:1pk,2pk;Ham & Cheese Sandwich:1pk,2pk;Chicken Salad Sandwich:1pk,2pk;Coronation Chicken Sandwich:1pk,2pk"),
        "Soup": (93, "Tomato & Basil Soup:400g,600g;Butternut Squash Soup:400g,600g;Chicken Noodle Soup:400g,600g;Minestrone:400g,600g;Leek & Potato Soup:400g,600g;Pea & Mint Soup:400g,600g;Mushroom Soup:400g,600g"),
        "Wraps": (76, "Chicken Fajita Wrap:1pk,2pk;Falafel Wrap:1pk,2pk;Duck Hoisin Wrap:1pk,2pk;Chicken Caesar Wrap:1pk,2pk;Halloumi Wrap:1pk,2pk;Tuna Melt Wrap:1pk,2pk")}),
    "Seafood": ("Chilled", "Fresh Foods", {
        "Fish Fillets": (106, "Cod Fillets:2pk,4pk;Haddock Fillets:2pk,4pk;Salmon Fillets:2pk,4pk;Sea Bass Fillets:2pk,4pk;Sea Bream Fillets:2pk,4pk;Hake Fillets:2pk,4pk;Plaice Fillets:2pk,4pk;Trout Fillets:2pk,4pk"),
        "Prepared": (80, "Fishcakes:2pk,4pk;Salmon En Croute:1pk,2pk;Fish Pie Mix:320g,640g;Seafood Cocktail:200g,400g;Garlic Butter Prawns:150g,300g;Tuna Steaks:2pk,4pk"),
        "Shellfish": (82, "King Prawns:150g,300g;Cooked Prawns:150g,300g;Mussels:500g,1kg;Scallops:150g,300g;Crab Meat:100g,200g;Squid Rings:200g,400g"),
        "Smoked Fish": (77, "Smoked Salmon:100g,200g;Hot Smoked Salmon:120g,240g;Smoked Mackerel:200g,400g;Smoked Haddock:250g,500g;Kippers:2pk,4pk;Smoked Trout:100g,200g")}),
    "Frozen": ("Frozen", "Frozen", {
        "Frozen Fish": (68, "Battered Cod Fillets:2pk,4pk;Breaded Haddock:2pk,4pk;Salmon Fillets:2pk,4pk;Fish Fingers:10pk,20pk;King Prawns:200g,400g"),
        "Frozen Meals": (78, "Lasagne:400g,800g;Cottage Pie:400g,800g;Chicken Curry:400g,800g;Macaroni Cheese:400g,800g;Vegetable Chilli:400g,800g;Fish Pie:400g,800g"),
        "Frozen Meat": (76, "Beef Burgers:4pk,8pk;Chicken Nuggets:500g,1kg;Pork Sausages:12pk,20pk;Turkey Crown:1.5kg,2.5kg;Lamb Meatballs:400g,800g;Chicken Kievs:2pk,4pk"),
        "Frozen Pastry": (71, "Puff Pastry:375g,750g;Shortcrust Pastry:375g,750g;Filo Pastry:270g,540g;Sausage Rolls:6pk,12pk;Vegetable Samosas:8pk,16pk;Spring Rolls:12pk,24pk;Cheese Twists:8pk,16pk"),
        "Frozen Vegetables": (97, "Garden Peas:900g,1.8kg;Sweetcorn:500g,1kg;Broccoli Florets:750g,1.5kg;Mixed Vegetables:1kg,2kg;Spinach:450g,900g;Edamame Beans:400g,800g;Roast Potatoes:750g,1.5kg"),
        "Ice Cream": (95, "Vanilla Ice Cream:500ml,1L;Chocolate Ice Cream:500ml,1L;Strawberry Ice Cream:500ml,1L;Salted Caramel Ice Cream:500ml,1L;Mint Choc Chip Ice Cream:500ml,1L;Lemon Sorbet:500ml,1L;Raspberry Sorbet:500ml,1L")}),
}
VARIANTS = ["{b} {s}", "Organic {b} {s}", "{b} {s} Twin Pack", "{b} {s} Multi-Buy", "{b} {s} 2 for £5",
            "{b} {s} Family Pack", "{b} {s} Value Pack"]

rows = []
for category, (cluster, dept, groups) in CATALOGUE.items():
    for pg, (n, spec) in groups.items():
        combos = []
        for item in spec.split(";"):
            base, sizes = item.split(":")
            combos += [(base, s) for s in sizes.split(",")]
        names = [v.format(b=b, s=s) for v in VARIANTS for b, s in combos]
        assert len(names) >= n, (pg, len(names), n)
        for name in names[:n]:
            if category == "Frozen" and pg != "Ice Cream":
                name = "Frozen " + name
            rows.append({"category": category, "cluster": cluster, "super_group": dept, "product_group": pg,
                         "product": name})
dim_product = pd.DataFrame(rows)
assert len(dim_product) == N_UPCS, len(dim_product)
dupes = dim_product["product"].duplicated(keep=False)
dim_product.loc[dupes, "product"] = dim_product.loc[dupes, "product"] + " (" + dim_product.loc[dupes, "product_group"] + ")"
assert dim_product["product"].is_unique
dim_product = dim_product.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
dim_product["upc_idx"] = np.arange(N_UPCS)
dim_product["upc"] = [f"50600{i + 1:08d}" for i in range(N_UPCS)]
print(dim_product.groupby("category").size())

# COMMAND ----------

SUPPLIER_STEMS = ("Ashcombe,Brackenfield,Danesmoor,Elmstead,Fairholme,Greywell,Hartswood,Juniper Vale,Kestrel Hill,"
                  "Larchmere,Marlowe,Northcote,Oakhurst,Pennywell,Ravenswood,Stonebridge,Upton Hollow,Valewood,"
                  "Yewtree,Bramwell,Cresswell,Dunmore,Fernleigh,Glenmoor,Hollybank,Kingsmere,Linden,Millbrook,"
                  "Netherby,Orchard Grove,Redcliffe,Thistledown,Wildmoor,Alderbrook,Birchwood,Coppergate,Dovecote,"
                  "Eastholme,Foxley,Goldthorpe,Harrowfield,Ivydene,Kirkdale,Longmeadow,Moorcroft,Nettlecombe,"
                  "Oldcastle,Primrose Vale,Quarrydale,Rosewood,Saltmarsh,Tanglewood,Underhill,Westbury Farm,"
                  "Wychwood,Ashdown,Blackthorn,Cherryvale,Deepdale,Elderwood,Fairfield Grange,Greenacre,Heatherleigh,"
                  "Highmoor,Lowther,Meadowbrook,Northfield,Oakmere,Parkside,Riverford Vale,Sandhurst,Shepherd's Lea,"
                  "Silverdale,Southwick,Summerleaze,Swallowfield,Tarnside,Thornley,Whitecross,Willowmere,Windmill Hill,"
                  "Woodlands,Amberley,Barrowby,Castlemere,Dunstan,Edgecombe,Fennimore,Gorsefield,Hawthorne,"
                  "Kingfisher,Lavender Hill,Merrow,Newbold,Oxley,Pemberley,Quayside,Rookwood,Sedgefield,Teasel,"
                  "Upperton,Wren Valley,Yarrow,Ashbourne Mill,Bluebell,Clover,Dalesman,Evergreen,Fieldfare,Garnet,"
                  "Harvest Moon,Ingleby,Juniper,Kittiwake,Lapwing,Merlin,Nightingale,Owlsbrook,Plover,"
                  "Redwing,Skylark,Tamarisk,Wheatear").split(",")
assert len(SUPPLIER_STEMS) >= 120 and len(set(SUPPLIER_STEMS)) == len(SUPPLIER_STEMS)
SUPPLIER_KIND = {"Bakery": ["Bakehouse", "Bakery", "Patisserie"],
                 "Beverages": ["Drinks Co.", "Beverages", "Coffee Roasters", "Tea Company"],
                 "Grocery": ["Foods", "Pantry", "Mills"], "Snacks & Confectionery": ["Snacks", "Confectionery", "Chocolatiers"],
                 "Dairy": ["Dairies", "Creamery", "Cheesemakers"], "Deli & Cooked Meats": ["Deli Foods", "Charcuterie"],
                 "Desserts": ["Desserts", "Puddings"], "Fresh Meat": ["Meats", "Butchers", "Farms"],
                 "Fresh Produce": ["Growers", "Fresh Produce", "Orchards", "Farms"], "Ready Meals": ["Kitchen", "Cuisine"],
                 "Sandwiches & Food To Go": ["Food To Go", "Kitchen"], "Seafood": ["Seafoods", "Fisheries", "Smokehouse"],
                 "Frozen": ["Frozen Foods", "Freezer Foods"]}
cat_sizes = dim_product.groupby("category").size()
n_sup = (cat_sizes / cat_sizes.sum() * 120).round().astype(int)
n_sup.iloc[0] += 120 - n_sup.sum()
stems = list(rng.permutation(SUPPLIER_STEMS))
suppliers, s_i = [], 0
dim_product["supplier"] = ""
for category, k_sup in n_sup.items():
    kinds = SUPPLIER_KIND[category]
    names = []
    for j in range(k_sup):
        names.append(f"{stems[s_i]} {kinds[j % len(kinds)]}")
        s_i += 1
    share = rng.dirichlet(np.full(k_sup, 1.6))
    idx = rng.permutation(dim_product.index[dim_product.category == category].to_numpy())
    floor_n = 12                                                         # every supplier carries at least 12 lines
    counts = floor_n + np.floor(share * (len(idx) - floor_n * k_sup)).astype(int)
    counts[np.argmax(counts)] += len(idx) - counts.sum()
    start = 0
    for name, c in zip(names, counts):
        dim_product.loc[idx[start:start + c], "supplier"] = name
        start += c
    for name in names:
        suppliers.append({"supplier": name, "category_specialism": category})
dim_supplier = pd.DataFrame(suppliers)
rel = np.exp(rng.normal(0, 0.6, len(dim_supplier)))
rel[rng.choice(len(dim_supplier), 6, replace=False)] *= 2.2            # a handful of genuinely unreliable suppliers
dim_supplier["short_risk_index"] = np.round(rel / rel.mean(), 2)
dim_supplier["supplier_id"] = [f"SUP{i + 1:03d}" for i in range(len(dim_supplier))]
assert (dim_product.supplier != "").all() and dim_supplier.supplier.is_unique
SUP_ID = dict(zip(dim_supplier.supplier, dim_supplier.supplier_id))
print(len(dim_supplier), "suppliers")

# COMMAND ----------

# MAGIC %md ## The day's true state of every shelf (answer key)
# MAGIC Exact headline counts, realistic placement:
# MAGIC - planned range exits and market-wide scarcity concentrate on specific lines;
# MAGIC - a few unreliable suppliers and one problem depot drive shorts and delivery blocks;
# MAGIC - promotions drive under-forecasts;
# MAGIC - waste concentrates in short-life categories.

# COMMAND ----------

S = dim_store.sort_values("store_idx")
Pd = dim_product.sort_values("upc_idx")
store_w = np.clip(np.exp(rng.normal(0, 0.45, N_STORES)), 0.4, 2.0)       # store-level heterogeneity
depot_of_store = S.depot.to_numpy()
cat_of_upc = Pd.category.to_numpy()
name_of_upc = Pd["product"].to_numpy()
risk = dict(zip(dim_supplier.supplier, dim_supplier.short_risk_index))
sup_w = np.array([risk[s] for s in Pd.supplier])

ss_depot = {"Pennine DC": 1.4, "Westcountry DC": 1.3}
odb_depot = {"Merseyvale DC": 2.2, "Wealden DC": 1.5}
waste_cat = {"Sandwiches & Food To Go": 2.0, "Bakery": 1.6, "Seafood": 1.6, "Fresh Produce": 1.5, "Ready Meals": 1.4,
             "Fresh Meat": 1.3, "Desserts": 1.3, "Dairy": 1.2, "Deli & Cooked Meats": 1.2}
scarce_cat = {"Fresh Produce": 3.0, "Seafood": 2.0, "Fresh Meat": 1.5}

exit_upcs = rng.choice(N_UPCS, 360, replace=False)                       # planned range exits
p = np.array([scarce_cat.get(c, 1.0) for c in cat_of_upc]); p /= p.sum()
scarce_upcs = rng.choice(N_UPCS, 150, replace=False, p=p)                # market-wide shortages
promo = np.array([("2 for £5" in n) or ("Multi-Buy" in n) for n in name_of_upc])

u_kg = np.ones(N_UPCS); u_kg[exit_upcs] = 25.0
u_sc = np.ones(N_UPCS); u_sc[scarce_upcs] = 40.0
u_uf = np.where(promo, 3.0, 1.0)
u_wa = np.array([waste_cat.get(c, 0.4) for c in cat_of_upc])
s_sfa = store_w ** 1.2 * np.clip(np.exp(rng.normal(0, 0.35, N_STORES)), 0.5, 1.8)
s_ss = store_w * np.array([ss_depot.get(d, 1.0) for d in depot_of_store])
s_odb = store_w * np.array([odb_depot.get(d, 1.0) for d in depot_of_store])

WEIGHTS = {  # reason -> (store weights, upc weights)
    "KNOWN_GAP": (store_w, u_kg), "SUPPLIER_SHORT": (s_ss, sup_w), "UNDER_FORECAST": (store_w, u_uf),
    "ORDER_DELIVERY_BLOCK": (s_odb, np.ones(N_UPCS)), "SCARCITY": (store_w, u_sc),
    "STOCKFILE_ADJUSTMENT": (s_sfa, np.ones(N_UPCS)), "WASTE": (store_w, u_wa), "INVESTIGATE": (store_w, np.ones(N_UPCS)),
}

occupied = np.zeros(N_STORES * N_UPCS, dtype=bool)
parts = []
for reason, gaps, lows, space in TARGETS:
    sw, uw = WEIGHTS[reason]
    logw = (np.log(sw)[:, None] + np.log(uw)[None, :]).ravel()
    keys = logw - np.log(-np.log(rng.random(logw.size)))                 # Gumbel-top-k = weighted sampling w/o replacement
    keys[occupied] = -np.inf
    n = gaps + lows
    pick_ = np.sort(np.argpartition(-keys, n)[:n])     # argpartition's order varies by CPU; sorting makes every run identical
    occupied[pick_] = True
    pick_ = rng.permutation(pick_)
    issue = np.array(["GAP"] * gaps + ["LOW"] * lows)
    low = np.array([None] * gaps + ["SPACE_LOW"] * space + ["SALES_LOW"] * (lows - space), dtype=object)
    parts.append(pd.DataFrame({"cell": pick_, "issue": issue, "low_issue": low, "consensus_reason": reason}))
exc = pd.concat(parts, ignore_index=True)
exc["store_idx"] = exc.cell // N_UPCS
exc["upc_idx"] = exc.cell % N_UPCS

m = len(exc)
cr = exc.consensus_reason.to_numpy()
exc["supplier_short_type"] = ""
ss_idx = exc.index[cr == "SUPPLIER_SHORT"].to_numpy()
ss_idx = rng.permutation(ss_idx)
start = 0
for t, c in SS_TYPES:
    exc.loc[ss_idx[start:start + c], "supplier_short_type"] = t
    start += c


def whole(x, lo, hi):
    """Quantities are whole units at store-line scale (a line sells about 1.2 units a day)."""
    return np.clip(np.rint(x), lo, hi).astype(np.int32)


# Same random draws as the Larkwell demo, rescaled from depot-level to store-line quantities.
ss_q = whole(np.exp(rng.normal(np.log(68), 0.55, m)) / 6, 1, 36)
sc_q = whole(rng.uniform(5, 50, m) / 4, 1, 12)
wa_q = whole(rng.uniform(2, 30, m) / 4, 1, 8)
uf_q = whole(np.exp(rng.normal(np.log(8), 0.7, m)) / 2, 1, 30)
us_q = whole(rng.uniform(1, 20, m) / 3, 1, 7)
sf_q = whole(rng.uniform(1, 10, m), 1, 10)
exc["supplier_short_qty"] = np.where(cr == "SUPPLIER_SHORT", ss_q, 0)
exc["scarcity_qty"] = np.where(cr == "SCARCITY", sc_q, 0)
exc["waste_qty"] = np.where(cr == "WASTE", wa_q, 0)
exc["under_forecast_qty"] = np.where(cr == "UNDER_FORECAST", uf_q, 0)
exc["under_space_qty"] = np.where(exc.low_issue.to_numpy() == "SPACE_LOW", us_q, 0)
exc["stockfile_adjustment_qty"] = np.where(cr == "STOCKFILE_ADJUSTMENT", sf_q, 0)
print(exc.groupby(["consensus_reason", "issue"]).size().unstack())

# COMMAND ----------

# MAGIC %md ## Turn the true state into source-system signals
# MAGIC
# MAGIC Every product-location gets a stock-and-sales record. Each exception also gets the evidence for its true root cause.
# MAGIC Secondary evidence is added only where the root-cause rules would still reach the right answer:
# MAGIC a reason earlier in the cascade outranks it, or the shelf is healthy anyway.

# COMMAND ----------

r2 = np.random.default_rng(SEED + 1)      # second stream: feed detail (the placement above is unchanged)
N = N_STORES * N_UPCS
cell = exc.cell.to_numpy()
rank = np.zeros(N, np.int8)
rank[cell] = exc.consensus_reason.map(RANK).to_numpy()
iss = np.zeros(N, np.int8)
iss[cell] = np.where(exc.issue.to_numpy() == "GAP", 1, 2)
low_np = exc.low_issue.to_numpy()
lowt = np.zeros(N, np.int8)
lowt[cell] = np.where(low_np == "SPACE_LOW", 2, np.where(low_np == "SALES_LOW", 1, 0))


def per_cell(col):
    a = np.zeros(N, np.int32)
    a[cell] = exc[col].to_numpy()
    return a


q_ss, q_sc, q_wa, q_uf, q_us, q_sf = (per_cell(c) for c in ["supplier_short_qty", "scarcity_qty", "waste_qty",
                                                             "under_forecast_qty", "under_space_qty",
                                                             "stockfile_adjustment_qty"])

store_ids = S.store_id.to_numpy()
upcs = Pd.upc.to_numpy()
depot_id_of_store = S.depot.map(DEPOT_ID).to_numpy()
sup_id_of_upc = Pd.supplier.map(SUP_ID).to_numpy()


def ids(cells):
    return store_ids[cells // N_UPCS], upcs[cells % N_UPCS]


def pick(mask, n=None, p=None):
    idx = np.flatnonzero(mask)
    if p is not None:
        return idx[r2.random(idx.size) < p]
    return np.sort(r2.choice(idx, size=min(n, idx.size), replace=False))


def stamps(n, lo_h=2, hi_h=34):
    t = pd.Timestamp(BUSINESS_DATE) - pd.to_timedelta(r2.uniform(lo_h, hi_h, n), unit="h")
    return t.floor("min").strftime("%Y-%m-%dT%H:%M:00Z")


# --- Store stock and sales: every product-location -------------------------------------------------
FMT_VEL = {"Superstore": 1.6, "Local": 0.9, "Travel": 1.1, "Forecourt": 0.6, "Outlet": 0.5}
CAT_VEL = {"Fresh Produce": 1.5, "Dairy": 1.4, "Bakery": 1.3, "Sandwiches & Food To Go": 1.3, "Beverages": 1.1,
           "Ready Meals": 1.0, "Snacks & Confectionery": 1.0, "Fresh Meat": 0.9, "Grocery": 0.8,
           "Deli & Cooked Meats": 0.8, "Frozen": 0.7, "Desserts": 0.6, "Seafood": 0.6}
# Daily demand: median 0.7 units per line, scaled by store format and category. Across 900 stores x 6,000 lines
# that is a sales base of about GBP 9bn a year, the scale of a large UK food retailer.
mu = (np.log(0.7) + np.log(S.site_trading_group.map(FMT_VEL).to_numpy())[:, None]
      + np.log(Pd.category.map(CAT_VEL).to_numpy())[None, :]).ravel()
forecast = np.maximum(1, np.rint(np.exp(mu + r2.normal(0, 0.6, N)))).astype(np.int32)
pres_min = r2.integers(2, 7, N).astype(np.int32)
capacity = np.ceil(np.maximum(pres_min, forecast) * r2.uniform(1.3, 3.0, N)).astype(np.int32)
sales = np.rint(forecast * r2.uniform(0.55, 1.0, N)).astype(np.int32)
beat = r2.random(N) < 0.12                                               # some lines sell more than forecast
sales[beat] = forecast[beat] + r2.geometric(0.5, int(beat.sum())).astype(np.int32)
on_hand = pres_min + np.floor(r2.random(N) * (capacity - pres_min + 1)).astype(np.int32)
del mu

uf = rank == RANK["UNDER_FORECAST"]
forecast[uf] = np.maximum(forecast[uf], np.rint(q_uf[uf] * r2.uniform(0.5, 1.5, int(uf.sum()))).astype(np.int32))
gap, low = iss == 1, iss == 2
on_hand[gap] = 0
on_hand[low] = 1 + np.floor(r2.random(int(low.sum())) * (pres_min[low] - 1)).astype(np.int32)
sp, sl = lowt == 2, lowt == 1
forecast[sp] = np.maximum(forecast[sp], pres_min[sp] + q_us[sp])        # shelf can't hold a day's demand
capacity[sp] = forecast[sp] - q_us[sp]
capacity[sl] = np.maximum(capacity[sl], forecast[sl])
sales[uf] = forecast[uf] + q_uf[uf]                                      # under-forecast lines sell 1.7-3x forecast
inv = rank == RANK["INVESTIGATE"]
sales[inv] = np.minimum(sales[inv], forecast[inv])

exit_line = np.zeros(N_UPCS, bool)
exit_line[exit_upcs] = True
sell_down = (rank == 0) & np.tile(exit_line, N_STORES) & (r2.random(N) < 0.35)   # exiting lines still on shelf
exiting = (rank == RANK["KNOWN_GAP"]) | sell_down

# --- Deliveries: supplier shorts (evidence), plus normal and noisy lines ---------------------------
SHORT_REASONS = np.array([t for t, _ in SS_TYPES])
ss_type_of = pd.Series(exc.supplier_short_type.to_numpy(), index=cell)
deliv = []


def delivery_lines(cells, ordered, delivered, reason, kind):
    sid, upc = ids(cells)
    deliv.append(pd.DataFrame({
        "business_date": BUSINESS_DATE, "store_id": sid, "upc": upc,
        "depot_id": depot_id_of_store[cells // N_UPCS], "supplier_id": sup_id_of_upc[cells % N_UPCS],
        "ordered_units": ordered, "delivered_units": delivered, "short_reason": reason,
        "delivered_at": stamps(len(cells), 6, 30), "_kind": kind}))


c = np.flatnonzero(rank == RANK["SUPPLIER_SHORT"])
d = r2.integers(0, 12, c.size)
delivery_lines(c, d + q_ss[c], d, ss_type_of.loc[c].to_numpy(), "truth_short")
c = np.concatenate([pick(rank == RANK["KNOWN_GAP"], p=0.15), pick(rank == RANK["SCARCITY"], p=0.35)])
d = r2.integers(0, 12, c.size)
delivery_lines(c, d + r2.integers(1, 24, c.size), d,
               np.where(rank[c] == RANK["SCARCITY"], "RAW_MATERIAL_SHORTAGE", r2.choice(SHORT_REASONS, c.size)),
               "secondary_short")
c = pick(rank == 0, n=25_000)
d = r2.integers(3, 24, c.size)
delivery_lines(c, d + r2.integers(1, 12, c.size), d, r2.choice(SHORT_REASONS, c.size), "short_on_healthy_shelf")
c = pick(np.ones(N, bool), n=300_000)
d = r2.integers(3, 25, c.size)
delivery_lines(c, d, d, None, "complete")
c = pick(np.ones(N, bool), n=400)
d = r2.integers(3, 25, c.size)
delivery_lines(c, d, d + r2.integers(1, 6, c.size), None, "over_delivered")
deliveries = pd.concat(deliv, ignore_index=True)
deliveries.insert(0, "delivery_line_id", [f"DL{BUSINESS_DATE.replace('-', '')}{i:07d}" for i in range(len(deliveries))])
# Malformed records the pipeline must reject. Negative deliveries sit on lines whose true cause is later in the
# cascade, so letting them through would wrongly turn them into supplier shorts.
bad = []
c = pick(rank >= RANK["ORDER_DELIVERY_BLOCK"], n=40)
sid, upc = ids(c)
bad.append(pd.DataFrame({"store_id": sid, "upc": upc, "ordered_units": 20, "delivered_units": -5, "_kind": "bad_negative"}))
c = pick(np.ones(N, bool), n=40)
sid, upc = ids(c)
bad.append(pd.DataFrame({"store_id": None, "upc": upc, "ordered_units": 12, "delivered_units": 0, "_kind": "bad_no_store"}))
c = pick(np.ones(N, bool), n=40)
sid, upc = ids(c)
bad.append(pd.DataFrame({"store_id": sid, "upc": [u[:7] + "XX" + u[9:] for u in upc], "ordered_units": 12,
                         "delivered_units": 0, "_kind": "bad_upc"}))
bad = pd.concat(bad, ignore_index=True)
bad["business_date"] = BUSINESS_DATE
bad["depot_id"], bad["supplier_id"], bad["short_reason"] = "D01", "SUP001", "DEPOT_SHORT"
bad["delivered_at"] = stamps(len(bad), 6, 30)
bad.insert(0, "delivery_line_id", [f"DLX{BUSINESS_DATE.replace('-', '')}{i:05d}" for i in range(len(bad))])
resent = deliveries.sample(frac=0.01, random_state=SEED)                # depot system re-sent ~1% of lines
deliveries = pd.concat([deliveries, bad, resent], ignore_index=True).sample(frac=1.0, random_state=SEED + 2)
print("deliveries:", deliveries._kind.value_counts().to_dict(), "| re-sent duplicates:", len(resent))

# --- Order events: delivery blocks (evidence), plus blocks that were later released -----------------
BLOCK_REASONS = np.array(["Depot capacity cap", "Vehicle cancelled", "Order system hold", "Missed delivery slot",
                          "Order quantity cap"])
ev = []


def order_events(cells, statuses, kind):
    sid, upc = ids(cells)
    n = len(cells)
    oid = np.array([f"PO{BUSINESS_DATE.replace('-', '')}{kind[:2].upper()}{i:06d}" for i in range(n)])
    t1 = pd.Timestamp(BUSINESS_DATE) - pd.to_timedelta(r2.uniform(20, 40, n), unit="h")
    for step, status in enumerate(statuses):
        keep = np.ones(n, bool) if step == 0 else status[1]
        st = status if step == 0 else status[0]
        ts = (t1 + pd.to_timedelta(6 * step, unit="h"))[keep]
        ev.append(pd.DataFrame({
            "order_id": oid[keep], "store_id": sid[keep], "upc": upc[keep], "status": st,
            "block_reason": r2.choice(BLOCK_REASONS, int(keep.sum())) if st == "BLOCKED" else None,
            "event_ts": ts.floor("min").strftime("%Y-%m-%dT%H:%M:00Z"), "_kind": kind}))


c = np.flatnonzero(rank == RANK["ORDER_DELIVERY_BLOCK"])
order_events(c, ["BLOCKED", ("CANCELLED", r2.random(c.size) < 0.2)], "truth_block")
c = pick((rank >= 1) & (rank < RANK["ORDER_DELIVERY_BLOCK"]), p=0.10)
order_events(c, ["BLOCKED"], "secondary_block")
c = pick(rank == 0, n=20_000)
order_events(c, ["BLOCKED"], "open_block_healthy_shelf")
c = np.concatenate([pick(rank > RANK["ORDER_DELIVERY_BLOCK"], p=0.08), pick(rank == 0, n=20_000)])
order_events(c, ["BLOCKED", ("RELEASED", np.ones(c.size, bool))], "released_block")
order_events_df = pd.concat(ev, ignore_index=True)
order_events_df.insert(0, "event_id", [f"OE{i:07d}" for i in range(len(order_events_df))])
order_events_df["business_date"] = BUSINESS_DATE
print("order events:", order_events_df._kind.value_counts().to_dict())

# --- Stock counts: phantom stock (evidence), plus found stock and transfers --------------------------
cnt = []


def counts(cells, units, reason, kind):
    sid, upc = ids(cells)
    cnt.append(pd.DataFrame({"business_date": BUSINESS_DATE, "store_id": sid, "upc": upc,
                             "adjustment_reason": reason, "adjustment_units": units,
                             "counted_at": stamps(len(cells), 2, 20), "_kind": kind}))


c = np.flatnonzero(rank == RANK["STOCKFILE_ADJUSTMENT"])
counts(c, -q_sf[c], "STOCK_COUNT", "truth_phantom")
c = pick((rank >= 1) & (rank < RANK["STOCKFILE_ADJUSTMENT"]), p=0.08)
counts(c, -r2.integers(1, 8, c.size), "STOCK_COUNT", "secondary_phantom")
c = pick(rank > RANK["STOCKFILE_ADJUSTMENT"], p=0.08)
counts(c, r2.integers(1, 6, c.size), "STOCK_COUNT", "found_stock")
c = pick(rank > RANK["STOCKFILE_ADJUSTMENT"], p=0.05)
counts(c, -r2.integers(1, 6, c.size), "TRANSFER_OUT", "transfer_out")
c = pick(rank == 0, n=40_000)
counts(c, r2.choice([-1, 1], c.size) * r2.integers(1, 6, c.size), "STOCK_COUNT", "count_healthy_shelf")
stock_counts = pd.concat(cnt, ignore_index=True)
stock_counts.insert(0, "count_id", [f"SC{i:07d}" for i in range(len(stock_counts))])
print("stock counts:", stock_counts._kind.value_counts().to_dict())

# --- Waste: waste-driven gaps (evidence), plus everyday waste ---------------------------------------
WASTE_REASONS = np.array(["OUT_OF_DATE", "DAMAGED", "QUALITY"])
wst = []


def waste(cells, units, kind):
    sid, upc = ids(cells)
    wst.append(pd.DataFrame({"business_date": BUSINESS_DATE, "store_id": sid, "upc": upc, "waste_units": units,
                             "waste_reason": r2.choice(WASTE_REASONS, len(cells)),
                             "recorded_at": stamps(len(cells), 2, 26), "_kind": kind}))


c = np.flatnonzero(rank == RANK["WASTE"])
split = (r2.random(c.size) < 0.35) & (q_wa[c] >= 2)                       # some waste is recorded in two goes
first = np.where(split, 1 + np.floor(r2.random(c.size) * (q_wa[c] - 1)).astype(np.int32), q_wa[c])
waste(c, first, "truth_waste")
waste(c[split], (q_wa[c] - first)[split], "truth_waste_second_entry")
c = pick((rank >= 1) & (rank < RANK["WASTE"]), p=0.10)
waste(c, r2.integers(1, 5, c.size), "secondary_waste")
c = np.flatnonzero((rank == 0) & (r2.random(N) < 0.028 * np.tile(u_wa, N_STORES)))
waste(c, r2.integers(1, 4, c.size), "waste_healthy_shelf")
waste_df = pd.concat(wst, ignore_index=True)
waste_df.insert(0, "waste_id", [f"WE{i:07d}" for i in range(len(waste_df))])
print("waste:", waste_df._kind.value_counts().to_dict())

# --- Allocations: market shortages (evidence), plus full and promotional allocations -----------------
scarce_line = np.zeros(N_UPCS, bool)
scarce_line[scarce_upcs] = True
on_scarce = np.tile(scarce_line, N_STORES)
alc = []


def allocations(cells, requested, allocated, reason, kind):
    sid, upc = ids(cells)
    alc.append(pd.DataFrame({"business_date": BUSINESS_DATE, "store_id": sid, "upc": upc,
                             "allocation_reason": reason, "requested_units": requested,
                             "allocated_units": allocated, "_kind": kind}))


c = np.flatnonzero(rank == RANK["SCARCITY"])
a = r2.integers(0, 12, c.size)
allocations(c, a + q_sc[c], a, "MARKET_SHORTAGE", "truth_shortage")
c = pick((rank == RANK["KNOWN_GAP"]) & on_scarce, p=0.4)
a = r2.integers(0, 12, c.size)
allocations(c, a + r2.integers(1, 12, c.size), a, "MARKET_SHORTAGE", "secondary_shortage")
c = pick((rank == 0) & on_scarce, p=0.6)
a = r2.integers(3, 24, c.size)
allocations(c, a + r2.integers(1, 6, c.size), a, "MARKET_SHORTAGE", "shortage_healthy_shelf")
c = pick((rank > RANK["SCARCITY"]) & on_scarce, p=1.0)
a = r2.integers(3, 24, c.size)
allocations(c, a, a, "MARKET_SHORTAGE", "allocated_in_full")
c = pick((rank > RANK["SCARCITY"]) & ~on_scarce, n=3_000)
a = r2.integers(3, 24, c.size)
allocations(c, a + r2.integers(1, 6, c.size), a, "PROMO_ALLOCATION", "promo_cap")
allocations_df = pd.concat(alc, ignore_index=True)
allocations_df.insert(0, "allocation_id", [f"AL{i:07d}" for i in range(len(allocations_df))])
print("allocations:", allocations_df._kind.value_counts().to_dict())

# COMMAND ----------

# MAGIC %md ## Master data
# MAGIC Prices, shelf lives and service levels are synthetic. Twenty-five products are re-issued with a later price change,
# MAGIC so the pipeline has to keep the latest version.

# COMMAND ----------

PRICE = {"Bakery": (0.9, 3.5), "Beverages": (0.8, 6.0), "Grocery": (0.8, 5.0), "Snacks & Confectionery": (0.6, 4.0),
         "Dairy": (0.9, 5.0), "Deli & Cooked Meats": (1.5, 5.0), "Desserts": (2.0, 6.0), "Fresh Meat": (3.0, 12.0),
         "Fresh Produce": (0.5, 4.0), "Ready Meals": (3.0, 8.0), "Sandwiches & Food To Go": (2.0, 5.0),
         "Seafood": (3.0, 12.0), "Frozen": (2.0, 7.0)}
LIFE = {"Bakery": (2, 5), "Beverages": (90, 365), "Grocery": (180, 540), "Snacks & Confectionery": (90, 365),
        "Dairy": (7, 21), "Deli & Cooked Meats": (7, 21), "Desserts": (4, 10), "Fresh Meat": (3, 8),
        "Fresh Produce": (3, 7), "Ready Meals": (4, 7), "Sandwiches & Food To Go": (1, 3), "Seafood": (2, 4),
        "Frozen": (180, 365)}
lo = Pd.category.map(lambda x: PRICE[x][0]).to_numpy()
hi = Pd.category.map(lambda x: PRICE[x][1]).to_numpy()
price = np.round(np.round((lo + (hi - lo) * r2.beta(2, 3, N_UPCS)) * 20) / 20 - 0.01, 2)   # e.g. 2.49, 3.99
life = np.array([r2.integers(LIFE[x][0], LIFE[x][1] + 1) for x in Pd.category])
products = pd.DataFrame({
    "upc": Pd.upc.to_numpy(), "product_name": Pd["product"].to_numpy(), "category": Pd.category.to_numpy(),
    "department": Pd.super_group.to_numpy(), "product_group": Pd.product_group.to_numpy(),
    "temperature_cluster": Pd.cluster.to_numpy(), "supplier_id": sup_id_of_upc, "unit_price_gbp": price,
    "shelf_life_days": life, "case_size": r2.choice([6, 8, 12], N_UPCS), "effective_date": "2026-09-01"})
reissued = products.sample(25, random_state=SEED).copy()
reissued["unit_price_gbp"] = np.round(reissued.unit_price_gbp + 0.20, 2)
reissued["effective_date"] = "2026-10-14"
products = pd.concat([products, reissued], ignore_index=True)
daily_sales = float((forecast.reshape(N_STORES, N_UPCS) * price[None, :]).sum())
print(f"Sales base: GBP {daily_sales / 1e6:.1f}m of forecast demand a day, about GBP {daily_sales * 364 / 1e9:.1f}bn a year")

stores_df = pd.DataFrame({
    "store_id": S.store_id.to_numpy(), "store_name": S.store.to_numpy(), "division": S.division.to_numpy(),
    "area": S.area.to_numpy(), "store_format": S.site_trading_group.to_numpy(),
    "ownership": S.business_scope.to_numpy(), "depot_id": depot_id_of_store, "effective_date": "2026-09-01"})
suppliers_df = pd.DataFrame({
    "supplier_id": dim_supplier.supplier_id, "supplier_name": dim_supplier.supplier,
    "category_specialism": dim_supplier.category_specialism,
    "contracted_service_level_pct": r2.choice([97.5, 98.0, 98.5, 99.0], len(dim_supplier)),
    "effective_date": "2026-09-01"})
depots_df = pd.DataFrame({"depot_id": [DEPOT_ID[n] for n, _ in DEPOTS], "depot_name": [n for n, _ in DEPOTS],
                          "region_served": [r for _, r in DEPOTS], "effective_date": "2026-09-01"})

# COMMAND ----------

# MAGIC %md ## Write the files

# COMMAND ----------

manifest = {"business_date": BUSINESS_DATE, "generated_by": "data/01_land_raw_feeds", "seed": SEED, "feeds": {}}


def folder(feed):
    path = f"{LANDING}/{feed}/{BUSINESS_DATE}"
    os.makedirs(path, exist_ok=True)
    for f in os.listdir(path):                                           # re-running a day replaces its files
        os.remove(f"{path}/{f}")
    return path


def record(feed, files, n_rows):
    manifest["feeds"][feed] = {"files": files, "rows": int(n_rows)}
    print(f"{feed:16s} {n_rows:>10,} rows in {len(files)} file(s)")


for feed, df in [("store_master", stores_df), ("product_master", products), ("supplier_master", suppliers_df),
                 ("depot_master", depots_df)]:
    path = folder(feed)
    name = f"{feed}_{BUSINESS_DATE}.csv"
    df.to_csv(f"{path}/{name}", index=False)
    record(feed, [name], len(df))

path, files, total = folder("store_stock"), [], 0
for area, grp in S.groupby("area", sort=False):
    st = grp.store_idx.to_numpy()
    cells = (st[:, None] * N_UPCS + np.arange(N_UPCS)[None, :]).ravel()
    chunk = pd.DataFrame({
        "business_date": BUSINESS_DATE, "store_id": np.repeat(store_ids[st], N_UPCS), "upc": np.tile(upcs, st.size),
        "range_status": np.where(exiting[cells], "EXITING", "ACTIVE"), "on_hand_units": on_hand[cells],
        "presentation_min_units": pres_min[cells], "shelf_capacity_units": capacity[cells],
        "forecast_units": forecast[cells], "sales_units": sales[cells]})
    name = f"store_stock_{BUSINESS_DATE}_{re.sub('[^a-z]+', '_', area.lower()).strip('_')}.csv.gz"
    chunk.to_csv(f"{path}/{name}", index=False, compression="gzip")
    files.append(name)
    total += len(chunk)
record("store_stock", files, total)

for feed, df, n_files in [("deliveries", deliveries, 4), ("order_events", order_events_df, 2),
                          ("stock_counts", stock_counts, 1), ("waste", waste_df, 2), ("allocations", allocations_df, 1)]:
    path, files = folder(feed), []
    out = df.drop(columns=["_kind"])
    for i, part in enumerate(np.array_split(np.arange(len(out)), n_files)):
        name = f"{feed}_{BUSINESS_DATE}_part{i + 1}.json"
        out.iloc[part].to_json(f"{path}/{name}", orient="records", lines=True)
        files.append(name)
    record(feed, files, len(out))

os.makedirs(f"{LANDING}/_manifests", exist_ok=True)
with open(f"{LANDING}/_manifests/{BUSINESS_DATE}.json", "w") as f:
    json.dump(manifest, f, indent=2)

# COMMAND ----------

# MAGIC %md ## Answer key (for testing only; the pipeline never reads it)

# COMMAND ----------

os.makedirs(ANSWER_KEY, exist_ok=True)
key = exc.assign(store_id=store_ids[exc.store_idx], upc=upcs[exc.upc_idx])[
    ["store_id", "upc", "issue", "low_issue", "consensus_reason", "supplier_short_type", "supplier_short_qty",
     "scarcity_qty", "waste_qty", "under_forecast_qty", "under_space_qty", "stockfile_adjustment_qty"]]
key.to_parquet(f"{ANSWER_KEY}/exceptions.parquet", index=False)
expected = {
    "product_locations": N, "stores": N_STORES, "lines": N_UPCS, "gaps": int((exc.issue == "GAP").sum()),
    "lows": int((exc.issue == "LOW").sum()), "sales_lows": int((exc.low_issue == "SALES_LOW").sum()),
    "space_lows": int((exc.low_issue == "SPACE_LOW").sum()),
    "owned_product_locations": int((S.business_scope == "Owned").sum() * N_UPCS),
    "reason_mix": {r: g + lw for r, g, lw, _ in TARGETS},
    "supplier_short_types": exc.loc[cr == "SUPPLIER_SHORT"].supplier_short_type.value_counts().to_dict(),
    "malformed_delivery_lines": int(len(bad)), "duplicate_delivery_lines": int(len(resent)),
    "daily_forecast_sales_gbp": round(daily_sales, 2),
}
with open(f"{ANSWER_KEY}/expected_counts.json", "w") as f:
    json.dump(expected, f, indent=2)
assert expected["gaps"] == 133765 and expected["lows"] == 72069
assert expected["sales_lows"] == 36099 and expected["space_lows"] == 35970 and expected["owned_product_locations"] == 4908000
print(json.dumps(expected, indent=2))

# COMMAND ----------

# MAGIC %md ## Check the signals reproduce the answer key
# MAGIC A pandas re-implementation of the root-cause rules, run on the generated records before anything reaches the
# MAGIC lakehouse. The Lakeflow pipeline implements the same rules in SQL and is tested against the answer key separately.

# COMMAND ----------

valid = deliveries[deliveries.store_id.notna() & deliveries.upc.str.fullmatch(r"\d{13}")
                   & (deliveries.ordered_units >= 0) & (deliveries.delivered_units >= 0)].drop_duplicates("delivery_line_id")
sh = valid[valid.delivered_units < valid.ordered_units]
e_ss = (sh.ordered_units - sh.delivered_units).groupby([sh.store_id, sh.upc]).sum()
lastev = order_events_df.sort_values("event_ts").groupby("order_id").tail(1)
blk = lastev[lastev.status.isin(["BLOCKED", "CANCELLED"])]
e_ob = blk.groupby([blk.store_id, blk.upc]).size()
ph = stock_counts[(stock_counts.adjustment_reason == "STOCK_COUNT") & (stock_counts.adjustment_units < 0)]
e_sf = (-ph.adjustment_units).groupby([ph.store_id, ph.upc]).sum()
e_wa = waste_df.waste_units.groupby([waste_df.store_id, waste_df.upc]).sum()
cut = allocations_df[(allocations_df.allocation_reason == "MARKET_SHORTAGE")
                     & (allocations_df.allocated_units < allocations_df.requested_units)]
e_sc = (cut.requested_units - cut.allocated_units).groupby([cut.store_id, cut.upc]).sum()

k = key.set_index(["store_id", "upc"])
ci = k.index
pos = np.array([int(s[1:]) - 1 for s in ci.get_level_values(0)]) * N_UPCS + Pd.set_index("upc").upc_idx.loc[ci.get_level_values(1)].to_numpy()
ev_tbl = pd.DataFrame({
    "KNOWN_GAP": exiting[pos], "SCARCITY": e_sc.reindex(ci).fillna(0).to_numpy() > 0,
    "SUPPLIER_SHORT": e_ss.reindex(ci).fillna(0).to_numpy() > 0, "ORDER_DELIVERY_BLOCK": e_ob.reindex(ci).fillna(0).to_numpy() > 0,
    "STOCKFILE_ADJUSTMENT": e_sf.reindex(ci).fillna(0).to_numpy() > 0, "WASTE": e_wa.reindex(ci).fillna(0).to_numpy() > 0,
    "UNDER_FORECAST": sales[pos] > forecast[pos]}, index=ci)
derived = np.select([ev_tbl[r].to_numpy() for r in CASCADE[:-1]], CASCADE[:-1], "INVESTIGATE")
mismatch = int((derived != k.consensus_reason.to_numpy()).sum())
print("exceptions:", len(k), "| derived root cause matches the answer key:", len(k) - mismatch, "| mismatches:", mismatch)
print("exceptions with more than one kind of evidence:", int((ev_tbl.sum(axis=1) > 1).sum()))
assert mismatch == 0
status = np.where(on_hand == 0, 1, np.where(on_hand < pres_min, 2, 0))           # the status rules, on every shelf
assert (status == iss).all(), "shelf status from stock levels must match the answer key"
low_type = np.where(capacity < forecast, 2, 1)
assert (low_type[iss == 2] == lowt[iss == 2]).all(), "low type from shelf capacity must match the answer key"
print("Raw feeds landed and self-check passed.")
