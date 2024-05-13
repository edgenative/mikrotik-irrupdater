
# mikrotik-irrupdater

Update IRR Routing Filters on a Mikrotik Router running ROS7+

#### Prerequisits

- Mikrotik router(s) running ROS 7+ (We've tested against 7.7 through 7.12)
- API configured and accessible on your router(s)
- [Mikrotik RouterOS API Python Packages](https://pypi.org/project/RouterOS-api/) and a Mikrotik Router(s) running BGP
- BGPQ4 installed on the host where you plan to run these scripts (Debian/Ubuntu apt-get install bgpq4)

#### What is this for?

You want to run strict IRR filters on your customer/peer BGP sessions and have a Mikrotik router.  This collection of scripts essentially wraps around BGPQ4 to generate prefix lists, then builds filter config that can be read by our python to push them to the actual router using the Mikrotik API.

If you wish to run the python on it's own, we've made the python script accept a format like the below;

```
{'chain': 'as35008-fcix-import-ipv4', 'rule': 'if (dst==194.246.109.0/24) { accept }'}
{'chain': 'as35008-fcix-import-ipv4', 'rule': 'if (dst==194.15.141.0/24) { accept }'}
{'chain': 'as35008-fcix-import-ipv4', 'rule': 'reject'}
````

However, we've included everything you need to make this pretty self-contained and so the scripts here do everything you need to build this format from a list of prefixes generated by BGPQ4.

#### How do I configure it?

This updated collection has everything you need in one place.  Our previous release was a bit complex and required IRRPT and some other bits.  We've made it much simpler after feedback, so it's all pretty self contained.  That said, you do need to configure a couple of things here.  We're expecting you to install this into ```/usr/share/mikrotik-irrupdater/``` on your host;

- ```config/routers.conf``` specify here the username and password required to interact with your routers API
- ```config/peers.conf``` specify here, as comma separated lines the ASN and AS-SET of your peers.  You'll need todo this everytime you add a new peer that you need filters for.
- ```config/sessions.conf``` this file contains the combination of the ASN, the slug (e.g. the IXP name, or the name you want to contain in the filter name) and the router hostname/ip it's on.  You'll need to update this everytime you setup a new peer on an IX/PNI/New Router. You can also specify a final parameter of ```ipv4|ipv6``` if you wish to only push a configuration for a particular affinity.


#### Automate it?

Once you've got the configuration set, you can simply schedule a couple of things to run in cron and you should be all set.

- ```buildprefixes.sh``` run this on some schedule.  It'll use bgpq4 to build the prefix lists and the actual filters to be pushed to the router.  It'll take time to run depending on the number of peers you have, and how many prefixes they have.  It pulls the prefixes for your peers based on ```config/peers.conf```.

- ```pushfilters.sh``` run this on a schedule, or directly after buildprefixes.sh.  Essentially this calls the python code to push the filters to your routers.  It'll loop through everything in the ```config/sessions.conf``` file automatically.

#### How do I use it on the router?

The scripts here generate filters using a slug as the entity name.  For example, we use fcix for the Fremont Cabal Internet Exchange, sfmix for San Francisco Metropolitan Internet Exchange and customer for downstream customers.  This results in filters named as follows;

- ```as32934-sfmix-import-ipv4``` for Facebook at SFMIX on IPv4
- ```as32934-sfmix-import-ipv6``` for Facebook at SFMIX on IPv6

Using the slug, it then goes on to call another filter which needs to exist on your router todo other things.  The filters generated by our code here look for ```<slugname>-import``` as the next filter.  So for sfmix in our example here, we're looking for another filter called ```sfmix-import```.  Within this import you can set local preference, med, communities and everything else you need for your internal TE policy.  Infact in our setup, we're then jumping to another filter after this which checks RPKI.


#### What else?

- This has been presented at a number of Internet fora, including EPF and Teraco Virtual Tech days -- a copy of the slides can be found at https://www.edgenative.net/teraco_virtual_techday_mikrotik_routing_security.pdf and youtube recording https://www.youtube.com/watch?v=OKN_GkD0hNI
- You can help by making this better, but nothing else seemed to exist for Mikrotik, I had a particular need so made this as an initial version after a peer leaked me a partial table for a few mins. If you need a Juniper version of these scripts, I've recently released this here [Edgenative/junos-irrupdater](https://github.com/edgenative/junos-irrupdater)

#### Was this useful?

Let me know, I'd love to hear from you!


