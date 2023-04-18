# mikrotik-irrupdater
Update IRR Routing Filters on a Mikrotik Router running ROS7+

#### Prerequisits

[Mikrotik RouterOS API Python Packages](https://pypi.org/project/RouterOS-api/) and a Mikrotik Router(s) running BGP

#### What is this for?

This script will help you take a desired configuration for your IRR filter from a text file in a specified format, check the router configuration to see if this matches what's currently running, and if not, update it.  There is an example here of the required format for the desired configuration;

```
{'chain': 'as35008-fcix-import-ipv4', 'rule': 'if (dst==194.246.109.0/24) { accept }'}
{'chain': 'as35008-fcix-import-ipv4', 'rule': 'if (dst==194.15.141.0/24) { accept }'}
{'chain': 'as35008-fcix-import-ipv4', 'rule': 'reject'}
````
#### How do I run it?

The script needs a few things.  In the ```config.cfg``` you can specify the auth details for your RouterOS API.  We're assuming here you have a common username/password across all of your routers for this purpose.  Further you need to supply a few command line arguments;
````
python3 mikrotik_irr_updater.py chain_name config_file router_ip
````
Where chain_name is the name of the Routing Filter chain on your Mikrotik, config_file is the filename of the desired configuration for the filter and router_ip is of course the IP or hostname of your router.  For example:
````
python3 mikrotik_irr_updater.py as35008-fcix-import-ipv4 as35008-fcix-import-ipv4.txt pr2.fmt2
````

#### What else do I need?

There are many systems to generate the desired configuration of your IRR filters, but perhaps not in the right format.  I'm currently using [IRRPT](https://github.com/6connect/irrpt) to generate my IRR configs - it seems to work pretty well.  However there isn't an Mikrotik output, so I've adapted some bash originally by [Anurag Bhatia](https://anuragbhatia.com/2017/04/networking/isp-column/route-filter-generation-for-mikrotik-routeros-via-irr/) to output in the correct format for the python to then call the RouterOS API.

In the generate_irr_filter folder you'll find the modified bash script I'm using for my network setup: ros.sh.  If you place this into your irrpt directory, it'll generate an output which can be saved to a text file and used for the python code.

#### Automate it?

Now you just need to wrap this in another script or call it from cron.  I have a wrapper that I'm using, which generates the text files using IRRPT once per day, and then runs the mikrotik_irr_updater against them to keep the routers upto date.  It's manual to setup a new peer etc into the system, but worth it to auto maintain the filters.  Checkout the [automation](automation) directory for a bit more detail.

#### What else?

The code is very very alpha release - and the first thing I've written in python.  You can help by making it better, but nothing else seemed to exist for Mikrotik, I had a particular need so made this as an initial version.