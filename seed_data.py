"""Seed data: top Utah companies across industries."""

from database import execute

UTAH_COMPANIES = [
    # ── Technology ──────────────────────────────────────────────────────
    {"name": "Qualtrics", "website": "https://www.qualtrics.com", "industry": "Technology", "city": "Provo"},
    {"name": "Pluralsight", "website": "https://www.pluralsight.com", "industry": "Technology", "city": "Draper"},
    {"name": "Domo", "website": "https://www.domo.com", "industry": "Technology", "city": "American Fork"},
    {"name": "Lucid Software", "website": "https://www.lucid.co", "industry": "Technology", "city": "South Jordan"},
    {"name": "Podium", "website": "https://www.podium.com", "industry": "Technology", "city": "Lehi"},
    {"name": "MX Technologies", "website": "https://www.mx.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Weave", "website": "https://www.getweave.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Ivanti", "website": "https://www.ivanti.com", "industry": "Technology", "city": "South Jordan"},
    {"name": "BambooHR", "website": "https://www.bamboohr.com", "industry": "Technology", "city": "Lindon"},
    {"name": "Instructure", "website": "https://www.instructure.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Entrata", "website": "https://www.entrata.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Vivint Smart Home", "website": "https://www.vivint.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Adobe (Utah)", "website": "https://www.adobe.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Microsoft (Utah)", "website": "https://www.microsoft.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Oracle (Utah)", "website": "https://www.oracle.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Workday (Utah)", "website": "https://www.workday.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Overstock.com", "website": "https://www.overstock.com", "industry": "Technology", "city": "Midvale"},
    {"name": "DigiCert", "website": "https://www.digicert.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Veritone (Utah)", "website": "https://www.veritone.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Carta (Utah)", "website": "https://www.carta.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Ancestry", "website": "https://www.ancestry.com", "industry": "Technology", "city": "Lehi"},
    {"name": "1-800 Contacts", "website": "https://www.1800contacts.com", "industry": "Technology", "city": "Draper"},
    {"name": "Sorenson Communications", "website": "https://www.sorenson.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Lendio", "website": "https://www.lendio.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Jive Communications", "website": "https://www.jive.com", "industry": "Technology", "city": "Orem"},
    {"name": "InsideSales.com (XANT)", "website": "https://www.insidesales.com", "industry": "Technology", "city": "Provo"},
    {"name": "Chatbooks", "website": "https://www.chatbooks.com", "industry": "Technology", "city": "Provo"},
    {"name": "Collective Medical", "website": "https://www.collectivemedical.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Nearside (formerly Lili)", "website": "https://www.nearside.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Filevine", "website": "https://www.filevine.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Neighbor", "website": "https://www.neighbor.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Owlet", "website": "https://www.owletcare.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Pattern", "website": "https://www.pattern.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Simplus (now Infosys)", "website": "https://www.simplus.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Impartner", "website": "https://www.impartner.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Kenect", "website": "https://www.kenect.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Conga", "website": "https://www.conga.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Verisk (Utah)", "website": "https://www.verisk.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Canopy", "website": "https://www.getcanopy.com", "industry": "Technology", "city": "Draper"},
    {"name": "Grow Inc.", "website": "https://www.grow.com", "industry": "Technology", "city": "Provo"},
    {"name": "Divvy (now BILL)", "website": "https://www.divvy.co", "industry": "Technology", "city": "Draper"},
    {"name": "Nuvi (now Reputation)", "website": "https://www.reputation.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Classy Llama", "website": "https://www.classyllama.com", "industry": "Technology", "city": "Springville"},
    {"name": "Galileo Financial Technologies", "website": "https://www.galileo-ft.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Zonos", "website": "https://www.zonos.com", "industry": "Technology", "city": "St. George"},
    {"name": "Gabb Wireless", "website": "https://www.gabb.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Taxbit", "website": "https://www.taxbit.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Movemedical", "website": "https://www.movemedical.com", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Clozd", "website": "https://www.clozd.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Pricebook Digital", "website": "https://www.pricebook.co", "industry": "Technology", "city": "Salt Lake City"},
    {"name": "Nectar HR", "website": "https://www.nectarhr.com", "industry": "Technology", "city": "Orem"},
    {"name": "Fortem Technologies", "website": "https://www.fortemtech.com", "industry": "Technology", "city": "Pleasant Grove"},

    # ── Healthcare ──────────────────────────────────────────────────────
    {"name": "Intermountain Health", "website": "https://intermountainhealthcare.org", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "University of Utah Health", "website": "https://healthcare.utah.edu", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Recursion Pharmaceuticals", "website": "https://www.recursion.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Health Catalyst", "website": "https://www.healthcatalyst.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "CHG Healthcare", "website": "https://www.chghealthcare.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "ARUP Laboratories", "website": "https://www.aruplab.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "BioFire Diagnostics", "website": "https://www.biofiredx.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Merit Medical Systems", "website": "https://www.merit.com", "industry": "Healthcare", "city": "South Jordan"},
    {"name": "Nelson Laboratories", "website": "https://www.nelsonlabs.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "MountainStar Healthcare", "website": "https://mountainstar.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Myriad Genetics", "website": "https://www.myriad.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Steward Health Care (Utah)", "website": "https://www.steward.org", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Revere Health", "website": "https://www.reverehealth.com", "industry": "Healthcare", "city": "Provo"},
    {"name": "Ogden Regional Medical Center", "website": "https://www.ogdenregional.com", "industry": "Healthcare", "city": "Ogden"},
    {"name": "Primary Children's Hospital", "website": "https://www.primarychildrens.org", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "HealthEquity", "website": "https://www.healthequity.com", "industry": "Healthcare", "city": "Draper"},
    {"name": "Theralink Technologies", "website": "https://www.theralink.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "4Life Research", "website": "https://www.4life.com", "industry": "Healthcare", "city": "Sandy"},
    {"name": "Mortenson Dental Partners", "website": "https://www.mortensondentalpartners.com", "industry": "Healthcare", "city": "Salt Lake City"},

    # ── Finance / Banking / Insurance ───────────────────────────────────
    {"name": "Zions Bancorporation", "website": "https://www.zionsbancorporation.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Goldman Sachs (SLC)", "website": "https://www.goldmansachs.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Ally Financial (SLC)", "website": "https://www.ally.com", "industry": "Finance", "city": "Sandy"},
    {"name": "Mountain America Credit Union", "website": "https://www.macu.com", "industry": "Finance", "city": "Sandy"},
    {"name": "America First Credit Union", "website": "https://www.americafirst.com", "industry": "Finance", "city": "Ogden"},
    {"name": "University Federal Credit Union", "website": "https://www.ucreditu.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Discover Financial Services (Utah)", "website": "https://www.discover.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Select Portfolio Servicing", "website": "https://www.spservicing.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Fidelity Investments (Utah)", "website": "https://www.fidelity.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Charles Schwab (Utah)", "website": "https://www.schwab.com", "industry": "Finance", "city": "Lone Peak"},
    {"name": "SoFi (Utah)", "website": "https://www.sofi.com", "industry": "Finance", "city": "Cottonwood Heights"},
    {"name": "WCF Insurance", "website": "https://www.wcf.com", "industry": "Insurance", "city": "Sandy"},
    {"name": "Progressive Insurance (Utah)", "website": "https://www.progressive.com", "industry": "Insurance", "city": "Salt Lake City"},
    {"name": "SelectHealth", "website": "https://www.selecthealth.org", "industry": "Insurance", "city": "Murray"},
    {"name": "EMI Health", "website": "https://www.emihealth.com", "industry": "Insurance", "city": "Salt Lake City"},
    {"name": "Workers Compensation Fund", "website": "https://www.wcf.com", "industry": "Insurance", "city": "Sandy"},
    {"name": "USAA (Utah)", "website": "https://www.usaa.com", "industry": "Finance", "city": "Highland"},
    {"name": "TAB Bank", "website": "https://www.tabbank.com", "industry": "Finance", "city": "Ogden"},
    {"name": "Celtic Bank", "website": "https://www.celticbank.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Nelnet (Utah)", "website": "https://www.nelnet.com", "industry": "Finance", "city": "Salt Lake City"},

    # ── Aerospace & Defense ─────────────────────────────────────────────
    {"name": "Northrop Grumman (Utah)", "website": "https://www.northropgrumman.com", "industry": "Aerospace & Defense", "city": "Roy"},
    {"name": "L3Harris Technologies (Utah)", "website": "https://www.l3harris.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "Hill Air Force Base (civilian)", "website": "https://www.hill.af.mil", "industry": "Aerospace & Defense", "city": "Ogden"},
    {"name": "Boeing (Utah)", "website": "https://www.boeing.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "Lockheed Martin (Utah)", "website": "https://www.lockheedmartin.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "BAE Systems (Utah)", "website": "https://www.baesystems.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "General Dynamics (Utah)", "website": "https://www.gd.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "Raytheon (Utah)", "website": "https://www.rtx.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "Williams International", "website": "https://www.williams-int.com", "industry": "Aerospace & Defense", "city": "Ogden"},
    {"name": "Parker Hannifin (Utah)", "website": "https://www.parker.com", "industry": "Aerospace & Defense", "city": "Ogden"},
    {"name": "KIHOMAC", "website": "https://www.kihomac.com", "industry": "Aerospace & Defense", "city": "Layton"},
    {"name": "Janicki Industries (Utah)", "website": "https://www.janicki.com", "industry": "Aerospace & Defense", "city": "Layton"},
    {"name": "General Atomics (Utah)", "website": "https://www.ga.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "Orbital ATK (Northrop Grumman)", "website": "https://www.northropgrumman.com", "industry": "Aerospace & Defense", "city": "Promontory"},

    # ── Airlines / Transportation ───────────────────────────────────────
    {"name": "SkyWest Airlines", "website": "https://www.skywest.com", "industry": "Airlines", "city": "St. George"},
    {"name": "Breeze Airways", "website": "https://www.flybreeze.com", "industry": "Airlines", "city": "Cottonwood Heights"},
    {"name": "UTA (Utah Transit Authority)", "website": "https://www.rideuta.com", "industry": "Transportation", "city": "Salt Lake City"},

    # ── Education ───────────────────────────────────────────────────────
    {"name": "Brigham Young University", "website": "https://www.byu.edu", "industry": "Education", "city": "Provo"},
    {"name": "University of Utah", "website": "https://www.utah.edu", "industry": "Education", "city": "Salt Lake City"},
    {"name": "Utah State University", "website": "https://www.usu.edu", "industry": "Education", "city": "Logan"},
    {"name": "Weber State University", "website": "https://www.weber.edu", "industry": "Education", "city": "Ogden"},
    {"name": "Utah Valley University", "website": "https://www.uvu.edu", "industry": "Education", "city": "Orem"},
    {"name": "Southern Utah University", "website": "https://www.suu.edu", "industry": "Education", "city": "Cedar City"},
    {"name": "Dixie State University", "website": "https://www.dixie.edu", "industry": "Education", "city": "St. George"},
    {"name": "Snow College", "website": "https://www.snow.edu", "industry": "Education", "city": "Ephraim"},
    {"name": "Salt Lake Community College", "website": "https://www.slcc.edu", "industry": "Education", "city": "Salt Lake City"},
    {"name": "Western Governors University", "website": "https://www.wgu.edu", "industry": "Education", "city": "Millcreek"},
    {"name": "Granite School District", "website": "https://www.graniteschools.org", "industry": "Education", "city": "Salt Lake City"},
    {"name": "Alpine School District", "website": "https://www.alpineschools.org", "industry": "Education", "city": "American Fork"},
    {"name": "Davis School District", "website": "https://www.davis.k12.ut.us", "industry": "Education", "city": "Farmington"},
    {"name": "Jordan School District", "website": "https://www.jordandistrict.org", "industry": "Education", "city": "Sandy"},
    {"name": "Canyons School District", "website": "https://www.canyonsdistrict.org", "industry": "Education", "city": "Sandy"},

    # ── Consumer Goods / Direct Sales ───────────────────────────────────
    {"name": "Nu Skin Enterprises", "website": "https://www.nuskin.com", "industry": "Consumer Goods", "city": "Provo"},
    {"name": "Traeger Grills", "website": "https://www.traeger.com", "industry": "Consumer Goods", "city": "Salt Lake City"},
    {"name": "Purple Innovation", "website": "https://www.purple.com", "industry": "Consumer Goods", "city": "Lehi"},
    {"name": "doTERRA", "website": "https://www.doterra.com", "industry": "Consumer Goods", "city": "Pleasant Grove"},
    {"name": "USANA Health Sciences", "website": "https://www.usana.com", "industry": "Consumer Goods", "city": "Salt Lake City"},
    {"name": "Young Living Essential Oils", "website": "https://www.youngliving.com", "industry": "Consumer Goods", "city": "Lehi"},
    {"name": "Nature's Sunshine Products", "website": "https://www.naturessunshine.com", "industry": "Consumer Goods", "city": "Lehi"},
    {"name": "LifeVantage", "website": "https://www.lifevantage.com", "industry": "Consumer Goods", "city": "Salt Lake City"},
    {"name": "MonaVie (ARIIX)", "website": "https://www.ariix.com", "industry": "Consumer Goods", "city": "Lehi"},
    {"name": "Just Ingredients", "website": "https://www.justingredients.us", "industry": "Consumer Goods", "city": "Lindon"},
    {"name": "Xango", "website": "https://www.xango.com", "industry": "Consumer Goods", "city": "Lehi"},

    # ── Retail / E-Commerce ─────────────────────────────────────────────
    {"name": "Cotopaxi", "website": "https://www.cotopaxi.com", "industry": "Retail", "city": "Salt Lake City"},
    {"name": "Backcountry.com", "website": "https://www.backcountry.com", "industry": "Retail", "city": "Park City"},
    {"name": "Black Diamond Equipment", "website": "https://www.blackdiamondequipment.com", "industry": "Retail", "city": "Salt Lake City"},
    {"name": "Skullcandy", "website": "https://www.skullcandy.com", "industry": "Retail", "city": "Park City"},
    {"name": "KURU Footwear", "website": "https://www.kurufootwear.com", "industry": "Retail", "city": "Salt Lake City"},
    {"name": "Pura", "website": "https://www.trypura.com", "industry": "Retail", "city": "Lehi"},
    {"name": "Nena & Co.", "website": "https://www.nenaandco.com", "industry": "Retail", "city": "Provo"},
    {"name": "Walmart (Utah operations)", "website": "https://www.walmart.com", "industry": "Retail", "city": "Salt Lake City"},
    {"name": "Costco (Utah operations)", "website": "https://www.costco.com", "industry": "Retail", "city": "Salt Lake City"},
    {"name": "Smith's Food & Drug (Kroger)", "website": "https://www.smithsfoodanddrug.com", "industry": "Retail", "city": "Salt Lake City"},

    # ── Outdoor Recreation ──────────────────────────────────────────────
    {"name": "Klymit", "website": "https://www.klymit.com", "industry": "Outdoor Recreation", "city": "Kaysville"},
    {"name": "Amer Sports (Utah)", "website": "https://www.amersports.com", "industry": "Outdoor Recreation", "city": "Ogden"},
    {"name": "Rossignol (Utah)", "website": "https://www.rossignol.com", "industry": "Outdoor Recreation", "city": "Park City"},
    {"name": "Petzl America", "website": "https://www.petzl.com", "industry": "Outdoor Recreation", "city": "Salt Lake City"},
    {"name": "Goal Zero", "website": "https://www.goalzero.com", "industry": "Outdoor Recreation", "city": "Bluffdale"},
    {"name": "ENVE Composites", "website": "https://www.enve.com", "industry": "Outdoor Recreation", "city": "Ogden"},
    {"name": "Nikon Sport Optics (Utah)", "website": "https://www.nikonusa.com", "industry": "Outdoor Recreation", "city": "West Valley City"},

    # ── Real Estate / Property Management ───────────────────────────────
    {"name": "Extra Space Storage", "website": "https://www.extraspace.com", "industry": "Real Estate", "city": "Salt Lake City"},
    {"name": "Clyde Companies", "website": "https://www.clydecompanies.com", "industry": "Real Estate", "city": "Orem"},
    {"name": "The Boyer Company", "website": "https://www.boyercompany.com", "industry": "Real Estate", "city": "Salt Lake City"},
    {"name": "Woodbury Corporation", "website": "https://www.woodburycorp.com", "industry": "Real Estate", "city": "Salt Lake City"},
    {"name": "Ivory Homes", "website": "https://www.ivoryhomes.com", "industry": "Real Estate", "city": "Salt Lake City"},
    {"name": "Holmes Homes", "website": "https://www.holmeshomes.com", "industry": "Real Estate", "city": "Layton"},

    # ── Construction / Engineering ──────────────────────────────────────
    {"name": "Big-D Construction", "website": "https://www.big-d.com", "industry": "Construction", "city": "Salt Lake City"},
    {"name": "Okland Construction", "website": "https://www.okland.com", "industry": "Construction", "city": "Salt Lake City"},
    {"name": "Wadman Corporation", "website": "https://www.wadman.com", "industry": "Construction", "city": "Ogden"},
    {"name": "Layton Construction", "website": "https://www.laytonconstruction.com", "industry": "Construction", "city": "Sandy"},
    {"name": "Jacobsen Construction", "website": "https://www.jacobsenconstruction.com", "industry": "Construction", "city": "Salt Lake City"},
    {"name": "R&O Construction", "website": "https://www.randoco.com", "industry": "Construction", "city": "Ogden"},
    {"name": "Staker Parson Companies", "website": "https://www.stakerparson.com", "industry": "Construction", "city": "Ogden"},
    {"name": "Geneva Rock Products", "website": "https://www.genevarock.com", "industry": "Construction", "city": "Orem"},
    {"name": "Sundt Construction (Utah)", "website": "https://www.sundt.com", "industry": "Construction", "city": "Salt Lake City"},
    {"name": "Hale Construction", "website": "https://www.haleconstruction.com", "industry": "Construction", "city": "Orem"},

    # ── Manufacturing ───────────────────────────────────────────────────
    {"name": "Lifetime Products", "website": "https://www.lifetime.com", "industry": "Manufacturing", "city": "Clearfield"},
    {"name": "Autoliv (Utah)", "website": "https://www.autoliv.com", "industry": "Manufacturing", "city": "Ogden"},
    {"name": "Moog Inc. (Utah)", "website": "https://www.moog.com", "industry": "Manufacturing", "city": "Salt Lake City"},
    {"name": "Conestoga Wood Specialties", "website": "https://www.conestogawood.com", "industry": "Manufacturing", "city": "Salt Lake City"},
    {"name": "Packsize International", "website": "https://www.packsize.com", "industry": "Manufacturing", "city": "Salt Lake City"},
    {"name": "Sportsman's Warehouse", "website": "https://www.sportsmans.com", "industry": "Retail", "city": "West Jordan"},
    {"name": "Futura Industries", "website": "https://www.futuraind.com", "industry": "Manufacturing", "city": "Clearfield"},
    {"name": "Icon Health & Fitness", "website": "https://www.iconfitness.com", "industry": "Manufacturing", "city": "Logan"},
    {"name": "MarketStar", "website": "https://www.marketstar.com", "industry": "Professional Services", "city": "Ogden"},

    # ── Energy / Utilities ──────────────────────────────────────────────
    {"name": "PacifiCorp (Rocky Mountain Power)", "website": "https://www.rockymountainpower.net", "industry": "Energy", "city": "Salt Lake City"},
    {"name": "Dominion Energy (Questar)", "website": "https://www.dominionenergy.com", "industry": "Energy", "city": "Salt Lake City"},
    {"name": "Vivint Solar (Sunrun)", "website": "https://www.sunrun.com", "industry": "Energy", "city": "Lehi"},
    {"name": "Rio Tinto Kennecott", "website": "https://www.riotinto.com", "industry": "Energy", "city": "Magna"},
    {"name": "Ambia Energy", "website": "https://www.ambiaservices.com", "industry": "Energy", "city": "Orem"},
    {"name": "Energy Solutions", "website": "https://www.energysolutions.com", "industry": "Energy", "city": "Salt Lake City"},
    {"name": "Holly Refining (HollyFrontier)", "website": "https://www.hfrefineries.com", "industry": "Energy", "city": "Woods Cross"},

    # ── Food & Beverage ─────────────────────────────────────────────────
    {"name": "Lehi Mills", "website": "https://www.lehimills.com", "industry": "Food & Beverage", "city": "Lehi"},
    {"name": "Swig", "website": "https://www.swig.com", "industry": "Food & Beverage", "city": "St. George"},
    {"name": "Crumbl Cookies", "website": "https://www.crumblcookies.com", "industry": "Food & Beverage", "city": "Lindon"},
    {"name": "Five Star Franchising", "website": "https://www.fivestarfranchising.com", "industry": "Food & Beverage", "city": "Springville"},
    {"name": "Kodiak Cakes", "website": "https://www.kodiakcakes.com", "industry": "Food & Beverage", "city": "Park City"},
    {"name": "Mrs. Cavanaugh's Chocolates", "website": "https://www.mrscavanaughs.com", "industry": "Food & Beverage", "city": "North Salt Lake"},
    {"name": "Soelberg's Market", "website": "https://www.soelbergsmarket.com", "industry": "Food & Beverage", "city": "Heber City"},
    {"name": "Associated Food Stores", "website": "https://www.afstores.com", "industry": "Food & Beverage", "city": "Salt Lake City"},
    {"name": "Nicholas & Company", "website": "https://www.nicholasandco.com", "industry": "Food & Beverage", "city": "Salt Lake City"},
    {"name": "Maverik", "website": "https://www.maverik.com", "industry": "Retail", "city": "North Salt Lake"},

    # ── Hospitality / Travel ────────────────────────────────────────────
    {"name": "Vail Resorts (Park City)", "website": "https://www.vailresorts.com", "industry": "Hospitality", "city": "Park City"},
    {"name": "Snowbird Ski Resort", "website": "https://www.snowbird.com", "industry": "Hospitality", "city": "Snowbird"},
    {"name": "Deer Valley Resort", "website": "https://www.deervalley.com", "industry": "Hospitality", "city": "Park City"},
    {"name": "Alta Ski Area", "website": "https://www.alta.com", "industry": "Hospitality", "city": "Alta"},
    {"name": "Brighton Resort", "website": "https://www.brightonresort.com", "industry": "Hospitality", "city": "Brighton"},
    {"name": "La Caille", "website": "https://www.lacaille.com", "industry": "Hospitality", "city": "Sandy"},
    {"name": "Sundance Mountain Resort", "website": "https://www.sundanceresort.com", "industry": "Hospitality", "city": "Sundance"},
    {"name": "Grand America Hotel", "website": "https://www.grandamerica.com", "industry": "Hospitality", "city": "Salt Lake City"},

    # ── Automotive / Dealerships ────────────────────────────────────────
    {"name": "Larry H. Miller Dealerships", "website": "https://www.lhm.com", "industry": "Automotive", "city": "Sandy"},
    {"name": "Ken Garff Automotive Group", "website": "https://www.kengarff.com", "industry": "Automotive", "city": "Salt Lake City"},
    {"name": "Mark Miller Auto Group", "website": "https://www.markmiller.com", "industry": "Automotive", "city": "Salt Lake City"},
    {"name": "Young Automotive Group", "website": "https://www.youngautomotive.com", "industry": "Automotive", "city": "Layton"},

    # ── Professional Services / Staffing ────────────────────────────────
    {"name": "Robert Half (Utah)", "website": "https://www.roberthalf.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Teleperformance (Utah)", "website": "https://www.teleperformance.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Deloitte (Utah)", "website": "https://www.deloitte.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Ernst & Young (Utah)", "website": "https://www.ey.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "PwC (Utah)", "website": "https://www.pwc.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "KPMG (Utah)", "website": "https://www.kpmg.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Tanner LLC", "website": "https://www.tannerco.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Kirton McConkie", "website": "https://www.kirtonmcconkie.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Stoel Rives", "website": "https://www.stoel.com", "industry": "Professional Services", "city": "Salt Lake City"},
    {"name": "Parsons Behle & Latimer", "website": "https://www.parsonsbehle.com", "industry": "Professional Services", "city": "Salt Lake City"},

    # ── Government ──────────────────────────────────────────────────────
    {"name": "State of Utah", "website": "https://www.utah.gov", "industry": "Government", "city": "Salt Lake City"},
    {"name": "Salt Lake County", "website": "https://slco.org", "industry": "Government", "city": "Salt Lake City"},
    {"name": "Salt Lake City Corporation", "website": "https://www.slc.gov", "industry": "Government", "city": "Salt Lake City"},
    {"name": "Internal Revenue Service (Utah)", "website": "https://www.irs.gov", "industry": "Government", "city": "Ogden"},
    {"name": "National Security Agency (Utah)", "website": "https://www.nsa.gov", "industry": "Government", "city": "Bluffdale"},

    # ── Logistics / Trucking ────────────────────────────────────────────
    {"name": "C.R. England Trucking", "website": "https://www.crengland.com", "industry": "Logistics", "city": "Salt Lake City"},
    {"name": "FedEx Ground (Utah Hub)", "website": "https://www.fedex.com", "industry": "Logistics", "city": "Salt Lake City"},
    {"name": "UPS (Utah operations)", "website": "https://www.ups.com", "industry": "Logistics", "city": "Salt Lake City"},
    {"name": "XPO Logistics (Utah)", "website": "https://www.xpo.com", "industry": "Logistics", "city": "Salt Lake City"},
    {"name": "Amazon (Utah fulfillment)", "website": "https://www.amazon.com", "industry": "Logistics", "city": "Salt Lake City"},

    # ── Media / Communications ──────────────────────────────────────────
    {"name": "KSL Broadcasting", "website": "https://www.ksl.com", "industry": "Media", "city": "Salt Lake City"},
    {"name": "The Salt Lake Tribune", "website": "https://www.sltrib.com", "industry": "Media", "city": "Salt Lake City"},
    {"name": "Deseret News", "website": "https://www.deseret.com", "industry": "Media", "city": "Salt Lake City"},
    {"name": "Bonneville International", "website": "https://www.bonneville.com", "industry": "Media", "city": "Salt Lake City"},

    # ── Nonprofit / Religious ───────────────────────────────────────────
    {"name": "The Church of Jesus Christ of Latter-day Saints", "website": "https://www.churchofjesuschrist.org", "industry": "Nonprofit / Religious", "city": "Salt Lake City"},
    {"name": "LDS Charities", "website": "https://www.latterdaysaintcharities.org", "industry": "Nonprofit / Religious", "city": "Salt Lake City"},
    {"name": "Deseret Industries", "website": "https://www.deseretindustries.org", "industry": "Nonprofit / Religious", "city": "Salt Lake City"},

    # ── Telecommunications ──────────────────────────────────────────────
    {"name": "UTOPIA Fiber", "website": "https://www.utopiafiber.com", "industry": "Telecommunications", "city": "Orem"},
    {"name": "CenturyLink (Lumen, Utah)", "website": "https://www.lumen.com", "industry": "Telecommunications", "city": "Salt Lake City"},
    {"name": "T-Mobile (Utah)", "website": "https://www.t-mobile.com", "industry": "Telecommunications", "city": "Salt Lake City"},

    # ── Sports / Entertainment ──────────────────────────────────────────
    {"name": "Smith Entertainment Group (Utah Jazz)", "website": "https://www.nba.com/jazz", "industry": "Sports / Entertainment", "city": "Salt Lake City"},
    {"name": "Real Salt Lake", "website": "https://www.rsl.com", "industry": "Sports / Entertainment", "city": "Sandy"},
    {"name": "CircusTrix (Sky Zone)", "website": "https://www.skyzone.com", "industry": "Sports / Entertainment", "city": "Provo"},
    {"name": "Loveland Living Planet Aquarium", "website": "https://www.thelivingplanet.com", "industry": "Sports / Entertainment", "city": "Draper"},
    {"name": "Evermore Park", "website": "https://www.evermore.com", "industry": "Sports / Entertainment", "city": "Pleasant Grove"},
]


def seed_companies():
    existing = execute("SELECT COUNT(*) FROM companies")
    if existing.rows[0][0] > 0:
        return existing.rows[0][0]

    for company in UTAH_COMPANIES:
        execute(
            "INSERT INTO companies (name, website, industry, city) VALUES (?, ?, ?, ?)",
            [company["name"], company["website"], company["industry"], company["city"]],
        )
    return len(UTAH_COMPANIES)
