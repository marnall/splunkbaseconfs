import math, sys, csv

def main():
	if len(sys.argv) != 7:
		print "Usage: python getPositionFromBearing.py [latitude] [longitude] [bearing] [distance] [latitude2] [longitude2]"
		sys.exit(1)

	lat1 = sys.argv[1] #51.13276
	lon1 = sys.argv[2] #0.0
	bearing = sys.argv[3] #45
	distance = sys.argv[4]
	latitude2 = sys.argv[5]
	longitude2 = sys.argv[6]

	infile = sys.stdin
	outfile = sys.stdout

	r = csv.DictReader(infile)
	header = r.fieldnames

	w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
	w.writeheader()

	for result in r:
		bearingRad = math.cos(math.radians(float(result[bearing])))
		R = 6378.1 #Radius of the Earth

		lat1r = math.radians(float(result[lat1])) #Current lat point converted to radians
		lon1r = math.radians(float(result[lon1])) #Current long point converted to radians

		lat2 = math.asin( math.sin(lat1r)*math.cos(float(result[distance])/R) +
			math.cos(lat1r)*math.sin(float(result[distance])/R)*math.cos(bearingRad))

		lon2 = lon1r + math.atan2(math.sin(bearingRad)*math.sin(float(result[distance])/R)*math.cos(lat1r),
			math.cos(float(result[distance])/R)-math.sin(lat1r)*math.sin(lat2))

		lat2 = math.degrees(lat2)
		lon2 = math.degrees(lon2)

		result[latitude2] = lat2
		result[longitude2] = lon2

		w.writerow(result)

main()
