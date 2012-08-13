import mx.DateTime
import shapelib
import dbflib
import sys
import os
import numpy
import traceback
import netCDF4


def createNETCDF(s):
	dirPre = s.strftime("/mesonet/wepp/data/rainfall/netcdf/daily/%Y/%m/")
	if not os.path.isdir(dirPre):
		os.makedirs(dirPre)
	fileName = dirPre + s.strftime("%Y%m%d_rain.nc")
	nc = netCDF4.Dataset(fileName, 'w')
 
	nc.createDimension("time", 96)
	nc.createDimension("hrap_i", 173)
	nc.createDimension("hrap_j", 134)

	tm = nc.createVariable("time", numpy.int, ('time',) ) 
	tm.units = "minutes since %s" % (s.strftime("%Y-%m-%d %H:%M"),)
	lat = nc.createVariable("latitude", numpy.float, ('hrap_j', 'hrap_i') )
	lon = nc.createVariable("longitude", numpy.float, ('hrap_j', 'hrap_i') )
	r15m = nc.createVariable("rainfall_15min", numpy.float, ('time', 'hrap_j', 'hrap_i') )
	r15m.units = "mm"
	r1d = nc.createVariable("rainfall_1day", numpy.float, ('hrap_j', 'hrap_i'))
	r1d.units = "mm"

	lat[:] = numpy.fromfile("/mesonet/wepp/GIS/lats.dat", sep=' ')
	lon[:] = numpy.fromfile("/mesonet/wepp/GIS/lons.dat", sep=' ')
	nc.sync()
	return nc, r1d, r15m, tm


def createSQLFILE(s):
	e = s + mx.DateTime.RelativeDateTime(day=1, months=+1)
	sql = open("rainfall.sql", 'w')
	if updateMonthly:
		sql.write("DELETE from monthly_rainfall_%s WHERE valid = '%s-01';\n" % (
											s.year, s.strftime("%Y-%m") ) )

	sql.write("DELETE from daily_rainfall_%s WHERE valid = '%s';\n" % (
										s.year, s.strftime("%Y-%m-%d") ) )
	sql.write("COPY daily_rainfall_%s FROM stdin;\n" % (s.year,))
	return sql

def createGIS(s):
	dir = s.strftime("/mesonet/wepp/data/rainfall/shape/daily/%Y/%m/")
	fname = s.strftime("%Y%m%d_rain")

	if (not os.path.isdir(dir)):
		os.makedirs(dir)
	dbf = dbflib.create(dir + fname)
	dbf.add_field("RAINFALL", dbflib.FTDouble, 5, 2)

	shp = shapelib.create(dir + fname, shapelib.SHPT_POINT)
	return shp, dbf

def main(_YEAR, _MONTH, _DAY):
	s = mx.DateTime.DateTime(_YEAR,_MONTH,_DAY,0,15)
	e = s + mx.DateTime.RelativeDateTime(days=+1)

	nc, nc_r1d, nc_r15m, nc_tm = createNETCDF(s)
	sql = createSQLFILE(s)
	shp, dbf = createGIS(s)

	rain15 = numpy.zeros( (96, 134, 173), numpy.float)
	interval = mx.DateTime.RelativeDateTime(minutes=+15)
	now = s
	i = 0
	while now < e:
		gts = now.gmtime()
		fp = gts.strftime("product/%Y/%Y%m%d/IA%Y%m%d_%H%M.dat")
		#print 'Processing: %s' % (fp,)
		nc_tm[i] = i * 15
		if os.path.isfile(fp):
			try:
				t = readFloatArray(fp)
			except:
				print "Error with %s" % (fp,)
				traceback.print_exc(file=sys.stdout)
				print "------> Using zeros"
				t = numpy.zeros( (134,173), numpy.float)
		else:
			print "------> MISSING [%s] Using zeros" % (fp,)
			t = numpy.zeros( (134,173), numpy.float)
		rain15[i] = t
		now += interval
		i += 1
	max_rain15 = numpy.max(rain15, 1)
	hr_cnt = numpy.sum( numpy.where( rain15 > 0, 1, 0) )
	nc_r15m[:] = rain15
	rain = numpy.sum(rain15, 0)
	nc_r1d[:] = rain
	nc.close()

	stringDate = s.strftime("%Y-%m-%d")
	lats = numpy.fromfile("/mesonet/wepp/GIS/lats.dat", sep=' ')
	lons = numpy.fromfile("/mesonet/wepp/GIS/lons.dat", sep=' ')
	i = 0
	max_rainfall = 0
	(rows, cols) = numpy.shape(rain)
	lats = numpy.reshape(lats, (rows, cols))
	lons = numpy.reshape(lons, (rows, cols))
	for row in range(rows):
		for col in range(cols):
			obj = shapelib.SHPObject(shapelib.SHPT_POINT, i, 
				[[(lons[row,col], lats[row,col])]] ) 
			shp.write_object(-1, obj)
			dbf.write_record(i, (rain[row][col] / 25.4 ,) )
			if rain[row][col] > 0:
				sql.write("%s\t%s\t%s\t%s\t%s\n" % (i +1, stringDate, 
					rain[row,col], max_rain15[row,col], hr_cnt[row,col]))
			if rain[row,col] > max_rainfall:
				max_rainfall = rain[row,col]
			i = i+1

	del(dbf)
	del(shp)
	sql.write("\.\n")
	em = s + mx.DateTime.RelativeDateTime(months=+1,day=1)
	sql.write("DELETE from rainfall_log WHERE valid = '%s' ;\n" % (
											s.strftime("%Y-%m-%d"),) )
	sql.write("""INSERT into rainfall_log (valid, max_rainfall) values ( 
	'%s', %s) ;\n""" % (s.strftime("%Y-%m-%d"), max_rainfall) )
	if (updateMonthly):
		sql.write("""INSERT into monthly_rainfall_%s (hrap_i, valid, rainfall,
		peak_15min, hr_cnt) 
        SELECT hrap_i, '%s-01', sum(rainfall), max(peak_15min), sum(hr_cnt) 
		from daily_rainfall_%s WHERE 
        valid >= '%s-01' and valid < '%s-01' GROUP by hrap_i;\n""" % (
		s.year, s.strftime("%Y-%m"), s.year, s.strftime("%Y-%m"), 
		em.strftime("%Y-%m") ) )


		sql.write("DELETE from yearly_rainfall WHERE valid = '%s-01-01';\n" \
		% (s.year) )
		sql.write("""INSERT into yearly_rainfall (hrap_i, valid, rainfall,
		peak_15min, hr_cnt) 
		SELECT hrap_i, '%s-01-01', sum(rainfall), max(peak_15min), sum(hr_cnt) 
		from monthly_rainfall_%s GROUP by hrap_i;\n""" % (s.year, s.year) )

if (__name__ == "__main__"):
	if (len(sys.argv) >= 4):
		_YEAR = int(sys.argv[1])
		_MONTH = int(sys.argv[2])
		_DAY = int(sys.argv[3])
		updateMonthly = 0
	else:
		ts = mx.DateTime.now() + mx.DateTime.RelativeDateTime(days=-1)
		_YEAR, _MONTH, _DAY = ts.year, ts.month, ts.day
		updateMonthly = 1
	if (len(sys.argv) == 5):
		updateMonthly = 1

	"""
	s = mx.DateTime.DateTime(1997, 4, 1)
	e = mx.DateTime.DateTime(1997, 5, 1)
	interval = mx.DateTime.RelativeDateTime(days=+1)
	now = s
	while (now < e):
		updateMonthly = 0
		print now
		if (now.month != (now + mx.DateTime.RelativeDateTime(days=1)).month):
			updateMonthly = 1
		main( now.year, now.month, now.day )
		os.system("psql -h iemdb -f rainfall.sql wepp") 
		now += interval
	"""
	main(_YEAR, _MONTH, _DAY)
	if (len(sys.argv) == 1):
		os.system("psql -h iemdb -f rainfall.sql -o grid2shp.log wepp")
