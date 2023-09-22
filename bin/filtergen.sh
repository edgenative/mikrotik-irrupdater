#!/bin/bash
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023 Lee Hetherington <lee@edgenative.net>
# Adapted from the original version by Anurag Bhatia
#
# Input name of chain via $2 and ASN via $2
#
path=/usr/share/mikrotik-irrupdater
# Grab latest filters via RADB / other IRRs using path
# IPv4 config part

echo -n "" > $path/filters/as$2-$3-import-ipv4.txt
sort -u $path/db/$2.4.agg | while read prefix
do
masklength=`echo $prefix|awk -F '/' '{print $2}'`
if [ "$masklength" -eq 24 ]
        then
        # Prefix is a /24 - generating config without defining prefix length
        echo "{'chain': 'as$2-$3-import-ipv4', 'rule': 'if (dst==$prefix) { jump $3-import }'}" >> $path/filters/as$2-$3-import-ipv4.txt
elif [ "$masklength" -lt 24 ]
        then
        # Prefix is greater than /24 - generating config with prefix length upto /24
        echo "{'chain': 'as$2-$3-import-ipv4', 'rule': 'if (dst in $prefix && dst-len<=24) { jump $3-import }'}" >> $path/filters/as$2-$3-import-ipv4.txt
fi
done
# Last entry for denial of pools
echo "{'chain': 'as$2-$3-import-ipv4', 'rule': 'reject'}" >> $path/filters/as$2-$3-import-ipv4.txt
echo -n "" > $path/filters/as$2-$3-import-ipv6.txt
sort -u $path/db/$2.6.agg | while read prefix6
do
masklength6=`echo $prefix6|awk -F '/' '{print $2}'`
if [ "$masklength6" -eq 48 ]
        then
        # Prefix is a /48 - generating config without defining prefix length
        echo "{'chain': 'as$2-$3-import-ipv6', 'rule': 'if (dst==$prefix6) { jump $3-import }'}" >> $path/filters/as$2-$3-import-ipv6.txt
elif [ "$masklength6" -lt 48 ]
        then
        # Prefix is greater than /48 - generating config with prefix length upto /48
        echo "{'chain': 'as$2-$3-import-ipv6', 'rule': 'if (dst in $prefix6 && dst-len<=48) { jump $3-import }'}" >> $path/filters/as$2-$3-import-ipv6.txt
fi
done
# Last entry for denial of pools
echo "{'chain': 'as$2-$3-import-ipv6', 'rule': 'reject'}" >> $path/filters/as$2-$3-import-ipv6.txt
