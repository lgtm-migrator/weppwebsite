# Make the 'real-time' runs!!!

echo -n "Begin Daily IDEP Run: "
date

# Convert our 15minute data into a local day's worth
cd iemcligen
python grids2shp.py

set direct=`date --date '1 day ago' +'%Y/%m/%d'`
mkdir -p /mesonet/wepp/data/static/$direct

cd /mesonet/www/apps/weppwebsite/html/GIS
php -q plot.php width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_rainfall_in.png
php -q plot.php var=avg_runoff_in width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_avg_runoff_in.png
php -q plot.php var=avg_loss_acre width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_avg_loss_acre.png 
php -q plot.php var=vsm width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_vsm.png 

cd /mesonet/www/apps/weppwebsite/scripts/iemcligen
python build.py

cd /mesonet/wepp/GIS
python yearlyPrecip.py
python monthlyPrecip.py


cd /mesonet/www/apps/weppwebsite/scripts/RT
rm -Rf error
mkdir error
rm -Rf wb.bad
mkdir wb.bad
rm -rf env
mkdir env

rm -rf wb.old
mv wb wb.old
mkdir wb

rm -rf output
mkdir output

python proctor.py
python extractWB.py 
python processEvents.py 
psql -h iemdb -f insert.sql wepp
python summarize.py

./processEvents.py `date --date '1 day ago' +'%Y %m %d'`
psql -h iemdb -f insert.sql wepp
./summarize.py `date --date '1 day ago' +'%Y %m %d'`

cd /mesonet/www/apps/weppwebsite/html/GIS
php -q plot.php var=avg_runoff_in width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_avg_runoff_in.png 
php -q plot.php var=avg_loss_acre width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_avg_loss_acre.png 
php -q plot.php var=vsm width=320 height=240 > /mesonet/wepp/data/static/${direct}_daily_vsm.png 

#rm -f /tmp/WEPP.lock
date
