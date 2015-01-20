# Mailrun Module
An Odoo/OpenERP module for facilitating ad-hoc sharing between nearby
warehouse locations.

## Overview

This module allows for sharing of stock between warehouses. Product quantities
on hand are calculated according to how much is available in all warehouses
that are being shared with the logged-in user's company warehouses. Stock gets
gets pulled from the "highest weighted" of those warehouses. Weights are
calculated as follows:

- 1pt: Warehouse location's address record is the same as the stock location of
       the order's shop's warehouse's stock location address record.

- 2pts: Warehouse location record is the same as the order's shop's warehouse's
       stock location record.

- 4pts: Warehouse location has the item in stock.

In other words, delivery orders from sales will pull from whatever location has
the item in stock. If there are multiple locations that have the item in stock,
or if no location has the item in stock, it will pull from the order's shop's
warehouse's stock location. If somehow there are no warehouses belonging to the
logged-in user's company or shared with the user's company's warehouses which
have the item in stock or share a location record with the order's stock
location, it will pull from whichever of those warehouses share an address
record with the order's stock location's address record.

Any warehouses which are in a "warehouse group" together will share stock.
Warehouse groups are presently set through a field on each warehouse's form.
Warehouses that are not in a group together will *not* share stock.

In the event that the module decides to pull the product from a warehouse owned
by another company, the delivery order will show the product's move as coming
from the location set in the order's warehouse as the "Mailrun Input" location.
It will also create a delivery order for the company that owns the warehouse
supplying the product with a move showing the product coming from its location
in the warehouse and going to the warehouse's "Mailrun Output" location.

On the picking list for the order, any moves coming from the "Mailrun Input"
location will show up under the "From Mailrun" heading. If the warehouse it is
coming from has not yet generated a mailrun report with their corresponding
move on it, "Mailrun Date" will show up as "TBD." Otherwise it will display the
date the mailrun report containing the corresponding move was generated.

Picking lists are generated the usual way, through the "Print" dropdown menu on
the "Delivery Orders" tree. Mailrun reports are generated through "Mailrun
Requests" in the sidebar menu under "Warehouse > Receive/Deliver By Orders."
The last ten mailrun reports generated are shown in the dropdown menu. Only
one new mailrun report can be generated per day. (This constraint is in place
to reduce the chances of stock moves being missed due to having been placed on
mailrun reports accidentally generated after the mailrun for that day has taken
place.)


