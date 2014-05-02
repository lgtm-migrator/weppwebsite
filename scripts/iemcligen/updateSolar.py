'''
 A straight copy of ISUAG solar radiation data to IDEPv1 climate sector data,
 if data is not found from the ISUAG network, then the previous year's value
 is used.  Lame yes, but will be improved with IDEPv2
'''
import psycopg2
ISUAG = psycopg2.connect(database='isuag', host='iemdb')
icursor = ISUAG.cursor()
WEPP = psycopg2.connect(database='wepp', host='iemdb')
wcursor = WEPP.cursor()
import sys
import datetime


cref = {1: 'DONI4', 2: 'KNAI4', 3: 'NASI4', 
        4: 'CNAI4', 5: 'AEEI4', 6: 'CIRI4',
        7: 'OKLI4', 8: 'CHAI4', 9: 'CRFI4'}

# c80 is solar rad
def process(ts):
    for sector in cref.keys():
        st = cref[sector]
        day = ts.strftime("%Y-%m-%d")
        sql = """SELECT slrmj_tot from sm_daily 
              WHERE valid = '%s' and station = '%s' and slrmj_tot is not null
              """ % (day, st)
        icursor.execute(sql)
        if icursor.rowcount == 0:
            print "Missing Solar for sector: %s station: %s" % (sector, st)
            continue
        row = icursor.fetchone()
        # convert mj to langleys
        rad = row[0] * 23.9
        wcursor.execute("""UPDATE climate_sectors SET rad = %s 
          WHERE day = %s and sector = %s """, (rad, day, sector))

#"""
if __name__ == '__main__':
    ts = datetime.datetime.now() - datetime.timedelta(days=1)
    if len(sys.argv) == 4:
        ts = datetime.datetime( int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
    process(ts)

    wcursor.close()
    WEPP.commit()
    WEPP.close()