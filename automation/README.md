### What is this?
Here is a bit of bash that you can place in the IRRPT folder on your host (Expects irrpt to be in /usr/share/irrpt).

#### How to use?

```ros.sh get asn slug```

Calling as above, this bash script will then output files into ```/usr/share/irrpt/filters/``` for both IPv4 and IPv6 output, in the name of the filter rule.  In my network, slug used to express the type/name of the peer -- for example, I use fcix for the FCIX IXP in Fremont.  In my setup I have a filter for fcix called fcix-import that gets called if the prefix matches, to later add the communities/local pref and finally accept the prefixes.  You can of course modify for your own needs - you might want to just accept the prefix and do nothing else YMMV.

Once you have the desired text files, you can then run the python script against them - supplying the correct variables for filter name, config file and router name;

```python3 mikrotik_irr_updater.py as12345-fcix-import-ipv4 as12345-fcix-import-ipv4.txt pr1.fmt2```

#### How am I using it in Production?

I have a wrapper I'm calling from CRON in the following format.  It's got a line for each peer/router combo

```
cat /usr/share/irrpt/cron.sh

/usr/share/irrpt/wrapper.sh 7034 fcix pr1.fmt2
/usr/share/irrpt/wrapper.sh 7500 fcix pr1.fmt2
/usr/share/irrpt/wrapper.sh 16509 sfmix pr2.fmt2
/usr/share/irrpt/wrapper.sh 32934 sfmix pr2.fmt2

```
The cron.sh file then calls a wrapper with ASN, SLUG, HOSTNAME as inputs, it then does the operations as needed, including generating the filter files stored in /usr/share/irrpt/filters and calling the python script against them all to apply the updates.

```
cat /usr/share/irrpt/wrapper.sh

/usr/share/irrpt/ros.sh get $1 $2
python3 /usr/share/irrpt/mikrotik_irr_updater.py as$1-$2-import-ipv4 /usr/share/irrpt/filters/as$1-$2-import-ipv4.txt $3
python3 /usr/share/irrpt/mikrotik_irr_updater.py as$1-$2-import-ipv6 /usr/share/irrpt/filters/as$1-$2-import-ipv6.txt $3
```
