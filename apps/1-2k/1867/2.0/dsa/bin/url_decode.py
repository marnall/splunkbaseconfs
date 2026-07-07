"""
This script takes search values from the search. It then looks for a variable called
'url='. With that URL we then break appart the url into it's URI and domain. Based
on domain we then call additional functions to break down the search. 

To power this code run the following search in splunk:
tid=262 | urldecode | top raw_url
or
tid=262 | urldecode 

tid=262 | urldecode | search url_is_ip=False | chart values(url_uri) by url_whole_domain
tid=262 | urldecode | search url_is_ip=False | chart values(url_uri) by url_base_domain

throw away the images and swf, flv, js files

tid=262 | urldecode | search url_is_ip=False | search NOT url_uri=*.js | search NOT url_uri=*swf | search NOT url_uri=*swf* | search NOT url_uri=*.flv | search NOT url_uri=*png | search NOT url_uri=*css | search NOT url_uri=*gif | search NOT url_uri=*xml | chart values(url_uri) by url_base_domain

NOTE: 
Script returns data when it's done with all data. So search is SLOW.
Recommend setting search time to "last 5 minutes" to get reasable response

You will get the following new variables:
  url_search_type
  url_search
  
with debug enabled you get these additional variables
  raw_url
  url_whole_domain
  url_uri

This code written by: Jeremiah Alfrey jalfrey@sonicwall.com
"""
import re,sys,time, splunk.Intersplunk
debug = True

def find_image(url_uri):
  image_list = ['.gif', '.jpg', '.png', '.ico']
  is_image = False
  for image_type in image_list:
    if image_type in url_uri:
      is_image = True

  return is_image
  

def craigslist(whole_domain, uri_stem, result):

  """
  tid=262 craigslist | urldecode | search NOT url_type="image" | search cl_uri_root="search" | top limit=50 url_search_string
  This search gives you the top things people are searching for in craiglist
  """
  if debug:
    result['url_process_function'] = 'craigslist'

  cl_sales_dict = {
  "ato":  "antiques by owner",
  "atd": "antiques by dealer",
  "ata": "antiques by owner and dealer",
  "ppo":  "appliances by owner",
  "ppd": "appliances by dealer",
  "ppa": "appliances by owner and dealer",
  "aro":  "arts & crafts by owner",
  "ard": "arts & crafts by dealer",
  "ara": "arts & crafts by owner and dealer",
  "sno":  "atvs",
  "snd": "atvs",
  "sna": "atvs",
  "pto":  "auto parts by owner",
  "ptd": "auto parts by dealer",
  "pta": "auto parts by owner and dealer",
  "cto":  "cars & trucks by owner",
  "ctd": "cars & trucks by dealer",
  "cta": "cars & trucks by owner + dealer",
  "bao":  "baby & kid stuff by owner",
  "bad": "baby & kid stuff by dealer",
  "baa": "baby & kid stuff by owner and dealer",
  "bar":  "barter",
  "bio":  "bicycles by owner",
  "bid": "bicycles by dealer",
  "bia": "bicycles by owner and dealer",
  "boo":  "boats by owner",
  "bod": "boats by dealer",
  "boa": "boats by owner and dealer",
  "bko":  "books & magazines by owner",
  "bkd": "books & magazines by dealer",
  "bka": "books & magazines by owner and dealer",
  "bfo":  "business by owner",
  "bfd": "business by dealer",
  "bfa": "business by owner and dealer",
  "emo":  "cd / dvds / vhs by owner",
  "emd": "cd / dvds / vhs by dealer",
  "ema": "cd / dvds / vhs by owner and dealer",
  "moo":  "cell phones by owner",
  "mod": "cell phones by dealer",
  "moa": "cell phones by owner and dealer",
  "clo":  "clothing & accessories by owner",
  "cld": "clothing & accessories by dealer",
  "cla": "clothing & accessories by owner and dealer",
  "cbo":  "collectibles by owner",
  "cbd": "collectibles by dealer",
  "cba": "collectibles by owner and dealer",
  "syo":  "computers by owner",
  "syd": "computers by dealer",
  "sya": "computers by owner and dealer",
  "elo":  "electronics by owner",
  "eld": "electronics by dealer",
  "ela": "electronics by owner and dealer",
  "gro":  "farm & garden by owner",
  "grd": "farm & garden by dealer",
  "gra": "farm & garden by owner and dealer",
  "zip":  "free stuff",
  "fuo":  "furniture by owner",
  "fud": "furniture by dealer",
  "fua": "furniture by owner and dealer",
  "gms":  "garage & moving sales",
  "foo":  "general for sale by owner",
  "fod": "general for sale by dealer",
  "foa": "general for sale by owner and dealer",
  "hao":  "health and beauty by owner",
  "had": "health and beauty by dealer",
  "haa": "health and beauty by owner and dealer",
  "hvo":  "heavy equipment by owner",
  "hvd": "heavy equipment by dealer",
  "hva": "heavy equipment by owner and dealer",
  "hso":  "household items by owner",
  "hsd": "household items by dealer",
  "hsa": "household items by owner and dealer",
  "jwo":  "jewelery by owner",
  "jwd": "jewelery by dealer",
  "jwa": "jewelery by owner and dealer",
  "mao":  "materials by owner",
  "mad": "materials by dealer",
  "maa": "materials by owner and dealer",
  "mpo":  "motorcycle parts & accessories by owner",
  "mpd": "motorcycle parts & accessories by dealer",
  "mpa": "motorcycle parts & accessories by owner and dealer",
  "mco":  "motorcycles/scooters by owner",
  "mcd": "motorcycles/scooters by dealer",
  "mca": "motorcycles/scooters by owner and dealer",
  "mso":  "musical instruments by owner",
  "msd": "musical instruments by dealer",
  "msa": "musical instruments by owner and dealer",
  "pho":  "photo/video by owner",
  "phd": "photo/video by dealer",
  "pha": "photo/video by owner and dealer",
  "rvo":  "recreational vehicles by owner",
  "rvd": "recreational vehicles by dealer",
  "rva": "recreational vehicles by owner and dealer",
  "sgo":  "sporting goods by owner",
  "sgd": "sporting goods by dealer",
  "sga": "sporting goods by owner and dealer",
  "tio":  "tickets by owner",
  "tid": "tickets by dealer",
  "tia": "tickets by owner and dealer",
  "tlo":  "tools by owner",
  "tld": "tools by dealer",
  "tla": "tools by owner and dealer",
  "tao":  "toys & games by owner",
  "tad": "toys & games by dealer",
  "taa": "toys & games by owner and dealer",
  "vgo":  "video gaming by owner",
  "vgd": "video gaming by dealer",
  "vga": "video gaming by owner and dealer",
  "wao":  "wanted by owner",
  "wad": "wanted by dealer",
  "waa": "wanted by owner and dealer"}
  
  cl_region_dict = {
  'www':'global',
  'sfbay':{'sfc':'san francisco', 
  'sby':'south bay',
  'eby':'east bay',
  'pen':'peninsula',
  'nby':'north bay',
  'scz':'santa cruz'},
  'auburn':'auburn',
  'bham':'birmingham',
  'dothan':'dothan',
  'shoals':'florence / muscle shoals',
  'gadsden':'gadsden-anniston',
  'huntsville':'huntsville / decatur',
  'mobile':'mobile',
  'montgomery':'montgomery',
  'tuscaloosa':'tuscaloosa',
  'anchorage':'anchorage / mat-su',
  'fairbanks':'fairbanks',
  'kenai':'kenai peninsula',
  'juneau':'southeast alaska',
  'flagstaff':'flagstaff / sedona',
  'mohave':'mohave county',
  'phoenix':{
  '':'phoenix',
  'cph':'central/south phx',
  'evl':'east valley',
  'nph':'phx north',
  'wvl':'west valley'},
  'prescott':'prescott',
  'showlow':'show low',
  'sierravista':'sierra vista',
  'tucson':'tucson',
  'yuma':'yuma',
  'fayar':'fayetteville ',
  'fortsmith':'fort smith',
  'jonesboro':'jonesboro',
  'littlerock':'little rock',
  'texarkana':'texarkana',
  'bakersfield':'bakersfield',
  'chico':'chico',
  'fresno':'fresno / madera',
  'goldcountry':'gold country',
  'hanford':'hanford-corcoran',
  'humboldt':'humboldt county',
  'imperial':'imperial county',
  'inlandempire':'inland empire',
  'losangeles':{
  '':'los angeles',
  'wst':'westside-southbay',
  'sfv':'SF valley',
  'lac':'central LA',
  'sgv':'san gabriel valley',
  'lgb':'long beach/562',
  'ant':'antelope valley'},
  'mendocino':'mendocino county',
  'merced':'merced',
  'modesto':'modesto',
  'monterey':'monterey bay',
  'orangecounty':'orange county',
  'palmsprings':'palm springs',
  'redding':'redding',
  'sacramento':'sacramento',
  'sandiego':{
  '':'san diego',
  'csd':'city of san diego',
  'nsd':'north SD county',
  'esd':'east SD county',
  'ssd':'south SD county'},
  'sfbay':'san francisco bay area',
  'slo':'san luis obispo',
  'santabarbara':'santa barbara',
  'santamaria':'santa maria',
  'siskiyou':'siskiyou county',
  'stockton':'stockton',
  'susanville':'susanville',
  'ventura':'ventura county',
  'visalia':'visalia-tulare',
  'yubasutter':'yuba-sutter',
  'boulder':'boulder',
  'cosprings':'colorado springs',
  'denver':'denver',
  'eastco':'eastern CO',
  'fortcollins':'fort collins / north CO',
  'rockies':'high rockies',
  'pueblo':'pueblo',
  'westslope':'western slope',
  'newlondon':'eastern CT',
  'hartford':'hartford',
  'newhaven':'new haven',
  'nwct':'northwest CT',
  'delaware':'delaware',
  'washingtondc':{
  '':'washington DC',
  'doc':'district of columbia',
  'nva':'northern virginia',
  'mld':'maryland'},
  'daytona':'daytona beach',
  'keys':'florida keys',
  'fortlauderdale':'fort lauderdale',
  'fortmyers':{
  '':'fortmyers',
  'lee':'lee county',
  'chl':'charlotte co',
  'col':'collier co'},
  'gainesville':'gainesville',
  'cfl':'heartland florida',
  'jacksonville':'jacksonville',
  'lakeland':'lakeland',
  'lakecity':'north central FL',
  'ocala':'ocala',
  'okaloosa':'okaloosa / walton',
  'orlando':'orlando',
  'panamacity':'panama city',
  'pensacola':'pensacola',
  'sarasota':'sarasota-bradenton',
  'miami':{
  '':'miami',
  'mdc':'miami/dade',
  'brw':'broward county',
  'pbc':'palm beach co'},
  'spacecoast':'space coast',
  'staugustine':'st augustine',
  'tallahassee':'tallahassee',
  'tampa':{
  '':'tampa',
  'hdo':'hernando co',
  'hil':'hillsborough co',
  'psc':'pasco co',
  'pnl':'pinellas co'},
  'treasure':'treasure coast',
  'westpalmbeach':'west palm beach',
  'albanyga':'albany ',
  'athensga':'athens',
  'atlanta':{
  '':'atlanta',
  'atl':'atlanta', 
  'nat':'otp north', 
  'eat':'otp east', 
  'sat':'otp south', 
  'wat':'otp west'},
  'augusta':'augusta',
  'brunswick':'brunswick',
  'columbusga':'columbus ',
  'macon':'macon / warner robins',
  'nwga':'northwest GA',
  'savannah':'savannah / hinesville',
  'statesboro':'statesboro',
  'valdosta':'valdosta',
  'honolulu':{
  '':'hawaii',
  'oah':'oahu',
  'big':'big island',
  'mau':'maui',
  'kau':'kauai',
  'mol':'molokai'},
  'boise':'boise',
  'eastidaho':'east idaho',
  'lewiston':'lewiston / clarkston',
  'twinfalls':'twin falls',
  'bn':'bloomington-normal',
  'chambana':'champaign urbana',
  'chicago':{
  '':'chicago',
  'chc':'city of chicago',
  'nch':'north chicagoland',
  'wcl':'west chicagoland',
  'sox':'south chicagoland',
  'nwi':'northwest indiana',
  'nwc':'northwest suburbs'},
  'decatur':'decatur',
  'lasalle':'la salle co',
  'mattoon':'mattoon-charleston',
  'peoria':'peoria',
  'rockford':'rockford',
  'carbondale':'southern illinois',
  'springfieldil':'springfield ',
  'quincy':'western IL',
  'bloomington':'bloomington',
  'evansville':'evansville',
  'fortwayne':'fort wayne',
  'indianapolis':'indianapolis',
  'kokomo':'kokomo',
  'tippecanoe':'lafayette / west lafayette',
  'muncie':'muncie / anderson',
  'richmondin':'richmond ',
  'southbend':'south bend / michiana',
  'terrehaute':'terre haute',
  'ames':'ames',
  'cedarrapids':'cedar rapids',
  'desmoines':'des moines',
  'dubuque':'dubuque',
  'fortdodge':'fort dodge',
  'iowacity':'iowa city',
  'masoncity':'mason city',
  'quadcities':'quad cities',
  'siouxcity':'sioux city',
  'ottumwa':'southeast IA',
  'waterloo':'waterloo / cedar falls',
  'lawrence':'lawrence',
  'ksu':'manhattan',
  'nwks':'northwest KS',
  'salina':'salina',
  'seks':'southeast KS',
  'swks':'southwest KS',
  'topeka':'topeka',
  'wichita':'wichita',
  'bgky':'bowling green',
  'eastky':'eastern kentucky',
  'lexington':'lexington',
  'louisville':'louisville',
  'owensboro':'owensboro',
  'westky':'western KY',
  'batonrouge':'baton rouge',
  'cenla':'central louisiana',
  'houma':'houma',
  'lafayette':'lafayette',
  'lakecharles':'lake charles',
  'monroe':'monroe',
  'neworleans':'new orleans',
  'shreveport':'shreveport',
  'maine':'maine',
  'annapolis':'annapolis',
  'baltimore':'baltimore',
  'easternshore':'eastern shore',
  'frederick':'frederick',
  'smd':'southern maryland',
  'westmd':'western maryland',
  'boston':{
  '':'boston',
  'gbs':'boston/camb/brook',
  'nwb':'northwest/merrimack',
  'bmw':'metro west',
  'nos':'north shore',
  'sob':'south shore'},
  'capecod':'cape cod / islands',
  'southcoast':'south coast',
  'westernmass':'western massachusetts',
  'worcester':'worcester / central MA',
  'annarbor':'ann arbor',
  'battlecreek':'battle creek',
  'centralmich':'central michigan',
  'detroit':{
  '':'detroit',
  'mcb':'macomb co',
  'wyn':'wayne co',
  'okl':'oakland co'},
  'flint':'flint',
  'grandrapids':'grand rapids',
  'holland':'holland',
  'jxn':'jackson ',
  'kalamazoo':'kalamazoo',
  'lansing':'lansing',
  'monroemi':'monroe ',
  'muskegon':'muskegon',
  'nmi':'northern michigan',
  'porthuron':'port huron',
  'saginaw':'saginaw-midland-baycity',
  'swmi':'southwest michigan',
  'thumb':'the thumb',
  'up':'upper peninsula',
  'bemidji':'bemidji',
  'brainerd':'brainerd',
  'duluth':'duluth / superior',
  'mankato':'mankato',
  'minneapolis':{
  '':'minneapolis',
  'hnp':'hennepin co',
  'ram':'ramsey co',
  'ank':'anok/chis/isa',
  'wsh':'washington/WI',
  'dak':'dakota/scott',
  'csw':'carv/sher/wri'},
  'rmn':'rochester ',
  'marshall':'southwest MN',
  'stcloud':'st cloud',
  'gulfport':'gulfport / biloxi',
  'hattiesburg':'hattiesburg',
  'jackson':'jackson',
  'meridian':'meridian',
  'northmiss':'north mississippi',
  'natchez':'southwest MS',
  'columbiamo':'columbia / jeff city',
  'joplin':'joplin',
  'kansascity':'kansas city',
  'kirksville':'kirksville',
  'loz':'lake of the ozarks',
  'semo':'southeast missouri',
  'springfield':'springfield',
  'stjoseph':'st joseph',
  'stlouis':'st louis',
  'billings':'billings',
  'bozeman':'bozeman',
  'butte':'butte',
  'greatfalls':'great falls',
  'helena':'helena',
  'kalispell':'kalispell',
  'missoula':'missoula',
  'montana':'eastern montana',
  'grandisland':'grand island',
  'lincoln':'lincoln',
  'northplatte':'north platte',
  'omaha':'omaha / council bluffs',
  'scottsbluff':'scottsbluff / panhandle',
  'elko':'elko',
  'lasvegas':'las vegas',
  'reno':'reno / tahoe',
  'nh':'new hampshire',
  'cnj':'central NJ',
  'jerseyshore':'jersey shore',
  'newjersey':'north jersey',
  'southjersey':'south jersey',
  'albuquerque':'albuquerque',
  'clovis':'clovis / portales',
  'farmington':'farmington',
  'lascruces':'las cruces',
  'roswell':'roswell / carlsbad',
  'santafe':'santa fe / taos',
  'albany':'albany',
  'binghamton':'binghamton',
  'buffalo':'buffalo',
  'catskills':'catskills',
  'chautauqua':'chautauqua',
  'elmira':'elmira-corning',
  'fingerlakes':'finger lakes',
  'glensfalls':'glens falls',
  'hudsonvalley':'hudson valley',
  'ithaca':'ithaca',
  'longisland':'long island',
  'newyork':{
  '':'new york',
  'mnh':'manhattan',
  'brk':'brooklyn',
  'que':'queens',
  'brx':'bronx',
  'stn':'staten island',
  'jsy':'new jersey',
  'lgi':'long island',
  'wch':'westchester',
  'fct':'fairfield'},
  'oneonta':'oneonta',
  'plattsburgh':'plattsburgh-adirondacks',
  'potsdam':'potsdam-canton-massena',
  'rochester':'rochester',
  'syracuse':'syracuse',
  'twintiers':'twin tiers NY/PA',
  'utica':'utica-rome-oneida',
  'watertown':'watertown',
  'asheville':'asheville',
  'boone':'boone',
  'charlotte':'charlotte',
  'eastnc':'eastern NC',
  'fayetteville':'fayetteville',
  'greensboro':'greensboro',
  'hickory':'hickory / lenoir',
  'onslow':'jacksonville ',
  'outerbanks':'outer banks',
  'raleigh':'raleigh / durham / CH',
  'wilmington':'wilmington',
  'winstonsalem':'winston-salem',
  'bismarck':'bismarck',
  'fargo':'fargo / moorhead',
  'grandforks':'grand forks',
  'nd':'north dakota',
  'akroncanton':'akron / canton',
  'ashtabula':'ashtabula',
  'athensohio':'athens ',
  'chillicothe':'chillicothe',
  'cincinnati':'cincinnati',
  'cleveland':'cleveland',
  'columbus':'columbus',
  'dayton':'dayton / springfield',
  'limaohio':'lima / findlay',
  'mansfield':'mansfield',
  'sandusky':'sandusky',
  'toledo':'toledo',
  'tuscarawas':'tuscarawas co',
  'youngstown':'youngstown',
  'zanesville':'zanesville / cambridge',
  'lawton':'lawton',
  'enid':'northwest OK',
  'oklahomacity':'oklahoma city',
  'stillwater':'stillwater',
  'tulsa':'tulsa',
  'bend':'bend',
  'corvallis':'corvallis/albany',
  'eastoregon':'east oregon',
  'eugene':'eugene',
  'klamath':'klamath falls',
  'medford':'medford-ashland',
  'oregoncoast':'oregon coast',
  'portland':{
  '':'portland',
  'mlt':'multnomah co',
  'wsc':'washington co',
  'clk':'clark/cowlitz',
  'clc':'clackamas co',
  'nco':'north coast',
  'yam':'yamhill co',
  'grg':'columbia gorge'},
  'roseburg':'roseburg',
  'salem':'salem',
  'altoona':'altoona-johnstown',
  'chambersburg':'cumberland valley',
  'erie':'erie',
  'harrisburg':'harrisburg',
  'lancaster':'lancaster',
  'allentown':'lehigh valley',
  'meadville':'meadville',
  'philadelphia':'philadelphia',
  'pittsburgh':'pittsburgh',
  'poconos':'poconos',
  'reading':'reading',
  'scranton':'scranton / wilkes-barre',
  'pennstate':'state college',
  'williamsport':'williamsport',
  'york':'york',
  'providence':'rhode island',
  'charleston':'charleston',
  'columbia':'columbia',
  'florencesc':'florence',
  'greenville':'greenville / upstate',
  'hiltonhead':'hilton head',
  'myrtlebeach':'myrtle beach',
  'nesd':'northeast SD',
  'csd':'pierre / central SD',
  'rapidcity':'rapid city / west SD',
  'siouxfalls':'sioux falls / SE SD',
  'sd':'south dakota',
  'chattanooga':'chattanooga',
  'clarksville':'clarksville',
  'cookeville':'cookeville',
  'jacksontn':'jackson  ',
  'knoxville':'knoxville',
  'memphis':'memphis',
  'nashville':'nashville',
  'tricities':'tri-cities',
  'abilene':'abilene',
  'amarillo':'amarillo',
  'austin':'austin',
  'beaumont':'beaumont / port arthur',
  'brownsville':'brownsville',
  'collegestation':'college station',
  'corpuschristi':'corpus christi',
  'dallas':'dallas / fort worth',
  'nacogdoches':'deep east texas',
  'delrio':'del rio / eagle pass',
  'elpaso':'el paso',
  'galveston':'galveston',
  'houston':'houston',
  'killeen':'killeen / temple / ft hood',
  'laredo':'laredo',
  'lubbock':'lubbock',
  'mcallen':'mcallen / edinburg',
  'odessa':'odessa / midland',
  'sanangelo':'san angelo',
  'sanantonio':'san antonio',
  'sanmarcos':'san marcos',
  'bigbend':'southwest TX',
  'texoma':'texoma',
  'easttexas':'tyler / east TX',
  'victoriatx':'victoria ',
  'waco':'waco',
  'wichitafalls':'wichita falls',
  'logan':'logan',
  'ogden':'ogden-clearfield',
  'provo':'provo / orem',
  'saltlakecity':'salt lake city',
  'stgeorge':'st george',
  'burlington':'vermont',
  'charlottesville':'charlottesville',
  'danville':'danville',
  'fredericksburg':'fredericksburg',
  'norfolk':'hampton roads',
  'harrisonburg':'harrisonburg',
  'lynchburg':'lynchburg',
  'blacksburg':'new river valley',
  'richmond':'richmond',
  'roanoke':'roanoke',
  'swva':'southwest VA',
  'winchester':'winchester',
  'bellingham':'bellingham',
  'kpr':'kennewick-pasco-richland',
  'moseslake':'moses lake',
  'olympic':'olympic peninsula',
  'pullman':'pullman / moscow',
  'seattle':{
  '':'seatle',
  'see':'seattle',
  'est':'eastside',
  'sno':'snohomish co',
  'kit':'kitsap co',
  'tac':'tacoma co',
  'oly':'olympia',
  'skc':'south king'},
  'skagit':'skagit / island / SJI',
  'spokane': "spokane / coeur d'alene",
  'wenatchee':'wenatchee',
  'yakima':'yakima',
  'charlestonwv':'charleston ',
  'martinsburg':'eastern panhandle',
  'huntington':'huntington-ashland',
  'morgantown':'morgantown',
  'wheeling':'northern panhandle',
  'parkersburg':'parkersburg-marietta',
  'swv':'southern WV',
  'wv':'west virginia (old)',
  'appleton':'appleton-oshkosh-FDL',
  'eauclaire':'eau claire',
  'greenbay':'green bay',
  'janesville':'janesville',
  'racine':'kenosha-racine',
  'lacrosse':'la crosse',
  'madison':'madison',
  'milwaukee':'milwaukee',
  'northernwi':'northern WI',
  'sheboygan':'sheboygan',
  'wausau':'wausau',
  'wyoming':'wyoming',
  'micronesia':'guam-micronesia',
  'puertorico':'puerto rico',
  'virgin':'U.S. virgin islands',
  'princegeorge':'prince george',
  'brussels':'belgium',
  'bulgaria':'bulgaria',
  'zagreb':'croatia',
  'copenhagen':'copenhagen',
  'bordeaux':'bordeaux',
  'rennes':'brittany',
  'grenoble':'grenoble',
  'lille':'lille',
  'loire':'loire valley',
  'lyon':'lyon',
  'marseilles':'marseille',
  'montpellier':'montpellier',
  'cotedazur':"nice / cote d'azur",
  'rouen':'normandy',
  'paris':'paris',
  'strasbourg':'strasbourg',
  'toulouse':'toulouse',
  'budapest':'budapest',
  'reykjavik':'reykjavik',
  'dublin':'dublin',
  'luxembourg':'luxembourg',
  'amsterdam':'amsterdam / randstad',
  'oslo':'norway',
  'bucharest':'romania',
  'moscow':'moscow',
  'stpetersburg':'st petersburg',
  'ukraine':'ukraine',
  'bangladesh':'bangladesh',
  'micronesia':'guam-micronesia',
  'jakarta':'indonesia',
  'tehran':'iran',
  'baghdad':'iraq',
  'haifa':'haifa',
  'jerusalem':'jerusalem',
  'telaviv':'tel aviv',
  'ramallah':'west bank',
  'kuwait':'kuwait',
  'beirut':'beirut, lebanon',
  'malaysia':'malaysia',
  'pakistan':'pakistan',
  'dubai':'united arab emirates',
  'vietnam':'vietnam',
  'auckland':'auckland',
  'christchurch':'christchurch',
  'wellington':'wellington',
  'buenosaires':'buenos aires',
  'lapaz':'bolivia',
  'belohorizonte':'belo horizonte',
  'brasilia':'brasilia',
  'curitiba':'curitiba',
  'fortaleza':'fortaleza',
  'portoalegre':'porto alegre',
  'recife':'recife',
  'rio':'rio de janeiro',
  'salvador':'salvador, bahia',
  'saopaulo':'sao paulo',
  'caribbean':'caribbean islands',
  'santiago':'chile',
  'colombia':'colombia',
  'costarica':'costa rica',
  'santodomingo':'dominican republic',
  'quito':'ecuador',
  'elsalvador':'el salvador',
  'guatemala':'guatemala',
  'managua':'nicaragua',
  'panama':'panama',
  'lima':'peru',
  'puertorico':'puerto rico',
  'montevideo':'montevideo',
  'caracas':'venezuela',
  'virgin':'virgin islands',
  'cairo':'egypt',
  'addisababa':'ethiopia',
  'accra':'ghana',
  'kenya':'kenya',
  'casablanca':'morocco',
  'tunis':'tunisia'}
  
  
  
  # at this point we need to try to break down the URL
  # if it fails oh well!
  #
  # Sample URL
  # search/cta?catAbb=ctd
  # search/sss?query=daytona%20675

  # start with:
  # search/sss?query=daytona%20675
  uri_parts = uri_stem.split('/', 1)
  # ['search', 'sss?query=daytona%20675']
  root = uri_parts[0]

  if debug:
    result['cl_uri_root'] = root
  if 'search' in root:
    try:
      # ['sss', 'query=daytona%20675']
      sales_area, tail = uri_parts[1].split('?')    
      try:
        result['cl_sales_area'] = cl_sales_dict[sales_area]
      except:
        result['cl_sales_area_unknown'] = sales_area
      if 'query' in tail:
        # ['query', 'daytona%20675&sort']
        tail_parts = tail.split('=')
        if '&' in tail_parts[1]:
          raw_search_list = tail_parts[1].split('&', 1)
          raw_search = raw_search_list[0]
        else:
          raw_search = tail_parts[1]

        search_string = raw_search.replace('%20', ' ')
        search_string = search_string.replace('%22', ' ')
        search_string = search_string.replace('+', ' ')        
        result['url_search_string'] = search_string
    except:
      result['cl_bad_url'] = uri_stem
  
  # the next type of craigslist url is a direct link to an item
  # http://sfbay.craigslist.org/sby/fuo/4551709502.html
  # that url links to sfbay -> southbay -> furniture by owner -> item number
  
  dot_count = whole_domain.count('.')
  # for domains that are like
  # www.craigslist.org
  # saltalakecity.craigslist.org
  if dot_count > 1:
    sub_domain, junk = whole_domain.split('.', 1)

    # used this to debug things
    # you should change debug = True at top of code to get extra values
    """
    tid=262 craigslist | urldecode  | search NOT cl_region="www" | search NOT cl_root="*" | chart values(raw_url), values(cl_region), values(cl_sub_region), values(cl_region_unknown), values(cl_root) by url_whole_domain
    """

  
    cl_not_regions = ['post','accounts', 'www', 'geo', 'map0', 'map1', 'map2', 
    'map3', 'map4', 'map5', 'map6', 'map7', 'map8', 'map9']
    if not sub_domain in cl_not_regions:
      try:
        result['cl_region'] = sub_domain  
        # this could either return a dictionar of sub regions
        # or it could be the name of the region
        region = cl_region_dict[sub_domain]
  
        if type(region) == str:
          result['cl_sub_region'] = region
        elif type(region) == dict:
          result['cl_sub_region'] = cl_region_dict[sub_domain][root]
      except:
        if debug:
          result['cl_root'] = root
          result['cl_region_unknown'] = sub_domain

  return result

#############
# apple.com #
#############

def apple(whole_domain, uri_stem, result):
  """
  old example
  tid=262 apple | urldecode | search NOT url_type="image" | search cl_uri_root="search" | top limit=50 url_search_string
  This search gives you the top things people are searching for in craiglist
  """
  if debug:
    result['url_process_function'] = 'apple'
    
  result['apple_region'] = 'americas'
  result['apple_bad_url'] = '???fooo???'
  result['url_search_string'] = 'iPhone 6'
  
  return result 

##############
# google.com #
##############
def google(whole_domain, uri_stem, result):
  """
  tid=262 tid=262 google "q=" | urldecode | top limit=500 google_search
  """
  if debug:
    result['url_process_function'] = 'google'
  if debug:
    result['google_whole_domain'] = whole_domain
    result['google_uri_stem'] = uri_stem
  # urls that are formatted like such
  # https://www.google.com/?gws_rd=ssl#q=some+special+string
  # the search string is: some special string
  if 'q=' in uri_stem:
    head, tail = uri_stem.split('q=', 1)
    if debug:
      result['google_q_head'] = head
      result['google_q_tail'] = tail
    if '&' in tail:
      raw_query, scrap = tail.split('&', 1)
      if debug:
        result['google_tail_split_a'] = raw_query
        result['google_tail_split_b'] = scrap
    else:
      raw_query = tail
      if debug:
        result['google_tail_split_a'] = raw_query
    # now the split up stuff is good but we still have 
    # junk like %20 and + in the string so we need to clean it up
    search_string = search_cleanup(raw_query)
    if len(search_string) > 1:
      space_count = whole_domain.count(' ')
      if search_string[0] == "%":
        result['google_bad_search_string'] = search_string
      elif (space_count < 2) and (len(search_string) > 20):
        result['google_bad_search_string'] = search_string        
      else:
        result['google_search'] = search_string
        result['url_search_string'] = search_string

  return result

###########
# twitter #
###########

def twitter(whole_domain, uri_stem, result):
  """
  decodes the twitter search only
  """
  if debug:
    result['url_process_function'] = 'twitter'
    
  if debug:
    result['twitter_whole_domain'] = whole_domain
    result['twitter_uri_stem'] = uri_stem

  if 'q=' in uri_stem:
    head, tail = uri_stem.split('q=', 1)
    if debug:
      result['twitter_q_head'] = head
      result['twitter_q_tail'] = tail      
    raw_query = tail
    search_string = search_cleanup(raw_query)
    result['twitter_search'] = search_string
    result['url_search_string'] = search_string
    
  return result

def stack_overflow(whole_domain, uri_stem, result):
  """
  decodes the twitter search only
  """
  if debug:
    result['url_process_function'] = 'stack_overflow'
    
  if debug:
    result['stack_overflow_whole_domain'] = whole_domain
    result['stack_overflow_uri_stem'] = uri_stem

  if 'q=' in uri_stem:
    head, tail = uri_stem.split('q=', 1)
    if debug:
      result['stack_overflow_q_head'] = head
      result['stack_overflow_q_tail'] = tail      
    raw_query = tail
    search_string = search_cleanup(raw_query)
    result['stack_overflow_search'] = search_string
    result['url_search_string'] = search_string
    
  return result

##########
# amazon #
##########

def amazon(whole_domain, uri_stem, result):
    result['url_process_function'] = 'amazon'
    
    if 'keywords=' in uri_stem:
        junk, keyword, product = uri_stem.partition('keywords=')
        
        if '&' in product:
            product, morejunk = product.split('&', 1)

        raw_query = product
        search_string = search_cleanup(raw_query)
        result['url_search_string'] = search_string

    return result

###########
# youtube #
###########

def youtube(whole_domain, uri_stem, base_domain, result):
    result['url_process_function'] = 'youtube'
    
    if 'youtube.com' in base_domain:
      ''' http://www.youtube.com/ user/ marquesbrownlee/videos '''
      if '&' in uri_stem:
        uri_stem, tail = uri_stem.split('&', 1)
      if 'uploads' in uri_stem:
        result['youtube_bad_url'] = whole_domain
      elif ('user' in uri_stem) and ('/' in uri_stem):
          junk, username = uri_stem.split('/', 1)
          if '/' in username:
              username, morejunk = username.split('/', 1)
          username = search_cleanup(username)
          result['youtube_user_search'] = username
          result['url_search_string'] = username
      elif 'search_query=' in uri_stem:
          junk, keyword, search_string = uri_stem.partition('search_query=')
          search_string = search_cleanup(search_string)
          result['url_search_string'] = search_string
    else:
      result['youtube_bad_url'] = whole_domain
      
    return result
    
########
# bing #
########

def bing(whole_domain, uri_stem, result):
  result['url_process_function'] = 'bing'
    

  if debug:
    result['bing_whole_domain'] = whole_domain
    result['bing_uri_stem'] = uri_stem
  if '&' in uri_stem:
    uri_stem, uri_tail = uri_stem.split('&', 1)
  if 'q=' in uri_stem:
    head, tail = uri_stem.split('q=', 1)
    if debug:
      result['bing_q_head'] = head
      result['bing_q_tail'] = tail      
    raw_query = tail
    search_string = search_cleanup(raw_query)
    if "http" in search_string:
      result['bing_bad_url'] = search_string
    elif 'www.' in search_string:
      result['bing_bad_url'] = search_string
    else:
      result['bing_search'] = search_string
      result['url_search_string'] = search_string
    
  return result 
  
#########
# cisco #
#########

def cisco(whole_domain, uri_stem, result):
  result['url_process_function'] = 'cisco'
    

  if debug:
    result['cisco_whole_domain'] = whole_domain
    result['cisco_uri_stem'] = uri_stem
  if '&' in uri_stem:
    uri_stem, uri_tail = uri_stem.split('&', 1)
    
  if 'q=' in uri_stem:
    head, tail = uri_stem.split('q=', 1)
    if debug:
      result['cisco_q_head'] = head
      result['cisco_q_tail'] = tail      
    raw_query = tail
    search_string = search_cleanup(raw_query)
    result['cisco_search'] = search_string
    result['url_search_string'] = search_string
    
  return result   

#############
# wikipedia #
#############

def wikipedia(whole_domain, uri_stem, result):
  """
  test with tid=262 wikipedia | urldecode | top url_search_string by url_process_function
  you will find some google URLs as well
  tid=262 wikipedia | urldecode | search url_process_function="wikipedia" | chart count by url_search_string
  """
  result['url_process_function'] = 'wikipedia'
  '''http://en.wikipedia.org/wiki/Obama'''
  if 'wiki/' in uri_stem:
      junk, keyword, search_string = uri_stem.partition('wiki/')
      search_string = search_cleanup(search_string)
      if search_string[0] == "%":
        result['wikipedia_bad_search_string'] = search_string
      else:
        result['url_search_string'] = search_string
  return result

############
# facebook #
############

def facebook(whole_domain, uri_stem, result):
    """
    tid=262 facebook | urldecode | search url_process_function="facebook" | chart count by url_search_string | sort -count
    """
    result['url_process_function'] = 'facebook'
    '''https://www.facebook.com/andy.haukness?fref=ts&ref=br_tf'''
    if '?fref=' in uri_stem:
        search_string, junk = uri_stem.split('?', 1)
        search_string = search_cleanup(search_string)
        result['url_search_string'] = search_string
    return result

########
# ebay #
########

def ebay(whole_domain, uri_stem, result):
    """
    tid=262 ebay | urldecode | search url_process_function="ebay" | chart count by url_search_string | search -count
    """
    result['url_process_function'] = 'ebay'
    '''http://www.ebay.com/sch/i.html?_odkw=google+glass&_osacat=0&_from=R40&_from=R40&_trksid=p2045573.m570.l1313.TR12.TRC2.A0.H0.Xnexus+5&_nkw=nexus+5&_sacat=0'''
    if 'nkw=' in uri_stem:
        junk, keyword, search_string = uri_stem.partition('nkw=')
        if '&' in search_string:
            search_string, junk = search_string.split('&', 1)
            search_string = search_cleanup(search_string)
            result['url_search_string'] = search_string
    return result

##########
# reddit #
##########

def reddit(whole_domain, uri_stem, result):
    '''http://www.reddit.com/search?q=google+vulnerability'''
    '''http://www.reddit.com/search?q=google+glass&restrict_sr=off&sort=relevance&t=all'''
    result['url_process_function'] = 'reddit'
    if 'search?q=' in uri_stem:
        junk, keyword, search_string = uri_stem.partition('search?q=')
        if '&' in search_string:
            search_string, morejunk = search_string.split('&', 1)
        search_string = search_cleanup(search_string)
        result['url_search_string'] = search_string

    return result

##########
# newegg #
##########

def newegg(whole_domain, uri_stem, result):
    '''http://www.newegg.com/Product/ProductList.aspx?Submit=ENE&DEPA=0&Order=BESTMATCH&Description=ipad+mini&N=-1&isNodeId=1'''
    result['url_process_function'] = 'newegg'
    if 'Description=' in uri_stem:
        if not 'BrandLiveChat' in uri_stem:
            junk, keyword, search_string = uri_stem.partition('Description=')
            if '&' in search_string:
                search_string, morejunk = search_string.split('&', 1)
            search_string = search_cleanup(search_string)
            result['url_search_string'] = search_string

    return result

#######
# ask #
#######

def ask(whole_domain, uri_stem, result):
    '''http://www.ask.com/web?qsrc=1&o=0&l=dir&q=jan+koum&qo=serpSearchTopBox'''
    result['url_process_function'] = 'ask'
    if 'dir&q=' in uri_stem:
        junk, keyword, search_string = uri_stem.partition('dir&q=')
        if '&' in search_string:
            search_string, morejunk = search_string.split('&', 1)
        search_string = search_cleanup(search_string)
        result['url_search_string'] = search_string

    return result

###########
# netflix #
###########

def netflix(whole_domain, uri_stem, result):
    '''http://dvd.netflix.com/Search?oq=&ac_posn=&fcld=true&v1=silicon+valley&search_submit='''
    result['url_process_function'] = 'netflix'
    if '&fcld=true&v1=' in uri_stem:
        junk, keyword, search_string = uri_stem.partition('&fcld=true&v1=')
        if '&' in search_string:
            search_string, morejunk = search_string.split('&', 1)
        search_string = search_cleanup(search_string)
        result['url_search_string'] = search_string

    return result

############
# linkedin #
############

def linkedin(whole_domain, uri_stem, result):
    '''https://www.linkedin.com/vsearch/f?type=all&keywords=jan+koum&orig=GLHD&rsid=&pageKey=nprofile_view_nonself&trkInfo='''
    result['url_process_function'] = 'linkedin'
    if 'keywords=' in uri_stem:
        junk, keyword, search_string = uri_stem.partition('keywords=')
        if '&' in search_string:
            search_string, morejunk = search_string.split('&', 1)
        search_string = search_cleanup(search_string)
        result['url_search_string'] = search_string

    return result


###########
# generic #
###########

def generic(whole_domain, base_domain, uri_stem, result):
  result['url_process_function'] = 'generic'
    

  if debug:
    result['generic_whole_domain'] = whole_domain
    result['generic_uri_stem'] = uri_stem
    
  no_decode_list = ['gstatic.com', 'doubleclick.net', 'quora.com']
  if '&' in uri_stem:
    uri_stem, uri_tail = uri_stem.split('&', 1)
  if not base_domain in no_decode_list:
    if 'q=' in uri_stem:
      head, tail = uri_stem.split('q=', 1)
      if debug:
        result['generic_q_head'] = head
        result['generic_q_tail'] = tail      
      raw_query = tail
      search_string = search_cleanup(raw_query)
      space_count = whole_domain.count(' ')
      if (space_count < 2) and (len(search_string) > 20):
        result['generic_bad_search_string'] = search_string
      else:
        result['generic_search'] = search_string
        result['url_search_string'] = search_string
    
  return result 


##################
# search_cleanup #
##################
def search_cleanup(raw_search):
  """
  This function removes the %20, %22 and + from the search strings
  and substitues them with spaces and such to make it pretty
  
  not very efficient code here. Should use a dictionary and walk the string
  """
  search_string = raw_search.replace('%20', ' ')
  search_string = search_string.replace('%E2%80%93', '-')
  search_string = search_string.replace('%22', ' ')
  search_string = search_string.replace('%23', '#')
  search_string = search_string.replace('%28', '(')
  search_string = search_string.replace('%29', ')')
  search_string = search_string.replace('%3A', ':')
  search_string = search_string.replace('%3a', ':')
  search_string = search_string.replace('%26', '&')
  # this should be decoded as a + but I want it to be a space
  search_string = search_string.replace('%2B', '+')
  search_string = search_string.replace('%2b', '+')
  search_string = search_string.replace('%2C', ',')  
  search_string = search_string.replace('%2c', ',')  
  search_string = search_string.replace('%2F', '/') 
  search_string = search_string.replace('%2f', '/')
  search_string = search_string.replace('%2520', ' ')  
  search_string = search_string.replace('%3b', ';')
  search_string = search_string.replace('%3B', ';')
  search_string = search_string.replace('%3f', '?')
  search_string = search_string.replace('%3F', '?')
  search_string = search_string.replace('%27', "'")
  # so we just replace the + with a space here 
  search_string = search_string.replace('+', ' ')
  search_string = search_string.replace('_', " ")     

  return search_string

#########
# is_ip #
#########

def is_ip(hostname):
  """
  This function verifies the hostname provided is an IP address
  """
  
  valid_ip = False
  try:
    if ':' in hostname:
      ip_address, port = hostname.split(':')
    else:
      ip_address = hostname
    octet_one, octet_two, octet_three, octet_four = ip_address.split('.')
    if int(octet_one) in range(1,254):
      if int(octet_two) in range(0,255):
        if int(octet_three) in range(0,255):
          if int(octet_four) in range(1,254):
            valid_ip = True

  except:
    valid_ip = False

  return valid_ip



############
# Find URL #
############

def find_url(results, settings):

  try:
    fields, argvals = splunk.Intersplunk.getKeywordsAndOptions()

    for result in results:
      if result.has_key('url'):
        # this is our raw url
        # We don't need to set this. I did to make things visible in splunk search
        raw_url = result['url']
        if debug:
          result['raw_url'] = raw_url
        
        # get our domain name here
        whole_domain, uri_stem = raw_url.split('/', 1)
        result['url_whole_domain'] = whole_domain
        result['url_uri'] = uri_stem
        
        # check to see if it's an IP address
        domain_is_ip = is_ip(whole_domain)
        result['url_is_ip'] = domain_is_ip


        ###############################
        # try to find the base domain #
        ###############################
        
        # count the number of dots tells us if it's a base domain
        # domain.com
        # or it has a host.domain.com 
        # sometimes it's a host.domain.com.cn 
        # there can also be host.domain.cn
        # and of course domain.cn
        
        # the sorted list looke like:
        # domain.com
        # domain.cn
        # host.domain.com
        # host.domain.cn
        # host.subdomain.domain.com
        # host.subdomain.domain.cn
        # host.domain.com.cn
        # host.subdomain.domain.com.cn
        
        dot_count = whole_domain.count('.')
        us_tld_list = ["com", "COM", "net", "NET", "edu", "EDU", 'org', 'ORG']

        if dot_count == 0:
          result['url_bad_domain'] = whole_domain
        elif domain_is_ip:
          base_domain = whole_domain
        
        else:
          # this covers:
          # domain.com
          # domain.cn
          if dot_count == 1:
            base_domain = whole_domain
          
          # this covers:
          # host.domain.com
          # host.domain.cn          
          elif dot_count == 2:
            parts = whole_domain.split('.', 1)
            base_domain = parts[1]  
          
          else:        
            for tld in us_tld_list:
              # this handles:
              # host.domain.com.cn
              # host.subdomain.domain.com.cn
              # host.subdomain.domain.com
              if tld in whole_domain:
                parts = whole_domain.split('.')
                # host.subdomain.domain.com
                # server.host.subdomain.domain.com
                if parts[-1] in us_tld_list:
                  temp_base_domain = parts[-2] + '.' + parts[-1]
                  base_domain = temp_base_domain
                else:
                  # host.domain.com.cn
                  # host.subdomain.domain.com.cn
                  temp_base_domain = parts[-3] + '.' + parts[-2] + '.' + parts[-1]
                  base_domain = temp_base_domain
                  
              # this covers
              # host.subdomain.domain.cn
              else:
                parts = whole_domain.split('.')
                # parts will look like:
                # ['host', 'subdomain', 'domain', 'cn']
                temp_base_domain = parts[-2] + '.' + parts[-1]
                base_domain = temp_base_domain
            
          result['url_base_domain'] = base_domain
        
        
          ###############################
          # call our functions per site #
          ###############################
  
          if find_image(uri_stem): 
            result['url_type'] = "image"
          elif 'google' in base_domain:
            result = google(whole_domain, uri_stem, result)
          elif 'bing' in base_domain:
            result = bing(whole_domain, uri_stem, result)
          elif base_domain == 'craigslist.org':
            result = craigslist(whole_domain, uri_stem, result)
          elif base_domain == 'cisco.com':
            result = cisco(whole_domain, uri_stem, result)
          elif 'twitter' in base_domain:
            result = twitter(whole_domain, uri_stem, result)
          elif 'amazon' in base_domain:
              result = amazon(whole_domain, uri_stem, result)
          elif 'youtube' in base_domain:
              result = youtube(whole_domain, uri_stem, base_domain, result)
          elif 'stackoverflow' in base_domain:
            result = stack_overflow(whole_domain, uri_stem, result)
          elif 'facebook' in base_domain:
            result = facebook(whole_domain, uri_stem, result)
          elif 'ebay' in base_domain:
              result = ebay(whole_domain, uri_stem, result)
          elif 'wikipedia' in base_domain:
            result = wikipedia(whole_domain, uri_stem, result) 
          elif 'reddit' in base_domain:
              result = reddit(whole_domain, uri_stem, result)
          elif 'newegg' in base_domain:
              result = newegg(whole_domain, uri_stem, result)
          elif 'ask' in base_domain:
              result = ask(whole_domain, uri_stem, result)
          elif 'netflix' in base_domain:
              result = netflix(whole_domain, uri_stem, result)
          elif 'linkedin' in base_domain:
              result = linkedin(whole_domain, uri_stem, result)
          else:
            result = generic(whole_domain, base_domain, uri_stem, result)
          
        

          
    splunk.Intersplunk.outputResults(results)
          
  except:
		import traceback
		stack =  traceback.format_exc()
		results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))      
   
  
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
results = find_url(results, settings)
     

