#!/usr/bin/env python
# Pull out yearly precipitation
# Daryl Herzmann 26 Jul 2004

import pg, dbflib, mx.DateTime, shutil
mydb = pg.connect('wepp','iemdb')

sts = mx.DateTime.DateTime(2008,3,1)
ets = mx.DateTime.DateTime(2008,11,1)
interval = mx.DateTime.RelativeDateTime(days=+7)

now = sts
ohrap = {}
rs = mydb.query("SELECT hrap_i from hrap_utm ORDER by hrap_i ASC").dictresult()
for i in range(len(rs)):
    ohrap[ int(rs[i]['hrap_i']) ] = {'rain': 0, 'hours': 0, 'mrain': 0}

hrapi = ohrap.keys()
hrapi.sort()

while (now < ets):
    print "Hello Heather, I am here ", now
    dbf = dbflib.create("weeklyrain/%srain" % (now.strftime("%Y%m%d"), ) )
    dbf.add_field("RAINFALL", dbflib.FTDouble, 8, 2)
    dbf.add_field("RAINHOUR", dbflib.FTDouble, 8, 2)
    dbf.add_field("RAINPEAK", dbflib.FTDouble, 8, 2)
    
    rs = mydb.query("select hrap_i, sum(rainfall) /25.4 as rain, \
	max(peak_15min) /25.4 * 4 as mrain, sum(hr_cnt) / 4.0 as hours from \
	daily_rainfall_%s  WHERE valid >= '%s' and valid < '%s' \
        GROUP by hrap_i ORDER by hrap_i ASC" % (now.strftime("%Y"), \
        now.strftime("%Y-%m-%d"), (now+interval).strftime("%Y-%m-%d")\
        ) ).dictresult()

    hrap = ohrap
    for i in range(len(rs)):
        #print rs[i]
        hrap[ int(rs[i]['hrap_i']) ]= {'rain': float(rs[i]['rain']), \
           'hours': float(rs[i]['hours']), 'mrain': float(rs[i]['mrain']) }

    for i in range(len(hrapi)):
        key = hrapi[i]
        dbf.write_record(i, (hrap[key]['rain'], hrap[key]['hours'],\
		hrap[key]['mrain'] ) )

    del dbf
    shutil.copy("static/hrap_point_4326.shp", "weeklyrain/%srain.shp" % (now.strftime("%Y%m%d"), ) )
    shutil.copy("static/hrap_point_4326.shx", "weeklyrain/%srain.shx" % (now.strftime("%Y%m%d"), ) )
    shutil.copy("static/hrap_point_4326.prj", "weeklyrain/%srain.prj" % (now.strftime("%Y%m%d"), ) )

    now += interval

